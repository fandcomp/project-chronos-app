from fastapi import APIRouter, Request, HTTPException
from google_auth_oauthlib.flow import Flow
from supabase import create_client, Client
import os

router = APIRouter()
SCOPES = ['https://www.googleapis.com/auth/calendar']
supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

@router.get("/.netlify/functions/google_callback")
async def google_callback(request: Request, state: str, code: str):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    project_id = os.environ.get("GCP_PROJECT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')

    if not all([client_id, project_id, client_secret, redirect_uri]):
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not fully configured.")

    client_config = {
        "web": { "client_id": client_id, "project_id": project_id, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_secret": client_secret }
    }
    
    flow = Flow.from_client_config(
        client_config=client_config, 
        scopes=SCOPES, 
        state=state, 
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    
    supabase.table('user_tokens').upsert({
        'user_id': state,
        'provider': 'google',
        'refresh_token': flow.credentials.refresh_token
    }, on_conflict='user_id').execute()

    return {"message": "Google Calendar berhasil terhubung!"}