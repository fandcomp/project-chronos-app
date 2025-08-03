from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os
import json

router = APIRouter()

# --- Konfigurasi ---
script_dir = os.path.dirname(__file__)
CLIENT_SECRETS_FILE = os.path.join(script_dir, 'client_secret.json')
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    with open(CLIENT_SECRETS_FILE, 'r') as f:
        secrets = json.load(f)['web']
        CLIENT_ID = secrets['client_id']
        CLIENT_SECRET = secrets['client_secret']
except FileNotFoundError:
    CLIENT_ID, CLIENT_SECRET = None, None

@router.post("/.netlify/functions/delete_task")
async def delete_task(request: Request):
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="Client secrets file not found.")

    body = await request.json()
    task_id = body.get('task_id')
    google_event_id = body.get('google_event_id')
    user_id = body.get('user_id')

    if not all([task_id, user_id]):
        raise HTTPException(status_code=400, detail="Missing task_id or user_id.")

    try:
        # 1. Hapus acara dari Google Calendar jika ada
        if google_event_id:
            res = supabase.table('user_tokens').select('refresh_token').eq('user_id', user_id).single().execute()
            if res.data and res.data.get('refresh_token'):
                creds = Credentials(
                    token=None, refresh_token=res.data['refresh_token'],
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=CLIENT_ID, client_secret=CLIENT_SECRET
                )
                service = build('calendar', 'v3', credentials=creds)
                try:
                    service.events().delete(calendarId='primary', eventId=google_event_id).execute()
                except Exception as e:
                    # Abaikan error jika acara sudah tidak ada di kalender
                    print(f"Could not delete Google Calendar event (it may already be gone): {e}")

        # 2. Hapus tugas dari database Supabase
        supabase.table("tasks").delete().eq("id", task_id).execute()

        return {"status": "success", "message": "Tugas berhasil dihapus."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))