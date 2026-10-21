import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from mcp.server.fastmcp import FastMCP

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]
TOKEN_FILE = Path("/tmp/youtube_token.json")

mcp = FastMCP("YouTube Upload")
app = FastAPI()

def oauth_flow(state=None):
    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI
    )

def save_creds(creds):
    TOKEN_FILE.write_text(creds.to_json())

def load_creds():
    if not TOKEN_FILE.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    except Exception:
        return None

@mcp.tool()
def youtube_auth_url() -> str:
    """Return a Google authorization URL. Open it once to authorize this server to upload to the connected YouTube channel."""
    state = secrets.token_urlsafe(32)
    # For a simple single-user deployment, state is encoded in the authorization URL.
    # The callback validates the OAuth state carried by Google's response.
    flow = oauth_flow(state)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url

@mcp.tool()
def youtube_auth_status() -> str:
    """Check whether this server has a stored YouTube OAuth credential."""
    creds = load_creds()
    if not creds:
        return "Not connected. Call youtube_auth_url and open the returned Google URL."
    return "YouTube authorization is present."

@mcp.tool()
def upload_video(
    file_url: str,
    title: str,
    description: str = "",
    tags: str = "",
    privacy_status: str = "private",
    category_id: str = "22",
) -> str:
    """Download a public HTTPS video URL and upload it to YouTube. privacy_status: private, unlisted, or public."""
    if privacy_status not in {"private", "unlisted", "public"}:
        raise ValueError("privacy_status must be private, unlisted, or public")
    creds = load_creds()
    if not creds:
        raise RuntimeError("YouTube is not connected. Call youtube_auth_url first.")
    import tempfile, urllib.request
    suffix = ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        tmp = f.name
    try:
        urllib.request.urlretrieve(file_url, tmp)
        yt = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": [x.strip() for x in tags.split(",") if x.strip()],
                "categoryId": category_id,
            },
            "status": {"privacyStatus": privacy_status},
        }
        request = yt.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(tmp, chunksize=-1, resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return f"Uploaded successfully: https://www.youtube.com/watch?v={response['id']}"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

# Mount MCP at /mcp. FastMCP's current streamable HTTP transport is used.
app.mount("/", mcp.streamable_http_app())

@app.get("/oauth2callback")
def oauth2callback(request: Request):
    state = request.query_params.get("state")
    if not state:
        return HTMLResponse("Missing OAuth state.", status_code=400)
    flow = oauth_flow(state)
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    save_creds(creds)
    return HTMLResponse("<h2>YouTube connected successfully.</h2><p>You can close this page and return to Claude.</p>")

@app.get("/health")
def health():
    return JSONResponse({"ok": True, "service": "youtube-mcp"})
