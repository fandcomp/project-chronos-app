from fastapi import APIRouter, Request, HTTPException
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import vision
from google.oauth2 import service_account
import os
import json
import base64
import datetime

router = APIRouter()
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)

vision_client = None
encoded_gcp_creds = os.environ.get('GOOGLE_GCP_CREDENTIALS_BASE64')
if encoded_gcp_creds:
    try:
        decoded_creds = base64.b64decode(encoded_gcp_creds)
        credentials_info = json.loads(decoded_creds)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        vision_client = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        print(f"Failed to initialize Vision Client from Base64 env var: {e}")

@router.post("/.netlify/functions/analyze_schedule_file")
async def analyze_schedule_file(request: Request):
    if not vision_client:
        raise HTTPException(status_code=500, detail="Google Cloud Vision is not configured correctly.")
        
    body = await request.json()
    try:
        # 1. Download file dari Supabase Storage
        file_content = supabase.storage.from_("schedules").download(file_path)
        
        # 2. Kirim ke Google Vision OCR untuk ekstraksi teks
        image = vision.Image(content=file_content)
        response = vision_client.text_detection(image=image)
        ocr_text = response.text_annotations[0].description if response.text_annotations else ""

        if not ocr_text:
            return {"message": "Tidak ada teks yang bisa dibaca dari file."}

        # 3. Kirim teks hasil OCR ke LLM (Gemini Pro) untuk dianalisis
        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        prompt = f"""
        Anda adalah asisten cerdas yang tugasnya mengekstrak jadwal dari teks mentah.
        Konteks waktu saat ini adalah: {today_date}.
        
        Berikut adalah teks hasil OCR dari sebuah file jadwal. Analisis teks ini dan kembalikan daftar acara dalam format JSON. Setiap acara harus memiliki 'title', 'start_time', dan 'end_time' dalam format ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        
        Abaikan teks yang tidak relevan. Jika waktu tidak spesifik, asumsikan jam kerja (09:00). Jika durasi tidak ada, asumsikan 1 jam.
        
        Teks:
        ---
        {ocr_text}
        ---
        """
        
        llm_response = llm.invoke(prompt)
        
        # Ekstrak JSON dari respons LLM
        # Logika ini mungkin perlu disesuaikan tergantung format output LLM
        import json
        json_string = llm_response.content.strip().replace("```json", "").replace("```", "")
        schedule_data = json.loads(json_string)

        # 4. Simpan jadwal yang terstruktur ke database Supabase
        tasks_to_insert = []
        for item in schedule_data:
            tasks_to_insert.append({
                "user_id": user_id,
                "title": item.get("title"),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time")
            })

        if tasks_to_insert:
            supabase.table("tasks").insert(tasks_to_insert).execute()

        return {"message": f"Berhasil menganalisis dan menambahkan {len(tasks_to_insert)} tugas baru dari file."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))