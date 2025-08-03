from fastapi import APIRouter, HTTPException
from google_auth_oauthlib.flow import Flow
import os
import json
import base64

router = APIRouter()
SCOPES = ['https://www.googleapis.com/auth/calendar']

@router.get("/.netlify/functions/google_auth_url")
async def get_google_auth_url():
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
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI')
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"auth_url": auth_url}