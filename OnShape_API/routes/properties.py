"""Properties Routes - Variables & Bounding Boxes with Better Debugging"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import logging
import traceback

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
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            logger.error(f"❌ Token error: {str(e)}")
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            logger.info(f"🔄 Calling OnShape API...")
            bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
            logger.info(f"📊 Raw response type: {type(bboxes)}, content: {str(bboxes)[:200]}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ OnShape API error: {error_msg}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(400, f"OnShape API error: {error_msg}")
        
        if not bboxes:
            logger.warning("⚠️ Empty bboxes response from OnShape")
            raise HTTPException(400, "No bounding boxes found. This might be an Assembly (not PartStudio) or empty element.")
        
        logger.info(f"✅ Got {len(bboxes) if isinstance(bboxes, list) else '?'} bboxes from OnShape")
        
        # Process each bounding box
        processed = []
        for idx, bbox in enumerate(bboxes):
            try:
                logger.info(f"📝 Processing bbox {idx+1}: {str(bbox)[:100]}")
                
                # Safely calculate dimensions
                if isinstance(bbox, dict):
                    dimensions = BOMService.calculate_dimensions(bbox)
                    bbox["dimensions"] = dimensions
                    processed.append(bbox)
                    logger.info(f"✅ Bbox {idx+1}: L={dimensions['length']}, W={dimensions['width']}, H={dimensions['height']}")
                else:
                    logger.warning(f"⚠️ Bbox {idx+1} is not a dict: {type(bbox)}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not process bbox {idx+1}: {str(e)}")
                try:
                    bbox["dimensions"] = {"length": 0, "width": 0, "height": 0, "volume": 0}
                    processed.append(bbox)
                except:
                    pass
        
        logger.info(f"✅ Successfully processed {len(processed)} bounding boxes")
        
        return {
            "status": "success",
            "data": processed,
            "count": len(processed),
            "message": f"Retrieved {len(processed)} bounding boxes"
        }
    
    except HTTPException as e:
        logger.error(f"HTTP {e.status_code}: {e.detail}")
        raise e
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Unexpected error: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(500, f"Unexpected error: {error_msg[:100]}")


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
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            logger.error(f"❌ Token error: {str(e)}")
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            logger.info(f"🔄 Calling OnShape API for variables...")
            config_data = service.get_configuration_variables(doc_id, workspace_id, element_id)
            logger.info(f"📊 Raw response: {str(config_data)[:200]}")
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ OnShape API error: {error_msg}")
            # Configuration might not exist - return empty but valid response
            return {
                "status": "info",
                "message": "Cannot retrieve configuration variables.",
                "note": "Configuration variables may not be available via OnShape REST API. This is a known limitation.",
                "data": None,
                "variables": [],
                "count": 0
            }
        
        # Process variables - handle different formats
        variables = []
        if isinstance(config_data, dict):
            logger.info(f"Config is dict with keys: {config_data.keys()}")
            if "parameters" in config_data:
                variables = config_data.get("parameters", [])
                logger.info(f"Found {len(variables)} in 'parameters'")
            elif "variables" in config_data:
                variables = config_data.get("variables", [])
                logger.info(f"Found {len(variables)} in 'variables'")
            elif "items" in config_data:
                variables = config_data.get("items", [])
                logger.info(f"Found {len(variables)} in 'items'")
            else:
                # Entire response might be the variables
                variables = config_data
                logger.info(f"Returning entire dict as variables")
        elif isinstance(config_data, list):
            variables = config_data
            logger.info(f"Config is list with {len(variables)} items")
        
        logger.info(f"✅ Retrieved {len(variables) if isinstance(variables, list) else '?'} configuration variables")
        
        # Check if empty
        if not variables or (isinstance(variables, list) and len(variables) == 0):
            return {
                "status": "info",
                "message": "No configuration variables found.",
                "note": "Configuration variables may not be available via OnShape REST API. This is a known limitation - they might only be accessible via the OnShape UI.",
                "data": config_data,
                "variables": [],
                "count": 0
            }
        
        return {
            "status": "success",
            "data": config_data,
            "variables": variables if isinstance(variables, list) else [],
            "count": len(variables) if isinstance(variables, list) else 0,
            "message": f"Retrieved {len(variables) if isinstance(variables, list) else 0} configuration variables"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Configuration error: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Don't crash - return empty response
        return {
            "status": "info",
            "message": f"Could not retrieve configuration: {error_msg[:100]}",
            "note": "Configuration variables may not be available via OnShape REST API",
            "data": None,
            "variables": [],
            "count": 0
        }


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
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            logger.error(f"❌ Token error: {str(e)}")
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            logger.info(f"🔄 Getting bounding boxes...")
            bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        except Exception as e:
            logger.error(f"❌ Bounding boxes error: {str(e)}")
            raise HTTPException(400, f"Failed to get bounding boxes: {str(e)[:100]}")
        
        if not bboxes:
            logger.warning("⚠️ No bounding boxes found")
            raise HTTPException(400, "No parts found in this PartStudio")
        
        logger.info(f"📊 Found {len(bboxes)} parts to process")
        
        updated_count = 0
        errors = []
        
        # Process each bounding box
        for idx, bbox in enumerate(bboxes):
            try:
                part_id = bbox.get("partId")
                if not part_id:
                    logger.warning(f"⚠️ Part {idx+1} has no partId")
                    continue
                
                # Calculate dimensions
                logger.info(f"📝 Part {idx+1}/{len(bboxes)}: Calculating dimensions...")
                dimensions = BOMService.calculate_dimensions(bbox)
                logger.info(f"✅ Dimensions: L={dimensions['length']}, W={dimensions['width']}, H={dimensions['height']}")
                
                # Create property objects
                properties = BOMService.create_property_objects(dimensions)
                logger.info(f"📤 Updating metadata for part {part_id[:12]}")
                
                # Update metadata
                try:
                    service.update_metadata(doc_id, workspace_id, element_id, part_id, properties)
                    updated_count += 1
                    logger.info(f"✅ Updated part {idx+1}")
                except Exception as e:
                    error_msg = f"Part {part_id[:8]}: {str(e)[:50]}"
                    errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
            
            except Exception as e:
                error_msg = f"Part {idx}: {str(e)[:50]}"
                errors.append(error_msg)
                logger.warning(f"⚠️ {error_msg}")
        
        logger.info(f"✅ Length properties complete: {updated_count}/{len(bboxes)} success, {len(errors)} errors")
        
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
        error_msg = str(e)
        logger.error(f"❌ Create length properties error: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(500, f"Unexpected error: {error_msg[:100]}")


@router.get("/health")
async def properties_health():
    """Health check"""
    return {"status": "healthy", "service": "properties"}