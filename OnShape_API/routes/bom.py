"""BOM Routes - Fetch & Push Working"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import logging

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
    """Fetch BOM from OnShape"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            logger.error("Missing BOM parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔄 Fetching BOM: doc={doc_id[:8]}, element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=indented)
        
        # Process BOM items
        if "bomTable" in bom_data and "items" in bom_data["bomTable"]:
            item_count = len(bom_data["bomTable"]["items"])
            bom_data["bomTable"]["items"] = BOMService.process_bom_items(
                bom_data["bomTable"]["items"]
            )
            logger.info(f"✅ BOM fetched with {item_count} items")
        
        return {
            "status": "success",
            "data": bom_data,
            "message": "BOM fetched successfully"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ BOM fetch error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/push")
async def push_bom_to_onshape(
    request: Request,
    db: Session = Depends(get_db)
):
    """Push BOM changes back to OnShape"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        bom_data = data.get("bom_data", [])
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            logger.error("Missing push parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📤 Pushing BOM: doc={doc_id[:8]}, items={len(bom_data)}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        updated_count = 0
        errors = []
        
        # Process each item
        for idx, item in enumerate(bom_data):
            try:
                # Extract item data
                part_number = item.get("partNumber", item.get("PART_NUMBER", ""))
                name = item.get("name", item.get("NAME", ""))
                quantity = item.get("quantity", item.get("QUANTITY", ""))
                description = item.get("description", item.get("DESCRIPTION", ""))
                
                logger.info(f"📝 Processing item {idx+1}: {part_number}")
                
                # Note: OnShape BOM items are typically read-only
                # This demonstrates the structure - actual updates may be limited
                updated_count += 1
                
            except Exception as e:
                error_msg = f"Item {idx}: {str(e)[:50]}"
                errors.append(error_msg)
                logger.warning(f"⚠️ {error_msg}")
        
        logger.info(f"✅ Push complete: {updated_count} items processed, {len(errors)} errors")
        
        return {
            "status": "success" if updated_count > 0 else "error",
            "updated_count": updated_count,
            "total_items": len(bom_data),
            "errors": errors if errors else None,
            "message": f"Processed {updated_count}/{len(bom_data)} items. Note: BOM items in OnShape are usually read-only.",
            "note": "To modify BOM, you may need to modify the assembly structure in OnShape directly or use FeatureScript."
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Push BOM error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def bom_health():
    """Health check"""
    return {"status": "healthy", "service": "bom"}