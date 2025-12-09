"""
routes/parts.py - Part Scanner & Metadata Endpoints
Fixed: Using correct OnShape metadata endpoint
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import logging
import requests

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= PARTSTUDIO PARTS SCANNING =============

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
        
        logger.info(f"📦 Scanning PartStudio: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get all parts in PartStudio
        url = f"https://cad.onshape.com/api/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}"
        logger.info(f"🔄 Fetching from: {url}")
        
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"❌ API error {response.status_code}")
            raise HTTPException(response.status_code, f"OnShape API error: {response.text}")
        
        parts_data = response.json()
        
        if not isinstance(parts_data, list):
            parts_data = [parts_data]
        
        logger.info(f"✅ Found {len(parts_data)} parts")
        
        # Process each part
        processed_parts = []
        for idx, part in enumerate(parts_data):
            try:
                processed_parts.append({
                    "index": idx + 1,
                    "partId": part.get("id", part.get("partId", f"part_{idx}")),
                    "name": part.get("name", f"Part {idx + 1}"),
                    "partNumber": part.get("partNumber", "-"),
                    "material": part.get("material", "Unknown"),
                    "properties": part.get("properties", []),
                    "href": part.get("href", "")
                })
            except Exception as e:
                logger.warning(f"⚠️ Error processing part {idx}: {str(e)}")
        
        return {
            "status": "success",
            "type": "PartStudio",
            "count": len(processed_parts),
            "parts": processed_parts,
            "message": f"Scanned {len(processed_parts)} parts from PartStudio"
        }
    
    except Exception as e:
        logger.error(f"❌ Scan error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= ASSEMBLY COMPONENTS SCANNING =============

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
        
        logger.info(f"🏗️ Scanning Assembly: element={element_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        
        # Try Assembly BOM endpoint first
        try:
            logger.info("🔄 Trying Assembly BOM endpoint...")
            url = f"https://cad.onshape.com/api/assemblies/d/{doc_id}/w/{workspace_id}/e/{element_id}/bom"
            
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info("✅ Got BOM from Assembly endpoint")
                bom_data = response.json()
                
                components = []
                items = bom_data.get("bomTable", {}).get("items", [])
                
                for idx, item in enumerate(items):
                    components.append({
                        "index": idx + 1,
                        "itemNumber": item.get("item", item.get("itemNumber", idx + 1)),
                        "partNumber": item.get("partNumber", "-"),
                        "name": item.get("name", f"Component {idx + 1}"),
                        "quantity": item.get("quantity", 1),
                        "description": item.get("description", ""),
                        "indentLevel": item.get("indentLevel", 0),
                        "hasChildren": item.get("hasChildren", False),
                        "partId": item.get("partId", "")
                    })
                
                return {
                    "status": "success",
                    "type": "Assembly",
                    "count": len(components),
                    "components": components,
                    "message": f"Scanned {len(components)} components from Assembly"
                }
        
        except Exception as e:
            logger.warning(f"⚠️ Assembly BOM failed: {str(e)}")
        
        # Fallback to Parts endpoint
        logger.info("🔄 Trying Parts endpoint as fallback...")
        url = f"https://cad.onshape.com/api/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}"
        
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("✅ Got parts from Parts endpoint")
            parts_data = response.json()
            
            if not isinstance(parts_data, list):
                parts_data = [parts_data]
            
            components = []
            for idx, part in enumerate(parts_data):
                components.append({
                    "index": idx + 1,
                    "itemNumber": idx + 1,
                    "partNumber": part.get("partNumber", "-"),
                    "name": part.get("name", f"Component {idx + 1}"),
                    "quantity": 1,
                    "description": "",
                    "partId": part.get("id", part.get("partId", f"part_{idx}"))
                })
            
            return {
                "status": "success",
                "type": "Assembly",
                "count": len(components),
                "components": components,
                "message": f"Scanned {len(components)} components from Assembly (via parts endpoint)"
            }
        
        raise HTTPException(400, "Could not access assembly or parts")
    
    except Exception as e:
        logger.error(f"❌ Assembly scan error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= PART METADATA =============

@router.get("/part-metadata")
async def get_part_metadata(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    part_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific part
    Uses CORRECT OnShape endpoint: /api/metadata/d/{docId}/w/{workId}/e/{elemId}/p/{partId}
    """
    try:
        if not all([doc_id, workspace_id, element_id, part_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📋 Getting metadata for part: {part_id}")
        
        token = AuthService.get_valid_token(db, user_id)
        
        # CORRECT OnShape metadata endpoint
        url = f"https://cad.onshape.com/api/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
        
        logger.info(f"🔄 Fetching from: {url}")
        
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        # 404 is NORMAL - means no custom properties
        if response.status_code == 404:
            logger.info(f"⚠️ No metadata found for part {part_id} (this is normal)")
            return {
                "status": "info",
                "data": {
                    "partId": part_id,
                    "properties": [],
                    "message": "No custom properties defined for this part"
                },
                "message": "No custom properties. This is normal for parts without user-defined metadata."
            }
        
        if response.status_code != 200:
            logger.error(f"❌ API error {response.status_code}: {response.text}")
            raise HTTPException(response.status_code, f"OnShape API error: {response.text}")
        
        metadata = response.json()
        logger.info(f"✅ Got metadata for part {part_id}")
        
        # Extract properties from response
        properties = []
        if isinstance(metadata, dict):
            if "items" in metadata:
                items = metadata.get("items", [])
                if items and len(items) > 0:
                    properties = items[0].get("properties", [])
            else:
                properties = metadata.get("properties", [])
        
        return {
            "status": "success",
            "data": {
                "partId": part_id,
                "properties": properties,
                "propertyCount": len(properties)
            },
            "message": f"Retrieved metadata with {len(properties)} custom properties"
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= SEARCH PARTS =============

@router.get("/search")
async def search_parts(
    query: str = Query(...),
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Search for parts by name or ID"""
    try:
        logger.info(f"🔍 Searching: {query}")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get all parts
        url = f"https://cad.onshape.com/api/parts/d/{doc_id}/w/{workspace_id}/e/{element_id}"
        
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(response.status_code, "Could not fetch parts")
        
        parts_data = response.json()
        if not isinstance(parts_data, list):
            parts_data = [parts_data]
        
        # Search
        query_lower = query.lower()
        results = []
        
        for idx, part in enumerate(parts_data):
            name = str(part.get("name", "")).lower()
            part_id = str(part.get("id", part.get("partId", ""))).lower()
            part_number = str(part.get("partNumber", "")).lower()
            
            if (query_lower in name or 
                query_lower in part_id or 
                query_lower in part_number):
                
                results.append({
                    "index": idx + 1,
                    "partId": part.get("id", part.get("partId", "")),
                    "name": part.get("name", ""),
                    "partNumber": part.get("partNumber", "-"),
                    "material": part.get("material", "Unknown")
                })
        
        logger.info(f"✅ Found {len(results)} matching parts")
        
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results,
            "message": f"Found {len(results)} parts matching '{query}'"
        }
    
    except Exception as e:
        logger.error(f"❌ Search error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= HEALTH CHECK =============

@router.get("/health")
async def parts_health():
    """Health check"""
    return {"status": "healthy", "service": "parts"}