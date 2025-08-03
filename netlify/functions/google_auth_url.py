# netlify/functions/google_auth_url.py

from fastapi import APIRouter
from google_auth_oauthlib.flow import Flow
import os

router = APIRouter()

# --- PERBAIKAN PATH ---
script_dir = os.path.dirname(__file__)
CLIENT_SECRETS_FILE = os.path.join(script_dir, 'client_secret.json')
# --------------------

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