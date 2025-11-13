import os
import base64
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests

app = FastAPI()

# Load config from environment variables
CLIENT_ID = os.getenv("ONSHAPE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONSHAPE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

AUTH_URL = "https://cad.onshape.com/oauth/authorize"
TOKEN_URL = "https://cad.onshape.com/oauth/token"
SCOPE = "documents:read documents:write"

# Single HTML file content
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnShape OAuth API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 50px auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        button {
            flex: 1;
            min-width: 150px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        #results {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            min-height: 100px;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .error {
            color: #dc3545;
            padding: 10px;
            background: #f8d7da;
            border-radius: 4px;
        }
        
        .success {
            color: #155724;
            padding: 10px;
            background: #d4edda;
            border-radius: 4px;
        }
        
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 14px;
        }
        
        .token-display {
            margin: 10px 0;
            padding: 10px;
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            border-radius: 4px;
            word-break: break-all;
        }
        
        .input-group {
            margin: 20px 0;
        }
        
        input {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 OnShape API Interface</h1>
        
        <div class="button-group">
            <button onclick="loginWithOnShape()">🔐 Login with OnShape</button>
            <button onclick="checkStatus()">📊 Check API Status</button>
        </div>
        
        <div class="input-group" id="tokenSection" style="display: none;">
            <label for="accessToken">Access Token:</label>
            <input type="text" id="accessToken" placeholder="Paste your access token here">
            <button onclick="getUserInfo()" style="margin-top: 10px; width: 100%;">👤 Get User Info</button>
        </div>
        
        <div class="input-group" id="refreshSection" style="display: none;">
            <label for="refreshToken">Refresh Token:</label>
            <input type="text" id="refreshToken" placeholder="Paste your refresh token here">
            <button onclick="refreshAccessToken()" style="margin-top: 10px; width: 100%;">🔄 Refresh Token</button>
        </div>
        
        <div id="results"></div>
    </div>

    <script>
        // Check if we're returning from OAuth callback
        window.onload = function() {
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            
            if (code) {
                // We're in the callback, show a message
                showResult('✅ Login successful! Processing...', 'success');
                // The FastAPI callback endpoint will handle the token exchange
            }
        };
        
        function loginWithOnShape() {
            window.location.href = '/login';
        }
        
        async function checkStatus() {
            showResult('Loading...', 'info');
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                showResult(JSON.stringify(data, null, 2), 'success');
            } catch (error) {
                showResult(`Error: ${error.message}`, 'error');
            }
        }
        
        async function getUserInfo() {
            const accessToken = document.getElementById('accessToken').value;
            if (!accessToken) {
                showResult('Please enter an access token', 'error');
                return;
            }
            
            showResult('Loading user info...', 'info');
            try {
                const response = await fetch(`/me?access_token=${encodeURIComponent(accessToken)}`);
                const data = await response.json();
                showResult(JSON.stringify(data, null, 2), 'success');
            } catch (error) {
                showResult(`Error: ${error.message}`, 'error');
            }
        }
        
        async function refreshAccessToken() {
            const refreshToken = document.getElementById('refreshToken').value;
            if (!refreshToken) {
                showResult('Please enter a refresh token', 'error');
                return;
            }
            
            showResult('Refreshing token...', 'info');
            try {
                const response = await fetch(`/refresh?refresh_token=${encodeURIComponent(refreshToken)}`);
                const data = await response.json();
                
                if (data.access_token) {
                    document.getElementById('accessToken').value = data.access_token;
                    if (data.refresh_token) {
                        document.getElementById('refreshToken').value = data.refresh_token;
                    }
                }
                
                showResult(JSON.stringify(data, null, 2), 'success');
                document.getElementById('tokenSection').style.display = 'block';
            } catch (error) {
                showResult(`Error: ${error.message}`, 'error');
            }
        }
        
        function showResult(message, type = 'info') {
            const resultsDiv = document.getElementById('results');
            let className = '';
            
            if (type === 'error') className = 'error';
            if (type === 'success') className = 'success';
            
            if (message.startsWith('{') || message.startsWith('[')) {
                resultsDiv.innerHTML = `<pre>${message}</pre>`;
                
                // Show token input sections if we got tokens
                try {
                    const data = JSON.parse(message);
                    if (data.access_token) {
                        document.getElementById('tokenSection').style.display = 'block';
                        document.getElementById('accessToken').value = data.access_token;
                    }
                    if (data.refresh_token) {
                        document.getElementById('refreshSection').style.display = 'block';
                        document.getElementById('refreshToken').value = data.refresh_token;
                    }
                } catch (e) {}
            } else {
                resultsDiv.innerHTML = `<div class="${className}">${message}</div>`;
            }
        }
    </script>
</body>
</html>
"""

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    @app.get("/", response_class=HTMLResponse)
    def missing_config():
        return "<h1>Error: Missing ONSHAPE_CLIENT_ID / ONSHAPE_CLIENT_SECRET / REDIRECT_URI in env</h1>"
else:
    # Serve the single HTML file
    @app.get("/", response_class=HTMLResponse)
    def root():
        return HTML_CONTENT

    @app.get("/api/status")
    def api_status():
        return {"message": "Onshape OAuth API running", "status": "ok"}

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

    @app.get("/callback", response_class=HTMLResponse)
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
        
        # Return HTML page with tokens displayed
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Success</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                h1 {{ color: #28a745; }}
                pre {{
                    background: #2d2d2d;
                    color: #f8f8f2;
                    padding: 15px;
                    border-radius: 4px;
                    overflow-x: auto;
                }}
                button {{
                    padding: 12px 24px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }}
                button:hover {{
                    background: #5568d3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Login Successful!</h1>
                <p>Your tokens:</p>
                <pre>{json.dumps(token_data, indent=2)}</pre>
                <button onclick="window.location.href='/'">Back to Home</button>
            </div>
        </body>
        </html>
        """

    @app.get("/me")
    def me(access_token: str = None):
        if not access_token:
            return {"error": "Provide access_token as query param"}

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
