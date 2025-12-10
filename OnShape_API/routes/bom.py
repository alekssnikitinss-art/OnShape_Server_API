"""BOM Routes - Fetch Working"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/fetch")
async def fetch_bom(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    indented: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Fetch BOM from OnShape - handles both Assemblies and PartStudios"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            logger.error("Missing BOM parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔄 Fetching BOM: doc={doc_id[:8]}, element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # This will try Assembly first, then PartStudio
        bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=indented)
        
        logger.info(f"📊 BOM data type: {bom_data.get('type', 'Assembly')}")
        
        # Process BOM items if they exist
        if "bomTable" in bom_data and "items" in bom_data["bomTable"]:
            item_count = len(bom_data["bomTable"]["items"])
            bom_data["bomTable"]["items"] = BOMService.process_bom_items(
                bom_data["bomTable"]["items"]
            )
            logger.info(f"✅ BOM fetched with {item_count} items")
        
        return {
            "status": "success",
            "data": bom_data,
            "message": f"BOM fetched successfully ({bom_data.get('type', 'Assembly')})"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ BOM fetch error: {str(e)}")
        raise HTTPException(500, f"BOM fetch failed: {str(e)[:100]}")


@router.get("/health")
async def bom_health():
    """Health check for BOM service"""
    return {
        "status": "healthy",
        "service": "bom",
        "version": "1.0"
    }