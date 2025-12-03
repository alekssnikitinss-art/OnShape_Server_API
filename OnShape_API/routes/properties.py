"""Properties Routes - Variables & Bounding Boxes"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/bounding-boxes")
async def get_bounding_boxes(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get bounding boxes for all parts in PartStudio"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            logger.error("Missing bbox parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📏 Getting bounding boxes: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get bounding boxes
        try:
            bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        except Exception as e:
            logger.warning(f"⚠️ Could not get bounding boxes: {str(e)}")
            # This element might be an Assembly, not PartStudio
            raise HTTPException(400, f"Could not get bounding boxes. This endpoint works with PartStudios only. Error: {str(e)[:100]}")
        
        # Calculate dimensions
        processed = []
        for bbox in bboxes:
            try:
                dimensions = BOMService.calculate_dimensions(bbox)
                bbox["dimensions"] = dimensions
                processed.append(bbox)
            except Exception as e:
                logger.warning(f"Could not calculate dimensions: {str(e)}")
                bbox["dimensions"] = {"length": 0, "width": 0, "height": 0, "volume": 0}
                processed.append(bbox)
        
        logger.info(f"✅ Retrieved {len(processed)} bounding boxes")
        
        return {
            "status": "success",
            "data": processed,
            "count": len(processed),
            "message": f"Retrieved {len(processed)} bounding boxes"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Bounding boxes error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/configuration")
async def get_configuration_variables(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get configuration variables for element"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            logger.error("Missing config parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📋 Getting configuration variables: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get configuration
        try:
            config_data = service.get_configuration_variables(doc_id, workspace_id, element_id)
        except Exception as e:
            logger.warning(f"⚠️ Could not get variables: {str(e)}")
            return {
                "status": "error",
                "message": f"This element may not have configuration variables or the feature is not available. Error: {str(e)[:100]}",
                "data": None
            }
        
        # Process variables if they exist
        variables = []
        if isinstance(config_data, dict):
            if "parameters" in config_data:
                variables = config_data.get("parameters", [])
            elif "variables" in config_data:
                variables = config_data.get("variables", [])
            elif isinstance(config_data, list):
                variables = config_data
        elif isinstance(config_data, list):
            variables = config_data
        
        logger.info(f"✅ Retrieved {len(variables)} configuration variables")
        
        return {
            "status": "success" if variables else "info",
            "data": config_data,
            "variables": variables,
            "count": len(variables),
            "message": f"Retrieved {len(variables)} configuration variables" if variables else "No configuration variables found"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Configuration error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/create-length-properties")
async def create_length_properties(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create Length, Width, Height properties from bounding boxes"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            logger.error("Missing length properties parameters")
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📐 Creating length properties: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get bounding boxes
        try:
            bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        except Exception as e:
            logger.error(f"❌ Could not get bounding boxes: {str(e)}")
            raise HTTPException(400, f"Failed to get bounding boxes: {str(e)[:100]}")
        
        if not bboxes:
            logger.warning("⚠️ No bounding boxes found")
            raise HTTPException(400, "No parts found in this PartStudio")
        
        updated_count = 0
        errors = []
        
        # Process each bounding box
        for idx, bbox in enumerate(bboxes):
            try:
                part_id = bbox.get("partId")
                if not part_id:
                    logger.warning(f"⚠️ Bbox {idx} has no partId")
                    continue
                
                # Calculate dimensions
                dimensions = BOMService.calculate_dimensions(bbox)
                logger.info(f"📝 Part {idx+1}: Length={dimensions['length']}, Width={dimensions['width']}, Height={dimensions['height']}")
                
                # Create property objects
                properties = BOMService.create_property_objects(dimensions)
                
                # Update metadata
                try:
                    service.update_metadata(doc_id, workspace_id, element_id, part_id, properties)
                    updated_count += 1
                    logger.info(f"✅ Updated part {idx+1}: {part_id[:12]}")
                except Exception as e:
                    error_msg = f"Part {part_id[:8]}: {str(e)[:50]}"
                    errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
            
            except Exception as e:
                error_msg = f"Bbox {idx}: {str(e)[:50]}"
                errors.append(error_msg)
                logger.warning(f"⚠️ {error_msg}")
        
        logger.info(f"✅ Length properties complete: {updated_count}/{len(bboxes)} success")
        
        return {
            "status": "success" if updated_count > 0 else "partial",
            "updated_count": updated_count,
            "total_parts": len(bboxes),
            "errors": errors if errors else None,
            "message": f"Successfully updated {updated_count}/{len(bboxes)} parts"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Create length properties error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def properties_health():
    """Health check"""
    return {"status": "healthy", "service": "properties"}