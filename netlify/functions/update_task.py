from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from supabase import create_client, Client
import os

router = APIRouter()
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

@router.post("/.netlify/functions/update_task")
async def update_task(request: Request):
    CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not all([CLIENT_ID, CLIENT_SECRET]):
        raise HTTPException(status_code=500, detail="Google client credentials are not configured.")

    body = await request.json()
    task_id = body.get('task_id')
    google_event_id = body.get('google_event_id')
    user_id = body.get('user_id')
    updated_data = body.get('updated_data')

    if not all([task_id, user_id, updated_data]):
        raise HTTPException(status_code=400, detail="Missing required data.")

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
                event = service.events().get(calendarId='primary', eventId=google_event_id).execute()
                event['summary'] = updated_data.get('title', event['summary'])
                event['start']['dateTime'] = updated_data.get('start_time', event['start']['dateTime'])
                event['end']['dateTime'] = updated_data.get('end_time', event['end']['dateTime'])
                service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

        supabase.table("tasks").update({"title": updated_data.get("title")}).eq("id", task_id).execute()
        return {"status": "success", "message": "Tugas berhasil diperbarui."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))