"""
routes/properties.py - Properties, Bounding Boxes, and Configuration Variables
Handles all property-related endpoints including bounding boxes and variables
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
from services.bom_conversion import BOMConversionService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= BOUNDING BOXES =============

@router.get("/bounding-boxes")
async def get_bounding_boxes(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get bounding boxes for parts (PartStudio or Assembly)
    Returns dimensions in millimeters
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📏 Fetching bounding boxes for element: {element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # This will try PartStudio first, then Assembly
        bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        
        # Process bounding boxes and calculate dimensions
        processed_bboxes = []
        for bbox in bboxes:
            # Check if already has dimensions
            if "dimensions" in bbox:
                processed = bbox
            else:
                # Calculate from raw bbox
                dims = BOMService.calculate_dimensions(bbox)
                processed = {
                    **bbox,
                    "Length X (mm)": dims["length"],
                    "Length Y (mm)": dims["width"],
                    "Length Z (mm)": dims["height"],
                    "Volume (mm³)": dims["volume"],
                    "Part ID": bbox.get("partId") or bbox.get("id") or "Unknown"
                }
            
            processed_bboxes.append(processed)
        
        logger.info(f"✅ Retrieved {len(processed_bboxes)} bounding boxes")
        
        return {
            "status": "success",
            "data": processed_bboxes,
            "count": len(processed_bboxes),
            "message": f"Retrieved {len(processed_bboxes)} bounding boxes"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting bounding boxes: {str(e)}")
        raise HTTPException(500, f"Failed to get bounding boxes: {str(e)[:100]}")


# ============= CONFIGURATION VARIABLES =============

@router.get("/configuration")
async def get_configuration_variables(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get configuration variables from PartStudio
    Variables are user-defined parameters that can drive feature dimensions
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📋 Fetching configuration variables: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get variables from OnShape
        var_data = service.get_configuration_variables(doc_id, workspace_id, element_id)
        
        # Parse response based on format
        variables = []
        if "variables" in var_data:
            variables = var_data.get("variables", [])
        elif isinstance(var_data, list):
            variables = var_data
        elif isinstance(var_data, dict) and "items" in var_data:
            variables = var_data.get("items", [])
        
        logger.info(f"✅ Retrieved {len(variables)} configuration variables")
        
        return {
            "status": "success",
            "data": {
                "variables": variables,
                "count": len(variables),
                "element_id": element_id
            },
            "message": f"Retrieved {len(variables)} configuration variables"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting configuration variables: {str(e)}")
        # Return info status instead of error for missing variables
        return {
            "status": "info",
            "data": {
                "variables": [],
                "count": 0,
                "element_id": element_id,
                "message": "No configuration variables found or feature not available"
            },
            "message": "Configuration variables not available for this element"
        }


# ============= CREATE LENGTH PROPERTIES =============

@router.post("/create-length-properties")
async def create_length_properties(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create custom Length, Width, Height properties from bounding boxes
    This will add properties to all parts in the element in OnShape
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📐 Creating length properties from bounding boxes")
        logger.info(f"   Element: {element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get bounding boxes
        bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
        
        if not bboxes:
            return {
                "status": "error",
                "message": "No bounding boxes found",
                "updated_count": 0,
                "total_parts": 0
            }
        
        logger.info(f"📦 Processing {len(bboxes)} parts...")
        
        # Get metadata service
        from services.metadata_service import MetadataService
        metadata_service = MetadataService(token)
        
        errors = []
        updated_count = 0
        
        for idx, bbox in enumerate(bboxes, 1):
            try:
                part_id = bbox.get("partId") or bbox.get("id")
                if not part_id:
                    logger.warning(f"   Part {idx}: No ID found, skipping")
                    continue
                
                # Calculate dimensions
                dims = BOMService.calculate_dimensions(bbox)
                
                # Get current metadata to find property IDs
                try:
                    current_metadata = metadata_service.get_part_metadata(
                        doc_id, workspace_id, element_id, part_id
                    )
                    
                    if current_metadata and "items" in current_metadata:
                        items = current_metadata["items"]
                        if items and len(items) > 0:
                            properties = items[0].get("properties", [])
                            
                            # Find existing property IDs
                            prop_updates = {}
                            for prop in properties:
                                prop_name = prop.get("name", "")
                                prop_id = prop.get("propertyId")
                                
                                if prop_name == "Length" and "length" in dims:
                                    prop_updates[prop_id] = str(dims["length"])
                                elif prop_name == "Width" and "width" in dims:
                                    prop_updates[prop_id] = str(dims["width"])
                                elif prop_name == "Height" and "height" in dims:
                                    prop_updates[prop_id] = str(dims["height"])
                            
                            # Update properties
                            if prop_updates:
                                success = metadata_service.update_part_metadata(
                                    doc_id, workspace_id, element_id, part_id, prop_updates
                                )
                                if success:
                                    updated_count += 1
                                    logger.info(f"   Part {idx} ({part_id[:8]}): ✅ Updated")
                                else:
                                    logger.warning(f"   Part {idx}: Update failed")
                                    errors.append(f"Part {part_id}: Update failed")
                except Exception as e:
                    logger.warning(f"   Part {idx}: Could not update - {str(e)}")
                    errors.append(f"Part {part_id}: {str(e)[:50]}")
            
            except Exception as e:
                logger.error(f"   Part {idx}: Error - {str(e)}")
                errors.append(f"Part {idx}: {str(e)[:50]}")
        
        logger.info(f"📊 Completed: {updated_count}/{len(bboxes)} parts updated")
        
        return {
            "status": "success" if updated_count > 0 else "partial",
            "message": f"Updated {updated_count}/{len(bboxes)} parts with length properties",
            "updated_count": updated_count,
            "total_parts": len(bboxes),
            "errors": errors if errors else None
        }
    
    except Exception as e:
        logger.error(f"❌ Error creating length properties: {str(e)}")
        raise HTTPException(500, f"Failed to create length properties: {str(e)[:100]}")


# ============= HEALTH CHECK =============

@router.get("/health")
async def properties_health():
    """Health check for properties service"""
    return {
        "status": "healthy",
        "service": "properties",
        "endpoints": [
            "bounding-boxes",
            "configuration",
            "create-length-properties"
        ]
    }