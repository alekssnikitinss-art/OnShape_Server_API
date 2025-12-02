"""
Authentication Routes
OAuth login and callback handling
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db, User
from services.auth_service import AuthService

router = APIRouter()

@router.get("/login")
async def login():
    """Redirect to OnShape OAuth"""
    url = AuthService.get_oauth_url()
    return RedirectResponse(url)

@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback from OnShape"""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    error_desc = request.query_params.get("error_description")
    
    if error:
        return f"""
        <html>
        <head><title>Error</title></head>
        <body style='font-family:Arial;padding:50px;text-align:center;'>
            <h1>❌ Authentication Error</h1>
            <p><strong>Error:</strong> {error}</p>
            <p><strong>Description:</strong> {error_desc}</p>
            <p><a href='/'>Back to Home</a></p>
        </body>
        </html>
        """
    
    if not code:
        return """
        <html>
        <head><title>Error</title></head>
        <body style='font-family:Arial;padding:50px;text-align:center;'>
            <h1>❌ Missing Code</h1>
            <p>No authorization code received from OnShape.</p>
            <p><a href='/'>Back to Home</a></p>
        </body>
        </html>
        """
    
    try:
        # Exchange code for tokens
        token_data = AuthService.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        # Get user info
        user_info = AuthService.get_user_info(access_token)
        
        # Save user to database
        user = AuthService.save_user(
            db,
            onshape_id=user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name", ""),
            token_data=token_data
        )
        
        # Success page with redirect
        return f"""
        <html>
        <body style='font-family:Arial;padding:50px;text-align:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;'>
            <div style='background:white;padding:40px;border-radius:12px;max-width:500px;margin:0 auto;'>
                <h1 style='color:green;'>✅ Success!</h1>
                <p>Logged in as <strong>{user.email}</strong></p>
                <p>Redirecting...</p>
                <script>
                    localStorage.setItem('userId', '{user.id}');
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 2000);
                </script>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return f"""
        <html>
        <head><title>Error</title></head>
        <body style='font-family:Arial;padding:50px;text-align:center;'>
            <h1>❌ Server Error</h1>
            <p><strong>Error:</strong> {str(e)[:200]}</p>
            <p><a href='/'>Back to Home</a></p>
        </body>
        </html>
        """

@router.post("/logout")
async def logout():
    """Logout user"""
    return {"status": "success", "message": "Logged out"}