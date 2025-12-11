"""
services/property_resolver.py - Smart Property Value Resolution
Handles configuration variables, bounding boxes, and custom properties
with proper error handling and fallback strategies

Resolves issues:
- Computed property execution errors
- Missing configuration variables
- Inconsistent bounding box detection
- Reliable custom property creation
"""

import logging
from typing import Dict, Optional, List, Any
from services.onshape_service import OnShapeService
from services.bom_service import BOMService
import requests

logger = logging.getLogger(__name__)

class PropertyResolver:
    """Resolve property values from multiple sources with smart fallbacks"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.onshape_service = OnShapeService(access_token)
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    # ============= GET CONFIGURATION VARIABLES =============
    
    def get_all_variables(self, doc_id: str, workspace_id: str, element_id: str) -> Dict[str, Any]:
        """
        Safely get ALL configuration variables from a PartStudio
        Uses multiple approaches to find variables
        
        Returns dict with structure:
        {
            "variable_name": {
                "value": 100,
                "unit": "mm",
                "type": "number",
                "source": "configuration" | "parameter"
            }
        }
        """
        try:
            logger.info(f"🔧 Getting all variables for element: {element_id[:8]}")
            
            all_vars = {}
            
            # Approach 1: Try standard variables endpoint
            try:
                logger.info(f"   Trying: /partstudios/.../variables endpoint")
                url = f"https://cad.onshape.com/api/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/variables"
                
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    vars_data = response.json()
                    logger.info(f"   ✅ Found variables via standard endpoint")
                    
                    if isinstance(vars_data, dict):
                        if "variables" in vars_data:
                            all_vars.update(self._parse_variables(vars_data.get("variables", [])))
                        elif "items" in vars_data:
                            all_vars.update(self._parse_variables(vars_data.get("items", [])))
                        else:
                            all_vars.update(self._parse_variables(vars_data))
                    elif isinstance(vars_data, list):
                        all_vars.update(self._parse_variables(vars_data))
            
            except Exception as e:
                logger.warning(f"   ⚠️ Standard endpoint failed: {str(e)}")
            
            # Approach 2: Try parameters endpoint (for derived parameters)
            try:
                if not all_vars:
                    logger.info(f"   Trying: /documents/.../parameters endpoint")
                    url = f"https://cad.onshape.com/api/documents/d/{doc_id}/w/{workspace_id}/e/{element_id}/parameters"
                    
                    response = requests.get(url, headers=self.headers, timeout=30)
                    
                    if response.status_code == 200:
                        params_data = response.json()
                        logger.info(f"   ✅ Found parameters via parameters endpoint")
                        
                        if isinstance(params_data, dict):
                            all_vars.update(self._parse_variables(params_data.get("parameters", [])))
                        elif isinstance(params_data, list):
                            all_vars.update(self._parse_variables(params_data))
            
            except Exception as e:
                logger.warning(f"   ⚠️ Parameters endpoint failed: {str(e)}")
            
            logger.info(f"✅ Found {len(all_vars)} variables total")
            
            return all_vars
        
        except Exception as e:
            logger.error(f"❌ Error getting variables: {str(e)}")
            return {}
    
    def _parse_variables(self, variables: List[Dict]) -> Dict[str, Any]:
        """Parse variable data from API response"""
        parsed = {}
        
        if not isinstance(variables, list):
            return parsed
        
        for var in variables:
            if not isinstance(var, dict):
                continue
            
            var_name = var.get("name") or var.get("variableName")
            if not var_name:
                continue
            
            var_value = var.get("value") or var.get("expression") or var.get("defaultValue")
            var_unit = var.get("unit") or var.get("units") or "unknown"
            
            # Determine type
            var_type = "unknown"
            if isinstance(var_value, (int, float)):
                var_type = "number"
            elif isinstance(var_value, str):
                var_type = "string"
            elif isinstance(var_value, bool):
                var_type = "boolean"
            
            parsed[var_name] = {
                "value": var_value,
                "unit": var_unit,
                "type": var_type,
                "source": "configuration"
            }
            
            logger.debug(f"   Parsed variable: {var_name} = {var_value} {var_unit}")
        
        return parsed
    
    # ============= GET BOUNDING BOX DIMENSIONS =============
    
    def get_bbox_dimensions(self, doc_id: str, workspace_id: str, element_id: str, part_id: str) -> Optional[Dict[str, float]]:
        """
        Get dimensions from bounding box for a specific part
        
        Returns:
        {
            "length": 100.5,
            "width": 50.25,
            "height": 25.75,
            "volume": 131637.28
        }
        Or None if failed
        """
        try:
            logger.info(f"📏 Getting bounding box for part: {part_id[:8]}")
            
            # Get bounding boxes
            bboxes = self.onshape_service.get_bounding_boxes(doc_id, workspace_id, element_id)
            
            if not bboxes:
                logger.warning(f"   ⚠️ No bounding boxes found")
                return None
            
            # Find matching part
            target_bbox = None
            for bbox in bboxes:
                bbox_part_id = bbox.get("partId") or bbox.get("id")
                if bbox_part_id == part_id:
                    target_bbox = bbox
                    break
            
            if not target_bbox:
                logger.warning(f"   ⚠️ No bounding box for part {part_id[:8]}")
                return None
            
            # Calculate dimensions
            dims = BOMService.calculate_dimensions(target_bbox)
            logger.info(f"   ✅ Got dimensions: L={dims['length']}, W={dims['width']}, H={dims['height']}")
            
            return {
                "length": dims["length"],
                "width": dims["width"],
                "height": dims["height"],
                "volume": dims["volume"]
            }
        
        except Exception as e:
            logger.error(f"   ❌ Error getting bbox: {str(e)}")
            return None
    
    # ============= RESOLVE PROPERTY VALUE (SMART FALLBACK) =============
    
    def resolve_property_value(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        property_name: str,  # "Length", "Width", "Height"
        config_var_name: Optional[str] = None,  # e.g., "PartLength"
    ) -> Optional[float]:
        """
        Resolve property value using smart fallback strategy:
        
        1. Try configuration variable (if provided)
        2. Try bounding box
        3. Return None (will not create computed property)
        
        This avoids "Computed property execution error"
        """
        try:
            logger.info(f"🔍 Resolving {property_name} for part {part_id[:8]}")
            
            # Strategy 1: Configuration Variable
            if config_var_name:
                logger.info(f"   Strategy 1: Checking configuration variable '{config_var_name}'")
                
                try:
                    all_vars = self.get_all_variables(doc_id, workspace_id, element_id)
                    
                    if config_var_name in all_vars:
                        var_data = all_vars[config_var_name]
                        value = var_data["value"]
                        
                        # Try to convert to float
                        try:
                            value_float = float(value)
                            logger.info(f"   ✅ Got value from variable: {value_float}")
                            return value_float
                        except (ValueError, TypeError):
                            logger.warning(f"   ⚠️ Variable value not numeric: {value}")
                    else:
                        logger.warning(f"   ⚠️ Variable '{config_var_name}' not found")
                
                except Exception as e:
                    logger.warning(f"   ⚠️ Variable resolution failed: {str(e)}")
            
            # Strategy 2: Bounding Box
            logger.info(f"   Strategy 2: Checking bounding box")
            
            try:
                bbox_dims = self.get_bbox_dimensions(doc_id, workspace_id, element_id, part_id)
                
                if bbox_dims:
                    if property_name.lower() == "length":
                        logger.info(f"   ✅ Got value from bounding box: {bbox_dims['length']}")
                        return bbox_dims["length"]
                    elif property_name.lower() == "width":
                        logger.info(f"   ✅ Got value from bounding box: {bbox_dims['width']}")
                        return bbox_dims["width"]
                    elif property_name.lower() == "height":
                        logger.info(f"   ✅ Got value from bounding box: {bbox_dims['height']}")
                        return bbox_dims["height"]
                
                logger.warning(f"   ⚠️ No bounding box value found")
            
            except Exception as e:
                logger.warning(f"   ⚠️ Bounding box resolution failed: {str(e)}")
            
            # No value found
            logger.warning(f"❌ Could not resolve {property_name} - will skip custom property creation")
            return None
        
        except Exception as e:
            logger.error(f"❌ Property resolution error: {str(e)}")
            return None
    
    # ============= CREATE CUSTOM PROPERTY (SAFE) =============
    
    def create_custom_property_safe(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        property_name: str,  # "Length", "Width", "Height"
        property_value: float,  # Pre-resolved value
        unit: str = "mm"
    ) -> bool:
        """
        Create a custom property with a STATIC VALUE (not computed)
        
        This avoids computed property execution errors by using
        string values instead of computed properties
        
        Returns True if successful, False otherwise
        """
        try:
            logger.info(f"📝 Creating custom property: {property_name} = {property_value}{unit}")
            
            # Format value as string (most reliable)
            property_value_str = f"{property_value:.2f}"
            
            # Build metadata update payload
            url = f"https://cad.onshape.com/api/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            payload = {
                "jsonType": "metadata-part",
                "partId": part_id,
                "properties": [
                    {
                        "name": property_name,
                        "value": property_value_str,  # String value, not computed
                        "valueType": "STRING"  # Explicit type to avoid computation
                    }
                ]
            }
            
            logger.debug(f"   Payload: {payload}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"   ✅ Custom property created successfully")
                return True
            else:
                logger.error(f"   ❌ Failed ({response.status_code}): {response.text[:200]}")
                return False
        
        except Exception as e:
            logger.error(f"   ❌ Error creating property: {str(e)}")
            return False
    
    # ============= BATCH CREATE PROPERTIES WITH SMART RESOLUTION =============
    
    def create_length_properties_smart(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        bom_items: List[Dict],
        use_config_vars: bool = True,
        use_bbox: bool = True
    ) -> Dict[str, Any]:
        """
        Create Length, Width, Height properties for all parts with smart resolution
        
        Returns:
        {
            "status": "success" | "partial" | "failed",
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "details": [
                {
                    "part_id": "...",
                    "part_name": "...",
                    "length": 100.5,
                    "width": 50.25,
                    "height": 25.75,
                    "created": True,
                    "reason": "Used bbox"
                }
            ]
        }
        """
        try:
            logger.info(f"📐 Creating length properties for {len(bom_items)} parts (smart resolution)")
            logger.info(f"   Use config vars: {use_config_vars} | Use bbox: {use_bbox}")
            
            created_count = 0
            skipped_count = 0
            errors = []
            details = []
            
            for idx, item in enumerate(bom_items, 1):
                try:
                    part_id = item.get("partId") or item.get("id")
                    part_name = item.get("name", f"Part {idx}")
                    
                    if not part_id:
                        logger.warning(f"   [{idx}] No part ID, skipping")
                        skipped_count += 1
                        continue
                    
                    logger.info(f"   [{idx}] Processing: {part_name} ({part_id[:8]})")
                    
                    # Resolve values
                    length_val = self.resolve_property_value(
                        doc_id, workspace_id, element_id, part_id,
                        "Length",
                        config_var_name="PartLength" if use_config_vars else None
                    )
                    
                    width_val = self.resolve_property_value(
                        doc_id, workspace_id, element_id, part_id,
                        "Width",
                        config_var_name="PartWidth" if use_config_vars else None
                    )
                    
                    height_val = self.resolve_property_value(
                        doc_id, workspace_id, element_id, part_id,
                        "Height",
                        config_var_name="PartHeight" if use_config_vars else None
                    )
                    
                    # Check if any value resolved
                    has_values = length_val or width_val or height_val
                    
                    if not has_values:
                        logger.warning(f"      ⚠️ No values resolved, skipping")
                        errors.append(f"Part {part_id[:8]}: No values resolved")
                        skipped_count += 1
                        continue
                    
                    # Create properties
                    success = True
                    reason = []
                    
                    if length_val:
                        if self.create_custom_property_safe(
                            doc_id, workspace_id, element_id, part_id,
                            "Length", length_val, "mm"
                        ):
                            reason.append("Length created")
                        else:
                            success = False
                    
                    if width_val:
                        if self.create_custom_property_safe(
                            doc_id, workspace_id, element_id, part_id,
                            "Width", width_val, "mm"
                        ):
                            reason.append("Width created")
                        else:
                            success = False
                    
                    if height_val:
                        if self.create_custom_property_safe(
                            doc_id, workspace_id, element_id, part_id,
                            "Height", height_val, "mm"
                        ):
                            reason.append("Height created")
                        else:
                            success = False
                    
                    if success:
                        created_count += 1
                        logger.info(f"      ✅ {', '.join(reason)}")
                    else:
                        errors.append(f"Part {part_id[:8]}: Partial creation")
                        logger.warning(f"      ⚠️ Partial creation")
                    
                    details.append({
                        "part_id": part_id,
                        "part_name": part_name,
                        "length": length_val,
                        "width": width_val,
                        "height": height_val,
                        "created": success,
                        "reason": " | ".join(reason) or "Failed"
                    })
                
                except Exception as e:
                    logger.error(f"   [{idx}] Error: {str(e)}")
                    errors.append(f"Part {idx}: {str(e)[:50]}")
                    skipped_count += 1
            
            status = "success" if created_count > 0 else "partial" if skipped_count > 0 else "failed"
            
            logger.info(f"📊 Complete: Created={created_count}, Skipped={skipped_count}, Errors={len(errors)}")
            
            return {
                "status": status,
                "created": created_count,
                "skipped": skipped_count,
                "total": len(bom_items),
                "errors": errors,
                "details": details,
                "message": f"Created {created_count}/{len(bom_items)} properties"
            }
        
        except Exception as e:
            logger.error(f"❌ Batch creation error: {str(e)}")
            return {
                "status": "failed",
                "created": 0,
                "skipped": len(bom_items),
                "total": len(bom_items),
                "errors": [str(e)],
                "details": [],
                "message": f"Failed: {str(e)}"
            }