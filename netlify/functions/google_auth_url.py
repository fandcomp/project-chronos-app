from fastapi import APIRouter
from google_auth_oauthlib.flow import Flow
import os
import json

router = APIRouter()

SCOPES = ['https://www.googleapis.com/auth/calendar']

@router.get("/.netlify/functions/google_auth_url")
async def get_google_auth_url():
    # Ambil konfigurasi dari environment variable
    client_config_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    if not client_config_json:
        raise HTTPException(status_code=500, detail="Google client secret is not configured.")
    
    client_config = json.loads(client_config_json)

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI')
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"auth_url": auth_url}