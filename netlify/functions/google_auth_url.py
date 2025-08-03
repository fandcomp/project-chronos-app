# netlify/functions/google_auth_url.py

from fastapi import APIRouter
from google_auth_oauthlib.flow import Flow
import os

router = APIRouter()

# Konfigurasi OAuth 2.0 (gunakan environment variables)
# Pastikan Anda sudah mengatur ini di Netlify
CLIENT_SECRETS_FILE = 'client_secret.json' # Anda perlu membuat file ini
SCOPES = ['https://www.googleapis.com/auth/calendar']

@router.get("/.netlify/functions/google_auth_url")
async def get_google_auth_url():
    flow = Flow.from_client_secrets_file(
        client_secrets_file=CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI') # e.g., https://yoursite.netlify.app/.netlify/functions/google_callback
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"auth_url": auth_url}