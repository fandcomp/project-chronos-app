from fastapi import APIRouter, HTTPException
from google_auth_oauthlib.flow import Flow
import os

router = APIRouter()
SCOPES = ['https://www.googleapis.com/auth/calendar']

@router.get("/.netlify/functions/google_auth_url")
async def get_google_auth_url():
    # Rakit kembali client_config dari environment variables
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    project_id = os.environ.get("GCP_PROJECT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')

    if not all([client_id, project_id, client_secret, redirect_uri]):
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not fully configured.")

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret
        }
    }
    
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"auth_url": auth_url}