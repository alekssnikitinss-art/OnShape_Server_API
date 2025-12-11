"""
routes/advanced.py - Advanced Document Management Features
Combines: Save with Custom Names, Element Search, Complete BOM with Dynamic Columns
All in single file following project conventions
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db, SavedDocument
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import logging
from datetime import datetime
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= 1. SAVE DOCUMENT WITH CUSTOM NAME =============

@router.post("/save-named")
async def save_document_with_name(request: Request, db: Session = Depends(get_db)):
    """
    Save document with custom user-friendly name instead of ID
    
    Request:
    {
        "user_id": "user-id",
        "document_id": "doc-id",
        "workspace_id": "ws-id",
        "element_id": "elem-id",
        "custom_name": "Main Chassis Assembly v3",
        "tags": ["production", "v3"],
        "notes": "Final version"
    }
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        document_id = data.get("document_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        custom_name = data.get("custom_name", "Unnamed")
        tags = data.get("tags", [])
        notes = data.get("notes", "")
        
        if not all([user_id, document_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required: user_id, document_id, workspace_id, element_id")
        
        logger.info(f"💾 Saving document as: '{custom_name}'")
        
        # Check if exists
        saved = db.query(SavedDocument).filter(
            SavedDocument.user_id == user_id,
            SavedDocument.document_id == document_id,
            SavedDocument.element_id == element_id
        ).first()
        
        if saved:
            logger.info(f"   Updating existing document")
            saved.document_name = custom_name
            saved.last_used_at = datetime.utcnow()
            saved.properties_data = {
                "custom_name": custom_name,
                "tags": tags,
                "notes": notes,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            logger.info(f"   Creating new saved document")
            saved = SavedDocument(
                id=str(uuid.uuid4()),
                user_id=user_id,
                document_id=document_id,
                workspace_id=workspace_id,
                element_id=element_id,
                document_name=custom_name,
                properties_data={
                    "custom_name": custom_name,
                    "tags": tags,
                    "notes": notes,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            db.add(saved)
        
        db.commit()
        db.refresh(saved)
        
        logger.info(f"✅ Document saved as '{custom_name}'")
        
        return {
            "status": "success",
            "id": saved.id,
            "message": f"Document saved as '{custom_name}'",
            "document": {
                "id": saved.id,
                "name": saved.document_name,
                "tags": tags,
                "notes": notes,
                "saved_at": saved.last_used_at.isoformat()
            }
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error saving document: {str(e)}")
        raise HTTPException(500, str(e))


# ============= 2. SEARCH ELEMENTS BY NAME AND TYPE =============

@router.get("/search-elements")
async def search_elements(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    user_id: str = Query(...),
    search_term: str = Query(""),
    element_type: str = Query(""),
    db: Session = Depends(get_db)
):
    """
    Search elements in document by name and/or type
    
    Types: Assembly, PartStudio, BLOB, APPLICATION, REFERENCE
    
    Query:
    ?doc_id=xxx&workspace_id=xxx&user_id=xxx&search_term=chassis&element_type=Assembly
    """
    try:
        if not all([doc_id, workspace_id, user_id]):
            raise HTTPException(400, "Missing required: doc_id, workspace_id, user_id")
        
        logger.info(f"🔍 Searching elements")
        logger.info(f"   Search: '{search_term}' | Type: '{element_type}'")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Get all elements
        elements = service.get_elements(doc_id, workspace_id)
        
        if not elements:
            return {
                "status": "success",
                "elements": [],
                "count": 0,
                "message": "No elements found"
            }
        
        # Filter by search term and type
        filtered = []
        
        for elem in elements:
            name = elem.get("name", "").lower()
            elem_type = elem.get("elementType", "")
            
            # Apply search filter
            if search_term and search_term.lower() not in name:
                continue
            
            # Apply type filter
            if element_type and elem_type != element_type:
                continue
            
            filtered.append({
                "id": elem.get("id", ""),
                "name": elem.get("name", "Unknown"),
                "type": elem_type,
                "owner": elem.get("owner", ""),
                "modifiedAt": elem.get("modifiedAt", ""),
                "description": elem.get("description", "")
            })
        
        logger.info(f"✅ Found {len(filtered)} elements")
        
        # Type summary
        type_summary = {}
        for elem in filtered:
            t = elem["type"]
            type_summary[t] = type_summary.get(t, 0) + 1
        
        return {
            "status": "success",
            "elements": filtered,
            "count": len(filtered),
            "total": len(elements),
            "types": type_summary,
            "message": f"Found {len(filtered)} elements"
        }
    
    except Exception as e:
        logger.error(f"❌ Search error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= 3. GET COMPLETE BOM WITH ALL COLUMNS =============

@router.get("/bom-complete")
async def get_complete_bom(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    indented: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get complete BOM with EVERY column automatically detected
    
    Returns:
    - All items with all available columns
    - Column metadata (name, type, presence %)
    - Cleaned data (null values removed)
    - Column grouping (all/most/few items have)
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📊 Fetching complete BOM with ALL columns")
        
        token = AuthService.get_valid_token(db, user_id)
        service = OnShapeService(token)
        
        # Fetch BOM
        bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=indented)
        
        if not bom_data or "bomTable" not in bom_data:
            raise HTTPException(400, "Could not fetch BOM")
        
        items = bom_data.get("bomTable", {}).get("items", [])
        
        if not items:
            return {
                "status": "success",
                "items": [],
                "columns": [],
                "count": 0,
                "message": "BOM is empty"
            }
        
        logger.info(f"   Fetched {len(items)} items")
        
        # ========= DETECT ALL COLUMNS DYNAMICALLY =========
        all_columns = {}
        
        for item in items:
            if isinstance(item, dict):
                for key, value in item.items():
                    if key not in all_columns:
                        # Determine type
                        data_type = "string"
                        if isinstance(value, (int, float)):
                            data_type = "number"
                        elif isinstance(value, bool):
                            data_type = "boolean"
                        elif isinstance(value, list):
                            data_type = "array"
                        elif isinstance(value, dict):
                            data_type = "object"
                        elif value is None:
                            data_type = "null"
                        
                        all_columns[key] = {
                            "name": key,
                            "type": data_type,
                            "present": 0,
                            "missing": 0
                        }
                    
                    if value is not None and value != "":
                        all_columns[key]["present"] += 1
                    else:
                        all_columns[key]["missing"] += 1
        
        # ========= BUILD COLUMN METADATA =========
        columns = []
        for key, info in all_columns.items():
            presence = round((info["present"] / len(items)) * 100, 1) if items else 0
            
            columns.append({
                "key": key,
                "name": key,
                "type": info["type"],
                "present": info["present"],
                "missing": info["missing"],
                "presence_percent": presence
            })
        
        # Sort by presence
        columns.sort(key=lambda x: (-x["present"], x["name"]))
        
        logger.info(f"✅ Detected {len(columns)} columns")
        
        # ========= CLEAN ITEMS =========
        cleaned = []
        for item in items:
            clean_item = {}
            for key, value in item.items():
                if value is not None and value != "":
                    clean_item[key] = value
            cleaned.append(clean_item)
        
        # Group columns by presence
        all_have = [c["key"] for c in columns if c["presence_percent"] == 100]
        most_have = [c["key"] for c in columns if 50 <= c["presence_percent"] < 100]
        few_have = [c["key"] for c in columns if c["presence_percent"] < 50]
        
        return {
            "status": "success",
            "items": cleaned,
            "columns": columns,
            "count": len(cleaned),
            "column_count": len(columns),
            "grouping": {
                "all_100_percent": all_have,
                "most_50_percent": most_have,
                "few_under_50": few_have
            },
            "metadata": {
                "doc_id": doc_id,
                "element_id": element_id,
                "type": bom_data.get("type", "Unknown"),
                "indented": indented,
                "fetched": datetime.utcnow().isoformat()
            },
            "message": f"BOM: {len(cleaned)} items, {len(columns)} columns"
        }
    
    except Exception as e:
        logger.error(f"❌ BOM error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= 4. RENAME AND MANAGE COLUMNS (UI SUPPORT) =============

@router.post("/column-settings")
async def save_column_settings(request: Request):
    """
    Save column renames and custom columns (client sends data to validate)
    Server validates, client stores in localStorage
    
    Request:
    {
        "element_id": "elem-id",
        "renames": {
            "partNumber": "Part #",
            "quantity": "Qty"
        },
        "custom_columns": [
            {
                "key": "unit_cost",
                "name": "Unit Cost",
                "type": "currency",
                "default": 0
            }
        ]
    }
    """
    try:
        data = await request.json()
        element_id = data.get("element_id")
        renames = data.get("renames", {})
        custom_cols = data.get("custom_columns", [])
        
        if not element_id:
            raise HTTPException(400, "Missing element_id")
        
        logger.info(f"🏷️ Validating column settings for: {element_id[:8]}")
        logger.info(f"   Renames: {len(renames)} | Custom: {len(custom_cols)}")
        
        # Validate custom columns
        valid_types = ["string", "number", "boolean", "date", "currency"]
        for col in custom_cols:
            if col.get("type") not in valid_types:
                raise HTTPException(400, f"Invalid type: {col.get('type')}")
        
        logger.info(f"✅ Column settings validated")
        
        return {
            "status": "success",
            "element_id": element_id,
            "renames": renames,
            "custom_columns": custom_cols,
            "message": "Column settings validated - save to localStorage in browser"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Column settings error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= 5. GET SAVED WITH FILTERS =============

@router.get("/saved-filtered")
async def get_saved_filtered(
    user_id: str = Query(...),
    search: str = Query(""),
    element_type: str = Query(""),
    sort_by: str = Query("last_used"),
    db: Session = Depends(get_db)
):
    """
    Get saved documents with search, filter, and sort
    
    Query:
    ?user_id=xxx&search=chassis&element_type=Assembly&sort_by=name
    """
    try:
        if not user_id:
            raise HTTPException(400, "Missing user_id")
        
        logger.info(f"📂 Fetching saved documents")
        logger.info(f"   Search: '{search}' | Type: '{element_type}' | Sort: {sort_by}")
        
        # Build query
        query = db.query(SavedDocument).filter(SavedDocument.user_id == user_id)
        
        # Search filter
        if search:
            search_lower = search.lower()
            query = query.filter(
                SavedDocument.document_name.ilike(f"%{search_lower}%") |
                SavedDocument.element_name.ilike(f"%{search_lower}%")
            )
        
        # Type filter
        if element_type:
            query = query.filter(SavedDocument.element_type == element_type)
        
        # Sort
        if sort_by == "name":
            query = query.order_by(SavedDocument.document_name.asc())
        elif sort_by == "created":
            query = query.order_by(SavedDocument.created_at.desc())
        else:
            query = query.order_by(SavedDocument.last_used_at.desc())
        
        docs = query.all()
        
        logger.info(f"✅ Found {len(docs)} documents")
        
        return {
            "status": "success",
            "documents": [d.to_dict() for d in docs],
            "count": len(docs),
            "filters": {
                "search": search,
                "element_type": element_type,
                "sort": sort_by
            },
            "message": f"Retrieved {len(docs)} documents"
        }
    
    except Exception as e:
        logger.error(f"❌ Filter error: {str(e)}")
        raise HTTPException(500, str(e))


# ============= HEALTH CHECK =============

@router.get("/health")
async def advanced_health():
    """Health check for advanced features"""
    return {
        "status": "healthy",
        "service": "advanced",
        "endpoints": [
            "save-named",
            "search-elements",
            "bom-complete",
            "column-settings",
            "saved-filtered"
        ]
    }