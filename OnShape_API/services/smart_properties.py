"""
routes/smart_properties.py - Smart Property Management
Uses PropertyResolver to safely handle:
- Configuration variables
- Bounding boxes
- Custom property creation without computed property errors
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.onshape_service import OnShapeService
from services.property_resolver import PropertyResolver
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============= GET ALL CONFIGURATION VARIABLES =============

@router.get("/variables")
async def get_variables(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get ALL configuration variables from a PartStudio
    
    Returns all variables with their values and types
    No computed property execution errors - direct values only
    """
    try:
        if not all([doc_id, workspace_id, element_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔧 Getting configuration variables")
        
        token = AuthService.get_valid_token(db, user_id)
        resolver = PropertyResolver(token)
        
        # Get all variables
        variables = resolver.get_all_variables(doc_id, workspace_id, element_id)
        
        logger.info(f"✅ Found {len(variables)} variables")
        
        return {
            "status": "success",
            "variables": variables,
            "count": len(variables),
            "message": f"Found {len(variables)} configuration variables"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting variables: {str(e)}")
        raise HTTPException(500, str(e))


# ============= RESOLVE PROPERTY VALUE (SMART FALLBACK) =============

@router.get("/resolve-value")
async def resolve_value(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    part_id: str = Query(...),
    property_name: str = Query(...),  # "Length", "Width", "Height"
    config_var_name: str = Query(""),  # e.g., "PartLength"
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Resolve a single property value using smart fallback:
    1. Try configuration variable (if provided)
    2. Try bounding box
    3. Return None if neither works
    
    This prevents "Computed property execution error"
    """
    try:
        if not all([doc_id, workspace_id, element_id, part_id, property_name, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Resolving {property_name} for part {part_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        resolver = PropertyResolver(token)
        
        # Resolve value
        value = resolver.resolve_property_value(
            doc_id, workspace_id, element_id, part_id,
            property_name,
            config_var_name=config_var_name if config_var_name else None
        )
        
        if value is None:
            logger.warning(f"❌ Could not resolve {property_name}")
            return {
                "status": "not_found",
                "property": property_name,
                "value": None,
                "message": f"Could not resolve {property_name} from configuration or bounding box"
            }
        
        logger.info(f"✅ Resolved {property_name} = {value}")
        
        return {
            "status": "success",
            "property": property_name,
            "value": round(value, 2),
            "message": f"Successfully resolved {property_name}"
        }
    
    except Exception as e:
        logger.error(f"❌ Error resolving value: {str(e)}")
        raise HTTPException(500, str(e))


# ============= CREATE LENGTH PROPERTIES (SMART) =============

@router.post("/create-smart")
async def create_smart_properties(request: Request, db: Session = Depends(get_db)):
    """
    Create Length, Width, Height properties with smart resolution
    
    Avoids "Computed property execution error" by:
    1. Resolving values first (config var or bbox)
    2. Only creating properties for resolved values
    3. Using static string values, not computed properties
    
    Request:
    {
        "user_id": "...",
        "doc_id": "...",
        "workspace_id": "...",
        "element_id": "...",
        "bom_items": [...],  // Optional - will fetch if not provided
        "use_config_vars": true,  // Try configuration variables
        "use_bbox": true  // Fallback to bounding boxes
    }
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        doc_id = data.get("doc_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        bom_items = data.get("bom_items")
        use_config_vars = data.get("use_config_vars", True)
        use_bbox = data.get("use_bbox", True)
        
        if not all([user_id, doc_id, workspace_id, element_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"📐 Creating smart properties")
        logger.info(f"   use_config_vars: {use_config_vars}")
        logger.info(f"   use_bbox: {use_bbox}")
        
        token = AuthService.get_valid_token(db, user_id)
        
        # Fetch BOM if not provided
        if not bom_items:
            logger.info(f"   Fetching BOM...")
            service = OnShapeService(token)
            bom_data = service.get_bom(doc_id, workspace_id, element_id, indented=False)
            bom_items = bom_data.get("bomTable", {}).get("items", [])
        
        if not bom_items:
            raise HTTPException(400, "No BOM items found")
        
        logger.info(f"   Processing {len(bom_items)} items")
        
        # Create properties with smart resolution
        resolver = PropertyResolver(token)
        
        result = resolver.create_length_properties_smart(
            doc_id, workspace_id, element_id,
            bom_items,
            use_config_vars=use_config_vars,
            use_bbox=use_bbox
        )
        
        logger.info(f"✅ Complete: {result['created']}/{result['total']} properties created")
        
        return {
            "status": result["status"],
            "created": result["created"],
            "skipped": result["skipped"],
            "total": result["total"],
            "errors": result["errors"][:10],  # Limit to first 10 errors
            "details": result["details"],
            "message": result["message"]
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error creating smart properties: {str(e)}")
        raise HTTPException(500, str(e))


# ============= DIAGNOSE PROPERTY ISSUES =============

@router.get("/diagnose")
async def diagnose_part(
    doc_id: str = Query(...),
    workspace_id: str = Query(...),
    element_id: str = Query(...),
    part_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Diagnose why a part's property creation is failing
    
    Returns:
    - Available configuration variables
    - Bounding box dimensions
    - What can be used for Length property
    - Recommendations
    """
    try:
        if not all([doc_id, workspace_id, element_id, part_id, user_id]):
            raise HTTPException(400, "Missing required parameters")
        
        logger.info(f"🔍 Diagnosing part {part_id[:8]}")
        
        token = AuthService.get_valid_token(db, user_id)
        resolver = PropertyResolver(token)
        
        diagnosis = {
            "part_id": part_id,
            "configuration_variables": {},
            "bounding_box": None,
            "recommended_approach": None,
            "issues": [],
            "solutions": []
        }
        
        # Get configuration variables
        try:
            all_vars = resolver.get_all_variables(doc_id, workspace_id, element_id)
            diagnosis["configuration_variables"] = all_vars
            logger.info(f"   Found {len(all_vars)} variables")
        except Exception as e:
            diagnosis["issues"].append(f"Cannot access configuration variables: {str(e)}")
            logger.warning(f"   Variables error: {str(e)}")
        
        # Get bounding box
        try:
            bbox_dims = resolver.get_bbox_dimensions(doc_id, workspace_id, element_id, part_id)
            if bbox_dims:
                diagnosis["bounding_box"] = bbox_dims
                logger.info(f"   Found bounding box: {bbox_dims}")
            else:
                diagnosis["issues"].append("No bounding box found for this part")
        except Exception as e:
            diagnosis["issues"].append(f"Cannot access bounding box: {str(e)}")
            logger.warning(f"   Bbox error: {str(e)}")
        
        # Recommend approach
        if diagnosis["configuration_variables"]:
            diagnosis["recommended_approach"] = "Use configuration variable (most reliable)"
            diagnosis["solutions"].append(
                "Configuration variables are available. Use 'PartLength' variable for Length property."
            )
        elif diagnosis["bounding_box"]:
            diagnosis["recommended_approach"] = "Use bounding box"
            diagnosis["solutions"].append(
                f"Bounding box available: Length={diagnosis['bounding_box']['length']}mm"
            )
        else:
            diagnosis["recommended_approach"] = "Cannot auto-resolve - may need manual input"
            diagnosis["issues"].append("No configuration variables or bounding box found")
            diagnosis["solutions"].append(
                "1. Check if part is visible in 3D view\n" +
                "2. Define configuration variables in PartStudio\n" +
                "3. Manually set dimensions in OnShape"
            )
        
        logger.info(f"✅ Diagnosis complete")
        
        return {
            "status": "success",
            "diagnosis": diagnosis,
            "message": diagnosis["recommended_approach"]
        }
    
    except Exception as e:
        logger.error(f"❌ Error diagnosing: {str(e)}")
        raise HTTPException(500, str(e))


# ============= HEALTH CHECK =============

@router.get("/health")
async def smart_properties_health():
    """Health check for smart properties service"""
    return {
        "status": "healthy",
        "service": "smart_properties",
        "endpoints": [
            "variables",
            "resolve-value",
            "create-smart",
            "diagnose"
        ],
        "features": [
            "Configuration variable resolution",
            "Bounding box fallback",
            "Smart property creation",
            "Computed property error prevention",
            "Part diagnosis"
        ]
    }