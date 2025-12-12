"""
services/length_property_resolver.py - Smart Length Property Resolver
Intelligently extracts Length from configuration variables
Only for parts with 'Units - Millimeter' property

Solves: "Vai ir iespējams dabūt no configurācijām Length un to rādīt kā property?"
"""

import logging
import re
from typing import Dict, List, Any, Optional
from services.onshape_service import OnShapeService

logger = logging.getLogger(__name__)


class LengthPropertyResolver:
    """
    Smart resolver for getting Length values from part configurations
    
    Strategy:
    1. Check if part has 'Units - Millimeter' property
    2. If yes, search for Length variable in configuration
    3. Extract numeric value
    4. Convert to millimeters if needed
    5. Return as Length property
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.onshape = OnShapeService(access_token)
    
    # ============= MAIN WORKFLOW =============
    
    def resolve_length_properties(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        bom_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        Main workflow: Extract Length properties from configurations
        
        Returns:
        {
            "total_items": 25,
            "items_processed": 20,
            "items_with_units_mm": 15,
            "items_with_length_found": 12,
            "items_with_length_property": 12,
            "results": [...]
        }
        """
        
        logger.info(f"🔍 Starting Length Property resolution for {len(bom_items)} items...")
        
        results = []
        items_with_units = 0
        items_with_length = 0
        items_successfully_resolved = 0
        
        for item in bom_items:
            part_id = item.get("partId") or item.get("id")
            item_number = item.get("item", "?")
            part_name = item.get("name", "Unknown")
            
            try:
                logger.info(f"   [{item_number}] Processing: {part_name}...")
                
                # Step 1: Check if part has 'Units - Millimeter' property
                has_units_mm = self._check_units_millimeter(
                    doc_id, workspace_id, element_id, part_id
                )
                
                result_data = {
                    "item": item_number,
                    "part_id": part_id,
                    "name": part_name,
                    "has_units_mm": has_units_mm,
                    "length_found": None,
                    "length_unit": None,
                    "length_mm": None,
                    "status": "pending",
                    "message": ""
                }
                
                if has_units_mm:
                    items_with_units += 1
                    
                    # Step 2: Get length value for part
                    length_value = self._extract_length_from_config(
                        doc_id, workspace_id, element_id, part_id, part_name
                    )
                    
                    if length_value:
                        items_with_length += 1
                        result_data["length_found"] = str(length_value["value"])
                        result_data["length_unit"] = length_value["unit"]
                        result_data["length_mm"] = length_value["mm"]
                        result_data["status"] = "success"
                        result_data["message"] = "Length extracted from configuration"
                        items_successfully_resolved += 1
                        logger.info(f"      ✅ Length found: {length_value['value']} {length_value['unit']}")
                    else:
                        result_data["status"] = "no_length_found"
                        result_data["message"] = "Part has Units-MM but no Length variable found"
                        logger.info(f"      ⚠️ No Length variable found")
                else:
                    result_data["status"] = "no_units_mm"
                    result_data["message"] = "Part doesn't have 'Units - Millimeter' property"
                    logger.info(f"      ⏭️ Skipped (no Units-MM property)")
                
            except Exception as e:
                logger.warning(f"      ❌ Error processing {part_name}: {str(e)}")
                result_data["status"] = "error"
                result_data["message"] = str(e)
            
            results.append(result_data)
        
        logger.info(f"✅ Resolution complete:")
        logger.info(f"   Total items: {len(bom_items)}")
        logger.info(f"   Items with Units-MM: {items_with_units}")
        logger.info(f"   Items with Length found: {items_with_length}")
        logger.info(f"   Successfully resolved: {items_successfully_resolved}")
        
        return {
            "total_items": len(bom_items),
            "items_processed": len(bom_items),
            "items_with_units_mm": items_with_units,
            "items_with_length_found": items_with_length,
            "items_with_length_property": items_successfully_resolved,
            "results": results,
            "summary": {
                "success_rate": round(items_successfully_resolved / len(bom_items) * 100, 1) if bom_items else 0,
                "message": f"Successfully resolved {items_successfully_resolved} Length properties from {items_with_units} parts with Units-MM"
            }
        }
    
    # ============= STEP 1: CHECK UNITS-MM PROPERTY =============
    
    def _check_units_millimeter(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str
    ) -> bool:
        """Check if part has 'Units - Millimeter' property"""
        try:
            if not part_id:
                return False
            
            url = f"https://cad.onshape.com/api/v10/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            response = self.onshape._make_request("get", url, timeout=30)
            
            if response.status_code != 200:
                logger.debug(f"      ℹ️ Could not get metadata (status {response.status_code})")
                return False
            
            metadata = response.json()
            
            if "items" in metadata and len(metadata["items"]) > 0:
                properties = metadata["items"][0].get("properties", [])
                
                for prop in properties:
                    prop_name = prop.get("name", "").lower()
                    prop_value = str(prop.get("value", "")).lower()
                    
                    if "units" in prop_name and "millimeter" in prop_value:
                        logger.debug(f"      ✓ Found Units-MM property")
                        return True
                    
                    if "unit" in prop_name and ("mm" in prop_value or "millimeter" in prop_value):
                        logger.debug(f"      ✓ Found Units property with MM")
                        return True
            
            return False
        
        except Exception as e:
            logger.debug(f"      ⚠️ Error checking Units-MM: {str(e)}")
            return False
    
    # ============= STEP 2: EXTRACT LENGTH FROM CONFIG =============
    
    def _extract_length_from_config(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        part_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract Length value from part configuration using multiple strategies"""
        
        strategies = [
            self._get_from_variables,
            self._get_from_part_properties,
            self._get_from_part_name,
        ]
        
        for strategy in strategies:
            try:
                length_value = strategy(doc_id, workspace_id, element_id, part_id, part_name)
                if length_value:
                    return length_value
            except Exception as e:
                logger.debug(f"      Strategy failed: {str(e)}")
                continue
        
        return None
    
    def _get_from_variables(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        part_name: str
    ) -> Optional[Dict[str, Any]]:
        """Strategy 1: Get Length from configuration variables"""
        try:
            url = f"https://cad.onshape.com/api/v3/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/variables"
            
            response = self.onshape._make_request("get", url, timeout=30)
            
            if response.status_code == 200:
                variables = response.json()
                
                if isinstance(variables, list):
                    for var in variables:
                        var_name = var.get("name", "").lower()
                        var_value = var.get("value") or var.get("expression")
                        
                        if "length" in var_name:
                            length_mm = self._parse_value_to_mm(var_value, var.get("units"))
                            if length_mm is not None:
                                logger.debug(f"      Found from variables: {var.get('name')}")
                                return {
                                    "value": var_value,
                                    "unit": var.get("units", "unknown"),
                                    "mm": length_mm,
                                    "source": "configuration_variable"
                                }
        
        except Exception as e:
            logger.debug(f"      Variables strategy: {str(e)}")
        
        return None
    
    def _get_from_part_properties(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        part_name: str
    ) -> Optional[Dict[str, Any]]:
        """Strategy 2: Get Length from part metadata properties"""
        try:
            url = f"https://cad.onshape.com/api/v10/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            response = self.onshape._make_request("get", url, timeout=30)
            
            if response.status_code == 200:
                metadata = response.json()
                
                if "items" in metadata and len(metadata["items"]) > 0:
                    properties = metadata["items"][0].get("properties", [])
                    
                    for prop in properties:
                        prop_name = prop.get("name", "").lower()
                        prop_value = str(prop.get("value", ""))
                        
                        if "length" in prop_name:
                            length_mm = self._parse_value_to_mm(prop_value)
                            if length_mm is not None:
                                logger.debug(f"      Found from properties: {prop.get('name')}")
                                return {
                                    "value": prop_value,
                                    "unit": "mm",
                                    "mm": length_mm,
                                    "source": "metadata_property"
                                }
        
        except Exception as e:
            logger.debug(f"      Properties strategy: {str(e)}")
        
        return None
    
    def _get_from_part_name(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        part_name: str
    ) -> Optional[Dict[str, Any]]:
        """Strategy 3: Extract Length from part name (e.g., 'Bracket_50mm' → 50)"""
        try:
            patterns = [
                r'(\d+\.?\d*)\s*mm',
                r'(\d+\.?\d*)\s*x',
                r'_(\d+\.?\d*)',
                r'-(\d+\.?\d*)',
            ]
            
            part_name_lower = part_name.lower()
            
            for pattern in patterns:
                match = re.search(pattern, part_name_lower)
                if match:
                    value = float(match.group(1))
                    
                    if 0.1 < value < 10000:
                        logger.debug(f"      Found from name: {part_name} → {value}mm")
                        return {
                            "value": value,
                            "unit": "mm",
                            "mm": value,
                            "source": "part_name"
                        }
        
        except Exception as e:
            logger.debug(f"      Name pattern strategy: {str(e)}")
        
        return None
    
    # ============= HELPER: PARSE VALUE TO MM =============
    
    def _parse_value_to_mm(
        self,
        value: Any,
        unit: str = None
    ) -> Optional[float]:
        """Parse any value to millimeters"""
        
        try:
            value_str = str(value).lower().strip()
            
            numbers = re.findall(r'(\d+\.?\d*)', value_str)
            if not numbers:
                return None
            
            numeric_value = float(numbers[0])
            
            if unit:
                unit_str = unit.lower()
            else:
                unit_str = value_str
            
            if "mm" in unit_str or "millimeter" in unit_str:
                return round(numeric_value, 2)
            elif "cm" in unit_str or "centimeter" in unit_str:
                return round(numeric_value * 10, 2)
            elif "m" in unit_str and "mm" not in unit_str:
                return round(numeric_value * 1000, 2)
            elif "inch" in unit_str or '"' in unit_str:
                return round(numeric_value * 25.4, 2)
            elif "ft" in unit_str or "foot" in unit_str:
                return round(numeric_value * 304.8, 2)
            else:
                return round(numeric_value, 2)
        
        except Exception as e:
            logger.debug(f"Could not parse {value}: {str(e)}")
            return None