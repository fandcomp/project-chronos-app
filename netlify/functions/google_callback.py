from fastapi import APIRouter, Request, HTTPException
from google_auth_oauthlib.flow import Flow
from supabase import create_client, Client
import os
import json
import base64

router = APIRouter()
SCOPES = ['https://www.googleapis.com/auth/calendar']
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

@router.get("/.netlify/functions/google_callback")
async def google_callback(request: Request, state: str, code: str):
    encoded_secret = os.environ.get('GOOGLE_CLIENT_SECRET_BASE64')
    if not encoded_secret:
        raise HTTPException(status_code=500, detail="Google client secret is not configured.")
    
    try:
        decoded_secret = base64.b64decode(encoded_secret)
        client_config = json.loads(decoded_secret)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decode client secret: {e}")
    
    flow = Flow.from_client_config(
        client_config=client_config, 
        scopes=SCOPES, 
        state=state, 
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI')
    )
    flow.fetch_token(code=code)
    
    supabase.table('user_tokens').upsert({
        'user_id': state,
        'provider': 'google',
        'refresh_token': flow.credentials.refresh_token
    }, on_conflict='user_id').execute()

    return {"message": "Google Calendar berhasil terhubung!"}