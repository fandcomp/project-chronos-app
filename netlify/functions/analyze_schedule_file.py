from fastapi import APIRouter, Request, HTTPException
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import vision
from google.oauth2 import service_account
import os, json, datetime

router = APIRouter()
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)

vision_client = None
gcp_project_id = os.environ.get("GCP_PROJECT_ID")
gcp_private_key = os.environ.get("GCP_PRIVATE_KEY")
gcp_client_email = os.environ.get("GCP_CLIENT_EMAIL")

if all([gcp_project_id, gcp_private_key, gcp_client_email]):
    gcp_credentials_info = {
        "type": "service_account", "project_id": gcp_project_id,
        "private_key": gcp_private_key.replace('\\n', '\n'),
        "client_email": gcp_client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    credentials = service_account.Credentials.from_service_account_info(gcp_credentials_info)
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)

@router.post("/.netlify/functions/analyze_schedule_file")
async def analyze_schedule_file(request: Request):
    if not vision_client:
        raise HTTPException(status_code=500, detail="Google Vision credentials are not configured correctly.")
    
    body = await request.json()
    file_path = body.get("filePath")
    user_id = body.get("user_id")

    try:
        file_content = supabase.storage.from_("schedules").download(file_path)
        image = vision.Image(content=file_content)
        response = vision_client.text_detection(image=image)
        ocr_text = response.text_annotations[0].description if response.text_annotations else ""

        if not ocr_text: return {"message": "Tidak ada teks yang bisa dibaca dari file."}

        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        
        # --- ISI PROMPT DI SINI ---
        prompt = f"""
        Anda adalah asisten cerdas yang tugasnya mengekstrak jadwal dari teks mentah.
        Konteks waktu saat ini adalah: {today_date}.
        
        Berikut adalah teks hasil OCR dari sebuah file jadwal. Analisis teks ini dan kembalikan HANYA daftar acara dalam format JSON yang valid. Setiap acara dalam daftar harus berupa objek dengan key "title", "start_time", dan "end_time".
        
        Aturan:
        - Format "start_time" dan "end_time" harus dalam format ISO 8601 (contoh: "2025-08-04T10:00:00").
        - Jika durasi tidak disebutkan, asumsikan durasi acara adalah 1 jam.
        - Jika waktu tidak spesifik (hanya hari), asumsikan jam 9 pagi (09:00).
        - Abaikan semua teks yang tidak relevan dengan jadwal atau acara.
        - Jangan memberikan penjelasan apa pun, hanya output JSON.
        
        Teks:
        ---
        {ocr_text}
        ---
        """
        # --- AKHIR DARI PROMPT ---
        
        llm_response = llm.invoke(prompt)
        json_string = llm_response.content.strip().replace("```json", "").replace("```", "")
        schedule_data = json.loads(json_string)

        tasks_to_insert = [
            {"user_id": user_id, "title": item.get("title"), "start_time": item.get("start_time"), "end_time": item.get("end_time")}
            for item in schedule_data
        ]

        if tasks_to_insert:
            supabase.table("tasks").insert(tasks_to_insert).execute()

        return {"message": f"Berhasil menganalisis dan menambahkan {len(tasks_to_insert)} tugas baru."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))