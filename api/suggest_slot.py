# api/suggest_slot.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from datetime import datetime, date, time, timedelta, timezone

# --- Inisialisasi Klien Supabase & Aplikasi FastAPI ---
# Pastikan Anda sudah mengatur environment variables ini di Vercel
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Cek jika variabel environment tidak ada
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Supabase URL and Service Key must be set in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
app = FastAPI()

# --- Model Data untuk Request Body ---
# Menggunakan Pydantic untuk validasi input otomatis
class SuggestSlotRequest(BaseModel):
    user_id: str
    date_str: str  # Format: "YYYY-MM-DD"
    duration_minutes: int
    buffer_minutes: int

# --- Logika Inti ---
@app.post("/api/suggest_slot")
async def suggest_slot(request: SuggestSlotRequest):
    try:
        # 1. Parsing dan Persiapan Input
        target_date = datetime.strptime(request.date_str, "%Y-%m-%d").date()
        total_duration_needed = timedelta(minutes=request.duration_minutes + request.buffer_minutes)

        # Tentukan jam kerja (bisa dibuat lebih dinamis nanti)
        working_hours_start = time(9, 0)
        working_hours_end = time(17, 0)
        
        # Buat rentang waktu kerja dalam format datetime dengan timezone UTC
        start_of_day = datetime.combine(target_date, working_hours_start, tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date, working_hours_end, tzinfo=timezone.utc)

        # 2. Ambil semua jadwal pengguna pada hari yang diinginkan
        response = supabase.table("tasks").select("start_time, end_time").eq("user_id", request.user_id).filter("start_time", "gte", start_of_day.isoformat()).filter("end_time", "lte", end_of_day.isoformat()).execute()
        
        events = response.data

        # 3. Buat daftar interval "sibuk" dan urutkan
        busy_intervals = []
        for event in events:
            if event.get("start_time") and event.get("end_time"):
                start = datetime.fromisoformat(event["start_time"])
                end = datetime.fromisoformat(event["end_time"])
                # Tambahkan buffer time ke setiap acara yang ada
                buffered_start = start - timedelta(minutes=request.buffer_minutes)
                buffered_end = end + timedelta(minutes=request.buffer_minutes)
                busy_intervals.append((buffered_start, buffered_end))
        
        busy_intervals.sort()

        # 4. Cari "celah" di antara interval sibuk
        free_slots = []
        current_time = start_of_day

        for busy_start, busy_end in busy_intervals:
            # Hitung waktu luang antara 'current_time' dan awal acara sibuk berikutnya
            free_duration = busy_start - current_time
            if free_duration >= total_duration_needed:
                free_slots.append(current_time.isoformat())
            
            # Majukan 'current_time' ke akhir acara sibuk saat ini
            if busy_end > current_time:
                current_time = busy_end
        
        # Cek waktu luang terakhir dari acara terakhir hingga akhir jam kerja
        if (end_of_day - current_time) >= total_duration_needed:
            free_slots.append(current_time.isoformat())

        # 5. Kembalikan hasilnya
        return {
            "message": f"Ditemukan {len(free_slots)} slot waktu yang disarankan.",
            "suggested_slots": free_slots
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))