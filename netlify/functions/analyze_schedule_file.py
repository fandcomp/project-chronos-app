from fastapi import APIRouter, Request, HTTPException
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import vision
from google.oauth2 import service_account
import os
import datetime
import json

router = APIRouter()

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)

# Inisialisasi Klien Google Vision dari environment variable
gcp_credentials_json = os.environ.get('GOOGLE_GCP_CREDENTIALS_JSON')
if gcp_credentials_json:
    credentials_info = json.loads(gcp_credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
else:
    vision_client = None # Handle jika variabel tidak ada

@router.post("/.netlify/functions/analyze_schedule_file")
async def analyze_schedule_file(request: Request):
    if not vision_client:
        raise HTTPException(status_code=500, detail="Google Cloud Vision credentials are not configured.")
        
    # ... (sisa kode tidak berubah)
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