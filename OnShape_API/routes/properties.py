from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService

router = APIRouter()

@router.get("/bounding-boxes")
async def get_bounding_boxes(
    doc_id: str,
    workspace_id: str,
    element_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get bounding boxes"""
    try:
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        
        # Add dimension calculations
        for bbox in bboxes:
            bbox["dimensions"] = BOMService.calculate_dimensions(bbox)
        
        return {"status": "success", "data": bboxes}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/create-length-properties")
async def create_length_properties(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create Length, Width, Height properties for all parts"""
    data = await request.json()
    user_id = data.get("user_id")
    doc_id = data.get("doc_id")
    workspace_id = data.get("workspace_id")
    element_id = data.get("element_id")
    
    if not all([user_id, doc_id, workspace_id, element_id]):
        raise HTTPException(400, "Missing required fields")
    
    try:
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get bounding boxes
        bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        updated_count = 0
        errors = []
        
        for bbox in bboxes:
            try:
                part_id = bbox.get("partId")
                if not part_id:
                    continue
                
                # Calculate dimensions
                dimensions = BOMService.calculate_dimensions(bbox)
                
                # Create property objects
                properties = BOMService.create_property_objects(dimensions)
                
                # Update metadata
                service.update_metadata(doc_id, workspace_id, element_id, part_id, properties)
                updated_count += 1
            except Exception as e:
                errors.append(f"Part {part_id}: {str(e)}")
        
        return {
            "status": "success" if updated_count > 0 else "error",
            "updated_count": updated_count,
            "errors": errors[:10] if errors else None
        }
    except Exception as e:
        raise HTTPException(400, str(e))