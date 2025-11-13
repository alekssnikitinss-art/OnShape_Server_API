import os
import base64
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load config from environment variables
CLIENT_ID = os.getenv("ONSHAPE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONSHAPE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

AUTH_URL = "https://cad.onshape.com/oauth/authorize"
TOKEN_URL = "https://cad.onshape.com/oauth/token"
SCOPE = "documents:read documents:write"


if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    @app.get("/")
    def missing_config():
        return {"error": "Missing ONSHAPE_CLIENT_ID / ONSHAPE_CLIENT_SECRET / REDIRECT_URI in env"}
else:
    # Serve your HTML website at root
    @app.get("/")
    def root():
        return FileResponse("static/index.html")
    
    # API endpoints remain the same but now under /api prefix
    @app.get("/api/status")
    def api_status():
        return {"message": "Onshape OAuth API running"}

    @app.get("/login")
    def login():
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": "aleks_state_123"
        }
        from urllib.parse import urlencode
        url = AUTH_URL + "?" + urlencode(params)
        return RedirectResponse(url)

    @app.get("/callback")
    async def callback(request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code:
            raise HTTPException(status_code=400, detail="Missing code in callback")

        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        resp = requests.post(TOKEN_URL, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Token exchange failed: {resp.text}")

        token_data = resp.json()
        return JSONResponse(content=token_data)

    @app.get("/me")
    def me(access_token: str = None):
        if not access_token:
            return {"error": "Provide access_token as query param for demo, or implement server-side storage."}

        profile_url = "https://cad.onshape.com/api/users/session"
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(profile_url, headers=headers)
        if r.status_code != 200:
            return {"status": "api call failed", "code": r.status_code, "body": r.text}
        return r.json()

    @app.get("/refresh")
    def refresh(refresh_token: str):
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")
        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        resp = requests.post(TOKEN_URL, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Refresh failed: {resp.text}")
        return resp.json()
