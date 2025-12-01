"""Authentication Routes"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService

router = APIRouter()

@router.get("/login")
async def login():
    """Redirect to OnShape OAuth"""
    url = AuthService.get_oauth_url()
    return RedirectResponse(url)

@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback"""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        return f"<h1>Error: {error}</h1><a href='/'>Back</a>"
    
    if not code:
        return "<h1>Missing code</h1><a href='/'>Back</a>"
    
    try:
        # Exchange code for tokens
        token_data = AuthService.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        # Get user info
        user_info = AuthService.get_user_info(access_token)
        
        # Save user
        user = AuthService.save_user(
            db,
            onshape_id=user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name", ""),
            token_data=token_data
        )
        
        # Success page
        return f"""
        <html>
        <body style='font-family:Arial;padding:50px;text-align:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)'>
            <div style='background:white;padding:40px;border-radius:12px;max-width:500px;margin:0 auto'>
                <h1 style='color:green'>✅ Success!</h1>
                <p>Logged in as <strong>{user.email}</strong></p>
                <p>Redirecting...</p>
                <script>
                    localStorage.setItem('userId', '{user.id}');
                    setTimeout(() => window.location.href = '/', 2000);
                </script>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1><a href='/'>Back</a>"

@router.post("/logout")
async def logout():
    """Logout user"""
    return {"status": "success", "message": "Logged out"}
