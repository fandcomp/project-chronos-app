import os
import json
import base64
import datetime
from fastapi import APIRouter, Request, HTTPException, FastAPI

# --- Impor untuk Supabase ---
from supabase import create_client, Client

# --- Impor untuk Google & AI ---
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import vision
from google.oauth2 import service_account
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import tool, AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# --- Konfigurasi Awal ---
# Netlify akan menjalankan aplikasi FastAPI ini.
app = FastAPI() 
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- FUNGSI BANTUAN (HELPERS) ---

def _get_google_client_config():
    """Merakit konfigurasi OAuth Google dari environment variables."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not all([client_id, client_secret, project_id]):
        raise ValueError("Google OAuth credentials are not fully configured.")
    return { "web": { "client_id": client_id, "project_id": project_id, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_secret": client_secret } }

def _get_google_calendar_service(user_id: str):
    """Membuat service untuk Google Calendar berdasarkan user_id."""
    res = supabase.table('user_tokens').select('refresh_token').eq('user_id', user_id).single().execute()
    if not res.data or not res.data.get('refresh_token'):
        raise ValueError("User has not connected their Google account or refresh token is missing.")
    
    client_config = _get_google_client_config()['web']
    creds = Credentials(
        token=None, refresh_token=res.data['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_config['client_id'], client_secret=client_config['client_secret']
    )
    return build('calendar', 'v3', credentials=creds)

# --- TOOLS UNTUK AI AGENT ---

@tool
def add_task_to_schedule(user_id: str, title: str, start_time: str, end_time: str):
    """Gunakan ini untuk menambahkan tugas baru. Simpan ke database dan Google Calendar."""
    try:
        task_res = supabase.table("tasks").insert({"user_id": user_id, "title": title, "start_time": start_time, "end_time": end_time}).execute()
        task_id = task_res.data[0]['id']

        service = _get_google_calendar_service(user_id)
        event_body = {'summary': title, 'start': {'dateTime': start_time, 'timeZone': 'Asia/Jakarta'}, 'end': {'dateTime': end_time, 'timeZone': 'Asia/Jakarta'}}
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        
        if google_event_id := created_event.get('id'):
            supabase.table("tasks").update({"google_calendar_event_id": google_event_id}).eq("id", task_id).execute()
        
        return f"Tugas '{title}' berhasil ditambahkan ke jadwal dan Google Calendar."
    except Exception as e:
        return f"Gagal menambahkan tugas: {e}"

# (Definisikan tools lain seperti delete_task dan update_task di sini jika diperlukan)

# --- ENDPOINTS API ---

@app.get("/api/google_auth_url")
async def get_google_auth_url():
    try:
        client_config = _get_google_client_config()
        flow = Flow.from_client_config(client_config=client_config, scopes=SCOPES, redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI'))
        auth_url, _ = flow.authorization_url(prompt='consent')
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/google_callback")
async def google_callback(state: str, code: str):
    try:
        client_config = _get_google_client_config()
        flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state, redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI'))
        flow.fetch_token(code=code)
        
        supabase.table('user_tokens').upsert({'user_id': state, 'provider': 'google', 'refresh_token': flow.credentials.refresh_token}, on_conflict='user_id').execute()
        return {"message": "Google Calendar berhasil terhubung!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze_schedule_file")
async def analyze_schedule_file(request: Request):
    try:
        gcp_credentials_info = {
            "type": "service_account", "project_id": os.environ.get("GCP_PROJECT_ID"),
            "private_key": os.environ.get("GCP_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.environ.get("GCP_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        credentials = service_account.Credentials.from_service_account_info(gcp_credentials_info)
        vision_client = vision.ImageAnnotatorClient(credentials=credentials)
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Google clients: {e}")
    
    body = await request.json()
    file_path = body.get("filePath")
    user_id = body.get("user_id")

    try:
        file_content = supabase.storage.from_("schedules").download(file_path)
        ocr_text = vision_client.text_detection(image=vision.Image(content=file_content)).text_annotations[0].description
        
        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        prompt = f"""Anda adalah asisten cerdas yang tugasnya mengekstrak jadwal dari teks mentah. Konteks waktu saat ini adalah: {today_date}. Berikut adalah teks hasil OCR dari sebuah file jadwal. Analisis teks ini dan kembalikan HANYA daftar acara dalam format JSON yang valid. Setiap acara dalam daftar harus berupa objek dengan key "title", "start_time", dan "end_time". Aturan: - Format "start_time" dan "end_time" harus dalam format ISO 8601 (contoh: "2025-08-04T10:00:00"). - Jika durasi tidak disebutkan, asumsikan durasi acara adalah 1 jam. - Jika waktu tidak spesifik (hanya hari), asumsikan jam 9 pagi (09:00). - Abaikan semua teks yang tidak relevan dengan jadwal atau acara. - Jangan memberikan penjelasan apa pun, hanya output JSON. Teks:\n---\n{ocr_text}\n---"""
        
        llm_response = llm.invoke(prompt)
        schedule_data = json.loads(llm_response.content.strip().replace("```json", "").replace("```", ""))
        
        tasks_to_insert = [{"user_id": user_id, "title": i.get("title"), "start_time": i.get("start_time"), "end_time": i.get("end_time")} for i in schedule_data]
        if tasks_to_insert:
            supabase.table("tasks").insert(tasks_to_insert).execute()
        return {"message": f"Berhasil menganalisis dan menambahkan {len(tasks_to_insert)} tugas baru."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent_handler")
async def handle_agent_query(request: Request):
    body = await request.json()
    query = body.get("query")
    user_id = body.get("user_id")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, convert_system_message_to_human=True)
        tools = [add_task_to_schedule]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a helpful assistant named Chronos. The user's ID is {user_id}. You must always pass this user_id to any tool you use. Today's date is {datetime.date.today().isoformat()}."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        result = await agent_executor.ainvoke({"input": query})
        return {"response": result.get("output", "Tugas selesai diproses.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {e}")