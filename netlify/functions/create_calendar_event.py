from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os
import json

router = APIRouter()

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.post("/.netlify/functions/create_calendar_event")
async def create_event(request: Request):
    client_config_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    if not client_config_json:
        raise HTTPException(status_code=500, detail="Google client secret is not configured.")
    
    secrets = json.loads(client_config_json)['web']
    CLIENT_ID = secrets['client_id']
    CLIENT_SECRET = secrets['client_secret']

    body = await request.json()
    user_id = body.get('user_id')
    task_id = body.get('task_id')
    event_details = body.get('event')

    # ... (sisa kode tidak berubah)

    if not all([user_id, task_id, event_details]):
        raise HTTPException(status_code=400, detail="Missing user_id, task_id, or event details.")

    try:
        # 1. Ambil refresh_token dari database
        res = supabase.table('user_tokens').select('refresh_token').eq('user_id', user_id).single().execute()
        if not res.data or not res.data.get('refresh_token'):
            raise HTTPException(status_code=401, detail="User has not connected their Google account or refresh token is missing.")
        
        refresh_token = res.data['refresh_token']

        # 2. Buat objek credentials dari token yang ada
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        # 3. Bangun service Google Calendar
        service = build('calendar', 'v3', credentials=creds)

        # 4. Buat acara
        event_body = {
            'summary': event_details.get('summary'),
            'start': {'dateTime': event_details.get('start'), 'timeZone': 'Asia/Jakarta'},
            'end': {'dateTime': event_details.get('end'), 'timeZone': 'Asia/Jakarta'},
        }
        
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        google_event_id = created_event.get('id')

        # PERUBAHAN 2: SIMPAN google_event_id KE TABEL TASKS
        if google_event_id:
            supabase.table("tasks").update({
                "google_calendar_event_id": google_event_id
            }).eq("id", task_id).execute()
        
        return {"status": "success", "event_link": created_event.get('htmlLink')}

    except Exception as e:
        # Log error untuk debugging
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))