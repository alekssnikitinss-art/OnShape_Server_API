"""Document Routes"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db, User, SavedDocument
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/list")
async def list_documents(user_id: str, db: Session = Depends(get_db)):
    """List user's OnShape documents"""
    try:
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        documents = service.get_documents()
        return {"status": "success", "documents": documents}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/{doc_id}/elements")
async def get_elements(doc_id: str, workspace_id: str, user_id: str, db: Session = Depends(get_db)):
    """Get elements in a document"""
    try:
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        elements = service.get_elements(doc_id, workspace_id)
        return {"status": "success", "elements": elements}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/save")
async def save_document(request: Request, db: Session = Depends(get_db)):
    """Save document to user's library"""
    data = await request.json()
    user_id = data.get("user_id")
    document_id = data.get("document_id")
    workspace_id = data.get("workspace_id")
    element_id = data.get("element_id")
    document_name = data.get("document_name", "Unnamed")
    element_name = data.get("element_name")
    element_type = data.get("element_type")
    
    if not user_id or not document_id:
        raise HTTPException(400, "Missing required fields")
    
    # Check if already saved
    saved = db.query(SavedDocument).filter(
        SavedDocument.user_id == user_id,
        SavedDocument.document_id == document_id,
        SavedDocument.element_id == element_id
    ).first()
    
    if saved:
        saved.last_used_at = datetime.utcnow()
        saved.document_name = document_name
        saved.element_name = element_name
    else:
        saved = SavedDocument(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_id=document_id,
            workspace_id=workspace_id,
            element_id=element_id,
            document_name=document_name,
            element_name=element_name,
            element_type=element_type
        )
        db.add(saved)
    
    db.commit()
    return {"status": "success", "message": "Document saved"}

@router.get("/saved")
async def get_saved_documents(user_id: str, db: Session = Depends(get_db)):
    """Get user's saved documents"""
    docs = db.query(SavedDocument).filter(
        SavedDocument.user_id == user_id
    ).order_by(SavedDocument.last_used_at.desc()).all()
    
    return {"status": "success", "documents": [d.to_dict() for d in docs]}

