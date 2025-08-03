from fastapi import APIRouter, Request, HTTPException
from google_auth_oauthlib.flow import Flow
from supabase import create_client, Client
import os
import json

router = APIRouter()

SCOPES = ['https://www.googleapis.com/auth/calendar']
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.get("/.netlify/functions/google_callback")
async def google_callback(request: Request, state: str, code: str):
    client_config_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    if not client_config_json:
        raise HTTPException(status_code=500, detail="Google client secret is not configured.")
    
    client_config = json.loads(client_config_json)

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI')
    )
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    user_id = state 

    token_data = {
        'user_id': user_id,
        'provider': 'google',
        'refresh_token': credentials.refresh_token
    }
    
    supabase.table('user_tokens').upsert(token_data, on_conflict='user_id').execute()

    return {"message": "Google Calendar berhasil terhubung!"}