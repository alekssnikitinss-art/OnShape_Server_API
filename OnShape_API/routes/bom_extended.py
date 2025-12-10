"""
routes/bom_extended.py - Extended BOM operations (push, convert, calculate)
Handles unit conversion, volume calculation, and dimension operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
from services.bom_conversion import BOMConversionService
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= PUSH BOM TO ONSHAPE =============

@router.post("/push")
async def push_bom_to_onshape(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Push BOM changes back to OnShape
    Note: Many fields are read-only in OnShape API
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        bom_data = data.get("bom_data", [])
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required parameters")
        
        if not bom_data:
            raise HTTPException(400, "No BOM data provided")
        
        logger.info(f"📤 Pushing {len(bom_data)} BOM items to OnShape")
        logger.info(f"   Element: {element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # OnShape BOM push is complex - most fields are read-only
        # This is a best-effort implementation
        errors = []
        updated_count = 0
        
        for idx, item in enumerate(bom_data):
            try:
                logger.debug(f"   Item {idx + 1}: {item.get('name', 'Unknown')}")
                # Most BOM fields cannot be updated via API
                # Only custom properties can be updated
                # This is a limitation of OnShape API
                logger.warning(f"   Note: BOM fields are mostly read-only in OnShape API")
            except Exception as e:
                errors.append(f"Item {idx + 1}: {str(e)}")
        
        logger.info(f"📊 Push completed: {updated_count} items")
        
        return {
            "status": "info",
            "message": "BOM push initiated (Note: Most BOM fields are read-only in OnShape)",
            "updated_count": updated_count,
            "total_items": len(bom_data),
            "errors": errors if errors else None,
            "note": "Use /api/metadata/* endpoints to update custom properties instead"
        }
    
    except Exception as e:
        logger.error(f"❌ Error pushing BOM: {str(e)}")
        raise HTTPException(500, f"Failed to push BOM: {str(e)[:100]}")


# ============= UNIT CONVERSION =============

@router.post("/convert-unit")
async def convert_unit(request: Request):
    """
    Convert a value from one unit to millimeters
    
    Request body:
    {
        "value": "10",
        "unit": "in"
    }
    
    Supported units: mm, cm, m, in, ft, yd, µm
    """
    try:
        data = await request.json()
        value = data.get("value")
        unit = data.get("unit")
        
        if value is None or not unit:
            raise HTTPException(400, "Missing value or unit")
        
        try:
            numeric_value = float(value)
        except ValueError:
            raise HTTPException(400, f"Invalid numeric value: {value}")
        
        logger.info(f"🔄 Converting {numeric_value} {unit} to MM")
        
        # Convert to MM
        mm_value = BOMConversionService.convert_to_mm(numeric_value, unit)
        
        if mm_value is None:
            raise HTTPException(400, f"Unknown unit: {unit}")
        
        logger.info(f"✅ Converted: {mm_value} mm")
        
        return {
            "status": "success",
            "original": value,
            "unit": unit,
            "converted_mm": round(mm_value, 2),
            "message": f"{numeric_value} {unit} = {round(mm_value, 2)} mm"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Conversion error: {str(e)}")
        raise HTTPException(500, f"Conversion failed: {str(e)}")


# ============= CALCULATE VOLUME =============

@router.post("/calculate-volume")
async def calculate_volume(request: Request):
    """
    Calculate volume from three dimensions in millimeters
    
    Request body:
    {
        "length_mm": 100.0,
        "width_mm": 50.0,
        "height_mm": 25.0
    }
    
    Returns: Volume in mm³
    """
    try:
        data = await request.json()
        length = data.get("length_mm")
        width = data.get("width_mm")
        height = data.get("height_mm")
        
        if any(val is None for val in [length, width, height]):
            raise HTTPException(400, "Missing length_mm, width_mm, or height_mm")
        
        try:
            length = float(length)
            width = float(width)
            height = float(height)
        except ValueError:
            raise HTTPException(400, "Dimensions must be numeric")
        
        logger.info(f"📐 Calculating volume: {length}×{width}×{height} mm")
        
        # Calculate volume
        volume = BOMConversionService.calculate_volume_mm3(length, width, height)
        
        logger.info(f"✅ Volume: {volume} mm³")
        
        return {
            "status": "success",
            "length_mm": length,
            "width_mm": width,
            "height_mm": height,
            "volume_mm3": round(volume, 2),
            "message": f"Volume = {round(volume, 2)} mm³"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Volume calculation error: {str(e)}")
        raise HTTPException(500, f"Volume calculation failed: {str(e)}")


# ============= ADD DIMENSIONS TO BOM =============

@router.post("/add-dimensions-to-bom")
async def add_dimensions_to_bom(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Add dimension columns to BOM items from either:
    1. Manual input (length_values, width_values, height_values)
    2. Bounding boxes (fetched from OnShape)
    
    Request body:
    {
        "doc_id": "...",
        "workspace_id": "...",
        "element_id": "...",
        "user_id": "...",
        "length_values": ["10 mm", "20 in"],  // Optional
        "width_values": ["5 cm", "10 in"],
        "height_values": ["2.5 m", "5 in"],
        "use_bounding_boxes": true
    }
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        use_bbox = data.get("use_bounding_boxes", False)
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📝 Adding dimensions to BOM")
        logger.info(f"   Use bounding boxes: {use_bbox}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get BOM
        bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=False)
        
        if not bom_data or "bomTable" not in bom_data:
            raise HTTPException(400, "Could not fetch BOM")
        
        bom_items = bom_data.get("bomTable", {}).get("items", [])
        
        if not bom_items:
            raise HTTPException(400, "BOM has no items")
        
        logger.info(f"📦 Processing {len(bom_items)} BOM items")
        
        if use_bbox:
            # Get bounding boxes
            bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
            logger.info(f"   Fetched {len(bboxes)} bounding boxes")
            
            # Add bbox dimensions to BOM
            bom_items = BOMConversionService.add_bounding_box_dimensions_to_bom(
                bom_items, bboxes
            )
        else:
            # Manual dimensions
            length_values = data.get("length_values", [])
            width_values = data.get("width_values", [])
            height_values = data.get("height_values", [])
            
            logger.info(f"   Length values: {len(length_values)}")
            logger.info(f"   Width values: {len(width_values)}")
            logger.info(f"   Height values: {len(height_values)}")
            
            # Add manual dimensions
            bom_items = BOMConversionService.process_bom_with_dimensions(
                bom_items,
                length_values if length_values else None,
                width_values if width_values else None,
                height_values if height_values else None
            )
        
        logger.info(f"✅ Added dimensions to {len(bom_items)} items")
        
        return {
            "status": "success",
            "bom_items": bom_items,
            "items_count": len(bom_items),
            "message": f"Added dimensions to {len(bom_items)} BOM items"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error adding dimensions: {str(e)}")
        raise HTTPException(500, f"Failed to add dimensions: {str(e)[:100]}")


# ============= SUPPORTED UNITS =============

@router.get("/supported-units")
async def get_supported_units():
    """
    Get list of all supported units for conversion
    Returns conversion factors to millimeters
    """
    try:
        logger.info("📋 Fetching supported units")
        
        units = BOMConversionService.CONVERSION_FACTORS
        
        return {
            "status": "success",
            "supported_units": units,
            "count": len(units),
            "message": f"Found {len(units)} supported units"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting units: {str(e)}")
        raise HTTPException(500, str(e))


# ============= HEALTH CHECK =============

@router.get("/health")
async def bom_extended_health():
    """Health check for extended BOM service"""
    return {
        "status": "healthy",
        "service": "bom_extended",
        "endpoints": [
            "push",
            "convert-unit",
            "calculate-volume",
            "add-dimensions-to-bom",
            "supported-units"
        ]
    }