# api/process_pdf.py
from fastapi import FastAPI, Request
from supabase import create_client, Client
import fitz # PyMuPDF
import os
import re # Untuk parsing teks sederhana

# Inisialisasi Supabase
url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") # Gunakan Service Key untuk backend
supabase: Client = create_client(url, key)

router = APIRouter()

@router.post("/api/process_pdf")
async def process_pdf(request: Request):
    body = await request.json()
    file_path = body.get("filePath")
    user_id = file_path.split('/')[0] # Dapatkan user_id dari path file

    try:
        # 1. Download file dari Supabase Storage
        response = supabase.storage.from_("schedules").download(file_path)
        pdf_content = response

        # 2. Buka dan baca konten PDF
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        # 3. Logika Parsing (SANGAT DISESUAIKAN)
        # Contoh sederhana: mencari pola "Matakuliah: [Nama], Hari: [Hari], Jam: [Jam]"
        # Anda perlu menyesuaikan regex ini sesuai format PDF Anda.
        pattern = re.compile(r"Matakuliah: (.*), Hari: (.*), Jam: (.*)")
        matches = pattern.findall(full_text)

        tasks_to_insert = []
        for match in matches:
            title, day, time = match
            tasks_to_insert.append({
                "user_id": user_id,
                "title": f"{title} ({day})",
                # Anda perlu logika lebih lanjut untuk mengubah "Senin, 13:00" menjadi timestamp
                "description": f"Jadwal dari PDF. Hari: {day}, Jam: {time}"
            })

        # 4. Simpan ke database
        if tasks_to_insert:
            supabase.table("tasks").insert(tasks_to_insert).execute()

        return {"message": f"Berhasil memproses {len(tasks_to_insert)} jadwal dari PDF."}
    except Exception as e:
        return {"message": f"Terjadi kesalahan: {str(e)}"}, 500