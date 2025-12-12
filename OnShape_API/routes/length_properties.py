"""
routes/length_properties.py - Smart Length Property Extraction
Intelligently gets Length from configuration and creates properties
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.length_property_resolver import LengthPropertyResolver
from services.metadata_service import MetadataService
from services.onshape_service import OnShapeService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analyze-length-properties")
async def analyze_length_properties(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Analyze which parts have Length properties available
    
    Returns:
    - Parts with 'Units - Millimeter' property
    - Parts where Length was found in configuration
    - Detailed status for each part
    
    This is a READ-ONLY analysis - no modifications yet
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Analyzing Length properties...")
        
        token = AuthService.get_valid_token(db, user_id)
        
        # Get BOM first
        onshape = OnShapeService(token)
        
        bom_data = onshape.get_bom(doc_id, workspace_id, element_id)
        if not bom_data or "bomTable" not in bom_data:
            raise HTTPException(400, "Could not read BOM")
        
        bom_items = bom_data["bomTable"]["items"]
        logger.info(f"📊 Got {len(bom_items)} items from BOM")
        
        # Analyze each item for Length properties
        resolver = LengthPropertyResolver(token)
        result = resolver.resolve_length_properties(
            doc_id, workspace_id, element_id, bom_items
        )
        
        logger.info(f"✅ Analysis complete: {result['items_with_length_property']} items have Length")
        
        return {
            "status": "success",
            "data": result,
            "message": f"Analyzed {result['total_items']} items. Found Length in {result['items_with_length_property']} parts."
        }
    
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/create-length-properties")
async def create_length_properties(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Create Length properties for parts
    
    Process:
    1. Analyze BOM for Length values
    2. Filter only parts with 'Units - Millimeter' property
    3. Create "Length" metadata property for each
    4. Return results (successes and failures)
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📝 Creating Length properties...")
        
        token = AuthService.get_valid_token(db, user_id)
        
        # Step 1: Analyze
        onshape = OnShapeService(token)
        
        bom_data = onshape.get_bom(doc_id, workspace_id, element_id)
        if not bom_data or "bomTable" not in bom_data:
            raise HTTPException(400, "Could not read BOM")
        
        bom_items = bom_data["bomTable"]["items"]
        logger.info(f"📊 Got {len(bom_items)} items")
        
        # Step 2: Resolve Length values
        resolver = LengthPropertyResolver(token)
        analysis = resolver.resolve_length_properties(doc_id, workspace_id, element_id, bom_items)
        
        # Step 3: Create properties for successful resolutions
        metadata_service = MetadataService(token)
        
        created_count = 0
        failed_count = 0
        errors = []
        
        for result in analysis["results"]:
            # Only create for successful resolutions
            if result["status"] == "success" and result["length_mm"] is not None:
                try:
                    part_id = result["part_id"]
                    length_value = str(result["length_mm"])
                    
                    logger.info(f"   Creating property for {result['name']}: Length = {length_value} mm")
                    
                    # Create property
                    success = metadata_service.update_part_metadata(
                        doc_id,
                        workspace_id,
                        element_id,
                        part_id,
                        {
                            "Length": length_value,
                            "Length_Unit": "mm",
                            "Length_Source": result.get("source", "configuration")
                        }
                    )
                    
                    if success:
                        created_count += 1
                        logger.info(f"      ✅ Created")
                    else:
                        failed_count += 1
                        error_msg = f"Failed to create property for {result['name']}"
                        errors.append(error_msg)
                        logger.warning(f"      ❌ {error_msg}")
                
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Error with {result['name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"      ❌ {error_msg}")
        
        logger.info(f"✅ Complete: {created_count} created, {failed_count} failed")
        
        return {
            "status": "success",
            "analysis": analysis,
            "creation": {
                "created_count": created_count,
                "failed_count": failed_count,
                "errors": errors
            },
            "message": f"Successfully created Length properties for {created_count} parts"
        }
    
    except Exception as e:
        logger.error(f"❌ Creation error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/length-properties-status")
async def get_length_status(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Quick status check"""
    try:
        token = AuthService.get_valid_token(db, user_id)
        
        onshape = OnShapeService(token)
        
        bom_data = onshape.get_bom(doc_id, workspace_id, element_id)
        bom_items = bom_data["bomTable"]["items"]
        
        resolver = LengthPropertyResolver(token)
        result = resolver.resolve_length_properties(doc_id, workspace_id, element_id, bom_items)
        
        return {
            "status": "success",
            "summary": {
                "total_items": result["total_items"],
                "items_with_units_mm": result["items_with_units_mm"],
                "items_with_length_found": result["items_with_length_found"],
                "items_ready_to_create": result["items_with_length_property"],
                "success_rate": result["summary"]["success_rate"]
            },
            "next_step": "Call /create-length-properties to create the properties"
        }
    
    except Exception as e:
        logger.error(f"❌ Status error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def length_properties_health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "length-properties",
        "version": "1.0"
    }