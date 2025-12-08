"""Parts Routes - Scanner and Metadata Browser"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
from config import settings
import requests
import logging
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/scan-partstudio")
async def scan_partstudio_parts(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Scan all parts in a PartStudio"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Scanning PartStudio: element={element_id[:8]}")
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            
            # Get all parts
            logger.info("📦 Fetching all parts...")
            parts_url = f"{settings.ONSHAPE_API_URL}/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}"
            response = requests.get(parts_url, headers=service.headers, timeout=service.timeout)
            response.raise_for_status()
            parts_data = response.json()
            
            if not isinstance(parts_data, list):
                parts_data = [parts_data]
            
            logger.info(f"📦 Found {len(parts_data)} parts")
            
            # Get bounding boxes for dimensions
            bbox_map = {}
            try:
                logger.info("📏 Fetching bounding boxes...")
                bboxes = service.get_bounding_boxes(doc_id, workspace_id, element_id)
                bbox_map = {b.get("partId") or b.get("id") or f"part_{idx}": b for idx, b in enumerate(bboxes)}
                logger.info(f"✅ Got {len(bbox_map)} bounding boxes")
            except Exception as e:
                logger.warning(f"⚠️ Could not get bounding boxes: {e}")
            
            # Process each part
            processed_parts = []
            for idx, part in enumerate(parts_data):
                try:
                    part_id = part.get("id") or part.get("partId") or f"part_{idx}"
                    
                    logger.info(f"📝 Processing part {idx+1}: {part.get('name', 'Unknown')}")
                    
                    # Get metadata/properties
                    properties = []
                    try:
                        props_url = f"{settings.ONSHAPE_API_URL}/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}/metadata"
                        props_response = requests.get(props_url, headers=service.headers, timeout=service.timeout)
                        if props_response.status_code == 200:
                            props_data = props_response.json()
                            properties = props_data.get("properties", []) if isinstance(props_data, dict) else props_data
                    except Exception as e:
                        logger.debug(f"   Could not get metadata: {e}")
                    
                    # Get dimensions from bbox
                    bbox = bbox_map.get(part_id, {})
                    dimensions = bbox.get("dimensions", {})
                    
                    # Get material info
                    material_info = {}
                    if isinstance(part.get("material"), dict):
                        material_info = part.get("material", {})
                    
                    processed_parts.append({
                        "index": idx + 1,
                        "partId": part_id,
                        "name": part.get("name", f"Part {idx+1}"),
                        "partNumber": part.get("partNumber", ""),
                        "material": material_info.get("displayName", "") if material_info else "",
                        "properties": properties,
                        "dimensions": dimensions,
                        "propertyCount": len(properties),
                        "fullMaterial": material_info
                    })
                    
                    logger.info(f"✅ Part {idx+1}: {part.get('name', 'Unknown')} - {len(properties)} properties")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not process part {idx+1}: {e}")
                    logger.warning(f"   Traceback: {traceback.format_exc()}")
            
            logger.info(f"✅ Successfully scanned {len(processed_parts)} parts")
            
            return {
                "status": "success",
                "type": "PartStudio",
                "parts": processed_parts,
                "count": len(processed_parts),
                "message": f"Scanned {len(processed_parts)} parts"
            }
            
        except Exception as e:
            logger.error(f"❌ Scan error: {str(e)}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise HTTPException(400, f"Scan failed: {str(e)[:100]}")
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(500, f"Unexpected error: {str(e)[:100]}")


@router.get("/scan-assembly")
async def scan_assembly_components(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Scan all components in an Assembly"""
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Scanning Assembly: element={element_id[:8]}")
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            
            # Try Assembly endpoint first
            logger.info("🏗️ Trying Assembly API endpoint...")
            asm_url = f"{settings.ONSHAPE_API_URL}/assemblies/d/{doc_id}/w/{workspace_id}/e/{element_id}"
            
            try:
                response = requests.get(asm_url, headers=service.headers, timeout=service.timeout)
                response.raise_for_status()
                asm_data = response.json()
                logger.info(f"✅ Got assembly data")
                
                components = asm_data.get("occurrences", [])
            except Exception as e:
                logger.warning(f"⚠️ Assembly endpoint failed: {e}")
                logger.info(f"🔄 Falling back to Parts endpoint...")
                
                # Fallback: Get parts and treat as components
                parts_url = f"{settings.ONSHAPE_API_URL}/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}"
                response = requests.get(parts_url, headers=service.headers, timeout=service.timeout)
                response.raise_for_status()
                parts_data = response.json()
                
                if not isinstance(parts_data, list):
                    parts_data = [parts_data]
                
                logger.info(f"✅ Got {len(parts_data)} parts as fallback")
                
                # Convert parts to component format
                components = []
                for idx, part in enumerate(parts_data):
                    components.append({
                        "id": part.get("id", f"part_{idx}"),
                        "name": part.get("name", f"Part {idx+1}"),
                        "definition": {
                            "documentId": doc_id
                        },
                        "properties": part.get("properties", {}),
                        "_isPartStudio": True
                    })
            
            logger.info(f"📦 Found {len(components)} components")
            
            # Process each component
            processed_components = []
            for idx, comp in enumerate(components):
                try:
                    logger.info(f"📝 Processing component {idx+1}: {comp.get('name', 'Unknown')}")
                    
                    comp_id = comp.get("id", f"component_{idx}")
                    comp_name = comp.get("name", f"Component {idx+1}")
                    
                    # Try to get properties
                    properties = []
                    if isinstance(comp.get("properties"), list):
                        properties = comp.get("properties", [])
                    elif isinstance(comp.get("properties"), dict):
                        properties = [{"name": k, "value": v} for k, v in comp.get("properties", {}).items()]
                    
                    processed_components.append({
                        "index": idx + 1,
                        "componentId": comp_id,
                        "name": comp_name,
                        "partIdentifier": comp.get("definition", {}).get("documentId", ""),
                        "quantity": 1,
                        "properties": properties,
                        "propertyCount": len(properties) if isinstance(properties, list) else 0
                    })
                    
                    logger.info(f"✅ Component {idx+1}: {comp_name}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not process component {idx+1}: {e}")
            
            logger.info(f"✅ Successfully scanned {len(processed_components)} components")
            
            return {
                "status": "success",
                "type": "Assembly",
                "components": processed_components,
                "count": len(processed_components),
                "message": f"Scanned {len(processed_components)} components"
            }
            
        except Exception as e:
            logger.error(f"❌ Scan error: {str(e)}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise HTTPException(400, f"Scan failed: {str(e)[:100]}")
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(500, f"Unexpected error: {str(e)[:100]}")


@router.get("/part-metadata")
async def get_part_metadata(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    part_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get detailed metadata for a specific part"""
    try:
        if not all([doc_id, workspace_id, element_id, part_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Getting metadata for part: {part_id[:8]}")
        
        try:
            token = AuthService.get_valid_token(db, user_id)
        except Exception as e:
            raise HTTPException(401, f"Token error: {str(e)}")
        
        try:
            service = OnShapeService(token)
            
            # Get metadata
            logger.info(f"📋 Fetching metadata for {part_id}...")
            url = f"{settings.ONSHAPE_API_URL}/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}/metadata"
            response = requests.get(url, headers=service.headers, timeout=service.timeout)
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                metadata = response.json()
                logger.info(f"📋 Got metadata")
            else:
                logger.warning(f"⚠️ No metadata available (status {response.status_code})")
                metadata = {"properties": []}
            
            properties = metadata.get("properties", []) if isinstance(metadata, dict) else metadata
            
            logger.info(f"✅ Got metadata: {len(properties)} properties")
            
            return {
                "status": "success",
                "partId": part_id,
                "metadata": metadata,
                "properties": properties if isinstance(properties, list) else [],
                "count": len(properties) if isinstance(properties, list) else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return {
                "status": "info",
                "partId": part_id,
                "message": "Metadata not available for this part",
                "properties": [],
                "count": 0
            }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def parts_health():
    """Health check"""
    return {"status": "healthy", "service": "parts"}