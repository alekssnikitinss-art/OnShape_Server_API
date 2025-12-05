"""
routes/bom_conversion.py - BOM Unit Conversion Endpoints
Add these endpoints to your app.py router includes
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

@router.post("/convert-unit")
async def convert_unit(request: Request):
    """
    Convert a value from one unit to millimeters
    
    Request body:
    {
        "value": "10",
        "unit": "in"
    }
    
    Returns: {
        "original": "10",
        "unit": "in",
        "converted_mm": 254.0,
        "summary": {...}
    }
    """
    try:
        data = await request.json()
        value = data.get("value")
        unit = data.get("unit")
        
        if not value or not unit:
            raise HTTPException(400, "Missing 'value' or 'unit'")
        
        logger.info(f"🔄 Converting {value} {unit} to MM")
        
        # Parse the value
        try:
            num_value = float(value)
        except ValueError:
            raise HTTPException(400, f"Invalid number: {value}")
        
        # Convert to MM
        mm_value = BOMConversionService.convert_to_mm(num_value, unit)
        summary = BOMConversionService.create_conversion_summary(str(value), mm_value, unit)
        
        logger.info(f"✅ Converted: {value} {unit} = {mm_value} mm")
        
        return {
            "status": "success",
            "original": value,
            "unit": unit,
            "converted_mm": round(mm_value, 2),
            "summary": summary
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Conversion error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/convert-string")
async def convert_string(request: Request):
    """
    Convert a string like "10 in" to millimeters
    Automatically detects the unit
    
    Request body:
    {
        "value_string": "10 inches"
    }
    
    Returns: {
        "original": "10 inches",
        "value_mm": 254.0,
        "unit_detected": "in",
        "original_value": 10
    }
    """
    try:
        data = await request.json()
        value_string = data.get("value_string")
        
        if not value_string:
            raise HTTPException(400, "Missing 'value_string'")
        
        logger.info(f"🔄 Converting string: '{value_string}'")
        
        mm_value, unit_detected, original_num = BOMConversionService.convert_string_to_mm(
            value_string
        )
        
        if mm_value is None:
            raise HTTPException(400, f"Could not parse: {value_string}")
        
        logger.info(f"✅ Detected unit '{unit_detected}': {original_num} = {mm_value} mm")
        
        return {
            "status": "success",
            "original": value_string,
            "value_mm": round(mm_value, 2),
            "unit_detected": unit_detected,
            "original_value": original_num
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ String conversion error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/calculate-volume")
async def calculate_volume(request: Request):
    """
    Calculate volume from length, width, height
    All values should be in MM (after conversion if needed)
    
    Request body:
    {
        "length_mm": 100,
        "width_mm": 50,
        "height_mm": 25
    }
    
    Returns: {
        "volume_mm3": 125000,
        "dimensions": {...}
    }
    """
    try:
        data = await request.json()
        length = data.get("length_mm")
        width = data.get("width_mm")
        height = data.get("height_mm")
        
        if length is None or width is None or height is None:
            raise HTTPException(400, "Missing length_mm, width_mm, or height_mm")
        
        logger.info(f"📐 Calculating volume: {length}×{width}×{height} mm")
        
        volume = BOMConversionService.calculate_volume_mm3(length, width, height)
        
        logger.info(f"✅ Volume: {volume} mm³")
        
        return {
            "status": "success",
            "volume_mm3": round(volume, 2),
            "dimensions": {
                "length_mm": length,
                "width_mm": width,
                "height_mm": height
            }
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Volume calculation error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/add-dimensions-to-bom")
async def add_dimensions_to_bom(request: Request, db: Session = Depends(get_db)):
    """
    Add dimension columns to BOM items
    Can accept manual dimensions or get from bounding boxes
    
    Request body:
    {
        "doc_id": "...",
        "workspace_id": "...",
        "element_id": "...",
        "user_id": "...",
        "length_values": ["10 in", "20 mm", "5 cm"],
        "width_values": ["5 in", "10 mm", "2.5 cm"],
        "height_values": ["2 in", "4 mm", "1 cm"],
        "use_bounding_boxes": false
    }
    
    Returns: BOM with new columns
    """
    try:
        data = await request.json()
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        user_id = data.get("user_id")
        length_values = data.get("length_values", [])
        width_values = data.get("width_values", [])
        height_values = data.get("height_values", [])
        use_bounding_boxes = data.get("use_bounding_boxes", False)
        
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required fields")
        
        logger.info(f"📝 Adding dimensions to BOM")
        
        # Get token
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get BOM
        bom_data = service.get_bom(doc_id, workspace_id, element_id)
        bom_items = bom_data.get("bomTable", {}).get("items", [])
        
        if use_bounding_boxes:
            logger.info("🔄 Getting bounding boxes to fill dimensions...")
            try:
                bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
                bom_items = BOMConversionService.add_bounding_box_dimensions_to_bom(
                    bom_items, bboxes
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not get bounding boxes: {str(e)}")
        else:
            # Use provided values
            bom_items = BOMConversionService.process_bom_with_dimensions(
                bom_items,
                length_values=length_values,
                width_values=width_values,
                height_values=height_values
            )
        
        logger.info(f"✅ Added dimensions to {len(bom_items)} items")
        
        return {
            "status": "success",
            "items_count": len(bom_items),
            "bom_items": bom_items,
            "message": f"Added dimension columns to {len(bom_items)} BOM items"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error adding dimensions: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/supported-units")
async def get_supported_units():
    """
    Get list of all supported units and their conversion factors
    
    Returns: Dictionary of units and their MM equivalents
    """
    logger.info("📋 Fetching supported units")
    
    return {
        "status": "success",
        "supported_units": BOMConversionService.CONVERSION_FACTORS,
        "message": "All values are conversion factors to millimeters (MM)"
    }


@router.get("/health")
async def bom_conversion_health():
    """Health check for BOM conversion service"""
    return {
        "status": "healthy",
        "service": "bom_conversion",
        "version": "1.0"
    }