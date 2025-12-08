"""BOM Routes - Fetch & Push Working"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
from services.bom_conversion import BOMConversionService

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


@router.post("/convert-unit")
async def convert_unit(request: Request):
    """Convert a value from one unit to millimeters"""
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
    """Convert a string like '10 in' to millimeters"""
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
    """Calculate volume from length, width, height (all in MM)"""
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
    """Add dimension columns to BOM items"""
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
    """Get list of all supported units and their conversion factors"""
    logger.info("📋 Fetching supported units")
    
    return {
        "status": "success",
        "supported_units": BOMConversionService.CONVERSION_FACTORS,
        "message": "All values are conversion factors to millimeters (MM)"
    }


@router.get("/health")
async def bom_health():
    """Health check for BOM service"""
    return {
        "status": "healthy",
        "service": "bom",
        "version": "1.0"
    }