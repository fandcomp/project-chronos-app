# netlify/functions/google_callback.py

from fastapi import APIRouter, Request
from google_auth_oauthlib.flow import Flow
from supabase import create_client
import os
import json

router = APIRouter()

# Konfigurasi yang sama
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.get("/.netlify/functions/google_callback")
async def google_callback(request: Request, state: str, code: str):
    flow = Flow.from_client_secrets_file(
        client_secrets_file=CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI')
    )
    
    # Tukarkan authorization code dengan token
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Dapatkan ID pengguna (ini perlu Anda teruskan dari frontend, misal via 'state')
    # Untuk sekarang kita anggap 'state' berisi user_id
    user_id = state 

    # Simpan refresh token ke Supabase
    token_data = {
        'user_id': user_id,
        'provider': 'google',
        'refresh_token': credentials.refresh_token
    }
    
    # Buat tabel 'user_tokens' di Supabase jika belum ada
    supabase.table('user_tokens').upsert(token_data, on_conflict='user_id').execute()

    return {"message": "Google Calendar berhasil terhubung!"}