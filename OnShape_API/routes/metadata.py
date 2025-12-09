"""
routes/metadata.py - Metadata Read/Write Endpoints
Properly implements OnShape metadata operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.metadata_service import MetadataService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= GET METADATA =============

@router.get("/get")
async def get_metadata(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    part_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific part
    Shows all custom properties and their IDs
    """
    try:
        if not all([doc_id, workspace_id, element_id, part_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📖 Getting metadata for part: {part_id}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = MetadataService(token)
        
        metadata = service.get_part_metadata(doc_id, workspace_id, element_id, part_id)
        
        if metadata is None:
            return {
                "status": "info",
                "data": {
                    "partId": part_id,
                    "properties": [],
                    "propertyCount": 0
                },
                "message": "Part has no custom properties defined. Define properties in OnShape UI first."
            }
        
        properties = metadata.get("items", [{}])[0].get("properties", [])
        
        return {
            "status": "success",
            "data": {
                "partId": part_id,
                "properties": properties,
                "propertyCount": len(properties),
                "rawMetadata": metadata
            },
            "message": f"Retrieved {len(properties)} custom properties"
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= UPDATE METADATA =============

@router.post("/update")
async def update_metadata(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update custom properties for a part
    
    Request body:
    {
        "user_id": "...",
        "doc_id": "...",
        "workspace_id": "...",
        "element_id": "...",
        "part_id": "...",
        "updates": {
            "propertyId_1": "new_value_1",
            "propertyId_2": "new_value_2"
        }
    }
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        part_id = data.get("part_id")
        updates = data.get("updates", {})
        
        if not all([user_id, doc_id, workspace_id, element_id, part_id]):
            raise HTTPException(400, "Missing required parameters")
        
        if not updates:
            raise HTTPException(400, "No updates provided")
        
        logger.info(f"✏️ Updating metadata for part {part_id}")
        logger.info(f"   Updates: {updates}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = MetadataService(token)
        
        success = service.update_part_metadata(
            doc_id,
            workspace_id,
            element_id,
            part_id,
            updates
        )
        
        if success:
            return {
                "status": "success",
                "data": {
                    "partId": part_id,
                    "updated": True,
                    "updates": updates
                },
                "message": f"Successfully updated {len(updates)} properties"
            }
        else:
            return {
                "status": "error",
                "data": {
                    "partId": part_id,
                    "updated": False
                },
                "message": "Failed to update metadata. Check logs for details."
            }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= BATCH UPDATE =============

@router.post("/batch-update")
async def batch_update_metadata(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update metadata for multiple parts
    
    Request body:
    {
        "user_id": "...",
        "doc_id": "...",
        "workspace_id": "...",
        "element_id": "...",
        "parts": [
            {
                "partId": "part_1",
                "updates": {
                    "propertyId": "new_value"
                }
            },
            {
                "partId": "part_2",
                "updates": {
                    "propertyId": "new_value"
                }
            }
        ]
    }
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        parts = data.get("parts", [])
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required parameters")
        
        if not parts:
            raise HTTPException(400, "No parts provided")
        
        logger.info(f"📝 Batch updating {len(parts)} parts")
        
        token = AuthService.get_valid_token(db, user_id)
        service = MetadataService(token)
        
        # Convert parts list to expected format
        parts_updates = []
        for part in parts:
            parts_updates.append({
                "partId": part.get("partId"),
                "updates": part.get("updates", {})
            })
        
        results = service.update_multiple_parts(
            doc_id,
            workspace_id,
            element_id,
            parts_updates
        )
        
        success_count = sum(1 for v in results.values() if v)
        
        return {
            "status": "success" if success_count > 0 else "partial",
            "data": {
                "totalParts": len(parts),
                "successCount": success_count,
                "results": results
            },
            "message": f"Updated {success_count}/{len(parts)} parts"
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= HEALTH CHECK =============

@router.get("/health")
async def metadata_health():
    """Health check"""
    return {"status": "healthy", "service": "metadata"}