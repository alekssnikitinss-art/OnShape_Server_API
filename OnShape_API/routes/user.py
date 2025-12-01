"""User Routes"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db, User
from services.auth_service import AuthService

router = APIRouter()

@router.get("/info")
async def get_user_info(user_id: str, db: Session = Depends(get_db)):
    """Get user information"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat()
    }
