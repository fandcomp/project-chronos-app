from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os
import json
import base64

router = APIRouter()
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

@router.post("/.netlify/functions/delete_task")
async def delete_task(request: Request):
    encoded_secret = os.environ.get('GOOGLE_CLIENT_SECRET_BASE64')
    if not encoded_secret:
        raise HTTPException(status_code=500, detail="Google client secret is not configured.")
    
    try:
        decoded_secret = base64.b64decode(encoded_secret)
        secrets = json.loads(decoded_secret)['web']
        CLIENT_ID = secrets['client_id']
        CLIENT_SECRET = secrets['client_secret']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decode client secret: {e}")

    body = await request.json()
    user_id = body.get('user_id')
    task_id = body.get('task_id')
    google_event_id = body.get('google_event_id')

    if not all([task_id, user_id]):
        raise HTTPException(status_code=400, detail="Missing task_id or user_id.")

    try:
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
                    print(f"Could not delete Google Calendar event: {e}")

        supabase.table("tasks").delete().eq("id", task_id).execute()

        return {"status": "success", "message": "Tugas berhasil dihapus."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))