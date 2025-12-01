"""BOM Routes"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService

router = APIRouter()

@router.get("/fetch")
async def fetch_bom(
    doc_id: str,
    workspace_id: str,
    element_id: str,
    user_id: str,
    indented: bool = False,
    db: Session = Depends(get_db)
):
    """Fetch BOM from OnShape"""
    try:
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=indented)
        
        # Process BOM items
        if "bomTable" in bom_data and "items" in bom_data["bomTable"]:
            bom_data["bomTable"]["items"] = BOMService.process_bom_items(
                bom_data["bomTable"]["items"]
            )
        
        return {"status": "success", "data": bom_data}
    except Exception as e:
        raise HTTPException(400, str(e))


