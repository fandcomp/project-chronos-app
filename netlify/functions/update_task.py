from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os
import json

router = APIRouter()

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

@router.post("/.netlify/functions/update_task")
async def update_task(request: Request):
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="Client secrets file not found.")

    body = await request.json()
    task_id = body.get('task_id')
    google_event_id = body.get('google_event_id')
    user_id = body.get('user_id')
    updated_data = body.get('updated_data') # e.g., {"title": "new title", "start_time": "..."}

    if not all([task_id, user_id, updated_data]):
        raise HTTPException(status_code=400, detail="Missing required data.")

    try:
        # 1. Perbarui acara di Google Calendar jika ada
        if google_event_id:
            res = supabase.table('user_tokens').select('refresh_token').eq('user_id', user_id).single().execute()
            if res.data and res.data.get('refresh_token'):
                creds = Credentials(
                    token=None, refresh_token=res.data['refresh_token'],
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=CLIENT_ID, client_secret=CLIENT_SECRET
                )
                service = build('calendar', 'v3', credentials=creds)
                
                event = service.events().get(calendarId='primary', eventId=google_event_id).execute()
                
                event['summary'] = updated_data.get('title', event['summary'])
                event['start']['dateTime'] = updated_data.get('start_time', event['start']['dateTime'])
                event['end']['dateTime'] = updated_data.get('end_time', event['end']['dateTime'])
                
                service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

        # 2. Perbarui tugas di Supabase
        supabase.table("tasks").update({
            "title": updated_data.get("title"),
        }).eq("id", task_id).execute()

        return {"status": "success", "message": "Tugas berhasil diperbarui."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))