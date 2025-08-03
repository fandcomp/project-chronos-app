from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os

router = APIRouter()
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

@router.post("/.netlify/functions/create_calendar_event")
async def create_event(request: Request):
    CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not all([CLIENT_ID, CLIENT_SECRET]):
        raise HTTPException(status_code=500, detail="Google client credentials are not configured.")

    body = await request.json()
    user_id = body.get('user_id')
    task_id = body.get('task_id')
    event_details = body.get('event')

    if not all([user_id, task_id, event_details]):
        raise HTTPException(status_code=400, detail="Missing user_id, task_id, or event details.")

    try:
        res = supabase.table('user_tokens').select('refresh_token').eq('user_id', user_id).single().execute()
        refresh_token = res.data['refresh_token']

        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)

        event_body = {
            'summary': event_details.get('summary'),
            'start': {'dateTime': event_details.get('start'), 'timeZone': 'Asia/Jakarta'},
            'end': {'dateTime': event_details.get('end'), 'timeZone': 'Asia/Jakarta'},
        }
        
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        google_event_id = created_event.get('id')

        if google_event_id:
            supabase.table("tasks").update({"google_calendar_event_id": google_event_id}).eq("id", task_id).execute()
        
        return {"status": "success", "event_link": created_event.get('htmlLink')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))