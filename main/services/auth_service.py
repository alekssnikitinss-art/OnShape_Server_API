from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import base64
import requests
from config import settings
from sqlalchemy.orm import Session
from database import User

cipher = Fernet(settings.ENCRYPTION_KEY.encode()) if settings.ENCRYPTION_KEY else None

class AuthService:
    @staticmethod
    def encrypt_token(token: str) -> str:
        """Encrypt token"""
        if not cipher or not token:
            return token
        return cipher.encrypt(token.encode()).decode()
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Decrypt token"""
        if not cipher or not encrypted_token:
            return encrypted_token
        return cipher.decrypt(encrypted_token.encode()).decode()
    
    @staticmethod
    def get_oauth_url(state: str = "state123") -> str:
        """Get OAuth URL"""
        params = {
            "response_type": "code",
            "client_id": settings.ONSHAPE_CLIENT_ID,
            "redirect_uri": settings.ONSHAPE_REDIRECT_URI,
            "scope": settings.ONSHAPE_SCOPE,
            "state": state
        }
        from urllib.parse import urlencode
        return settings.ONSHAPE_AUTH_URL + "?" + urlencode(params)
    
    @staticmethod
    def exchange_code_for_token(code: str) -> dict:
        """Exchange authorization code for tokens"""
        auth_header = base64.b64encode(
            f"{settings.ONSHAPE_CLIENT_ID}:{settings.ONSHAPE_CLIENT_SECRET}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.ONSHAPE_REDIRECT_URI
        }
        
        response = requests.post(settings.ONSHAPE_TOKEN_URL, headers=headers, data=data, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        
        return response.json()
    
    @staticmethod
    def get_user_info(access_token: str) -> dict:
        """Get user info from OnShape"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/users/session",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.text}")
        
        return response.json()
    
    @staticmethod
    def save_user(db: Session, onshape_id: str, email: str, name: str, token_data: dict) -> User:
        """Save or update user in database"""
        user = db.query(User).filter(User.onshape_id == onshape_id).first()
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        if user:
            user.email = email
            user.name = name
            user.access_token = AuthService.encrypt_token(access_token)
            user.refresh_token = AuthService.encrypt_token(refresh_token) if refresh_token else None
            user.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            user.last_login = datetime.utcnow()
        else:
            user = User(
                onshape_id=onshape_id,
                email=email,
                name=name,
                access_token=AuthService.encrypt_token(access_token),
                refresh_token=AuthService.encrypt_token(refresh_token) if refresh_token else None,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_valid_token(db: Session, user_id: str) -> str:
        """Get valid access token for user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception("User not found")
        
        if user.is_token_expired():
            raise Exception("Token expired - please login again")
        
        return AuthService.decrypt_token(user.access_token)
