"""
services/metadata_service.py - Handle OnShape Metadata READ/WRITE Operations
Properly implements the OnShape metadata endpoint with correct request/response format
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from config import settings

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for reading and writing OnShape part metadata"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.timeout = 30
    
    # ============= READ OPERATIONS =============
    
    def get_part_metadata(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific part
        This retrieves ALL properties and their IDs for the part
        
        Returns:
        {
            "items": [{
                "href": "...",
                "properties": [
                    {
                        "propertyId": "57f3fb8efa3416c06701d60d",
                        "value": "100"
                    }
                ]
            }]
        }
        """
        try:
            url = f"{settings.ONSHAPE_API_URL}/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            logger.info(f"📖 GET metadata for part: {part_id}")
            logger.info(f"   URL: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            logger.info(f"   Response status: {response.status_code}")
            
            # 404 is normal - means no custom properties
            if response.status_code == 404:
                logger.info(f"⚠️ No metadata found (part has no custom properties)")
                return None
            
            if response.status_code != 200:
                logger.error(f"❌ GET error {response.status_code}: {response.text}")
                raise Exception(f"GET metadata failed: {response.text}")
            
            metadata = response.json()
            logger.info(f"✅ Retrieved metadata with {len(self._get_properties(metadata))} properties")
            
            return metadata
        
        except Exception as e:
            logger.error(f"❌ Error getting metadata: {str(e)}")
            raise
    
    # ============= WRITE OPERATIONS =============
    
    def update_part_metadata(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        part_id: str,
        property_updates: Dict[str, str]
    ) -> bool:
        """
        Update custom properties for a part
        
        Args:
            doc_id: Document ID
            workspace_id: Workspace ID
            element_id: Element ID (PartStudio or Assembly)
            part_id: Part ID
            property_updates: Dict of {propertyName: newValue}
                Example: {"Length": "100", "Material": "Aluminum"}
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"✏️ Updating metadata for part: {part_id}")
            logger.info(f"   Properties to update: {property_updates}")
            
            # Step 1: GET current metadata to get propertyIds
            current_metadata = self.get_part_metadata(doc_id, workspace_id, element_id, part_id)
            
            if current_metadata is None:
                logger.warning(f"⚠️ Part has no existing metadata. Cannot update.")
                return False
            
            # Step 2: Extract propertyIds and build update payload
            property_map = self._build_property_map(current_metadata)
            logger.info(f"   Found {len(property_map)} existing properties: {list(property_map.keys())}")
            
            # Step 3: Build the correct request body
            update_body = self._build_update_body(
                current_metadata,
                property_updates,
                property_map
            )
            
            if not update_body:
                logger.warning(f"⚠️ No valid properties to update")
                return False
            
            # Step 4: POST to update metadata
            url = f"{settings.ONSHAPE_API_URL}/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            # Add configuration parameter - IMPORTANT!
            url += "?configuration=default"
            
            logger.info(f"📤 POST to: {url}")
            logger.info(f"   Body: {update_body}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=update_body,
                timeout=self.timeout
            )
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ POST error {response.status_code}: {response.text}")
                return False
            
            logger.info(f"✅ Successfully updated metadata for part {part_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error updating metadata: {str(e)}")
            return False
    
    # ============= BATCH OPERATIONS =============
    
    def update_multiple_parts(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        parts_updates: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Update metadata for multiple parts
        
        Args:
            doc_id: Document ID
            workspace_id: Workspace ID
            element_id: Element ID
            parts_updates: List of {
                "partId": "xxx",
                "updates": {"Length": "100", "Material": "Steel"}
            }
        
        Returns:
            Dict of {partId: success}
        """
        results = {}
        
        logger.info(f"📝 Updating {len(parts_updates)} parts...")
        
        for idx, part_update in enumerate(parts_updates, 1):
            part_id = part_update.get("partId")
            updates = part_update.get("updates", {})
            
            logger.info(f"   [{idx}/{len(parts_updates)}] Updating part {part_id}...")
            
            success = self.update_part_metadata(
                doc_id,
                workspace_id,
                element_id,
                part_id,
                updates
            )
            
            results[part_id] = success
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ Updated {success_count}/{len(parts_updates)} parts successfully")
        
        return results
    
    # ============= HELPER METHODS =============
    
    def _get_properties(self, metadata: Optional[Dict]) -> List[Dict]:
        """Extract properties list from metadata response"""
        if not metadata:
            return []
        
        items = metadata.get("items", [])
        if not items or len(items) == 0:
            return []
        
        return items[0].get("properties", [])
    
    def _build_property_map(self, metadata: Dict) -> Dict[str, str]:
        """
        Build map of {propertyName: propertyId} from metadata
        
        Example output:
        {
            "Length": "57f3fb8efa3416c06701d60d",
            "Material": "57f3fb8efa3416c06701d60e"
        }
        """
        prop_map = {}
        properties = self._get_properties(metadata)
        
        for prop in properties:
            # Note: OnShape returns propertyId in metadata
            # But doesn't always include the property name
            # So we use the propertyId as both key and value
            prop_id = prop.get("propertyId")
            if prop_id:
                prop_map[prop_id] = prop_id
        
        return prop_map
    
    def _build_update_body(
        self,
        current_metadata: Dict,
        property_updates: Dict[str, str],
        property_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Build the correct request body for POST update
        
        OnShape requires:
        {
            "items": [{
                "href": "...",  # From current metadata
                "properties": [{
                    "propertyId": "...",  # From property_map
                    "value": "..."  # New value
                }]
            }]
        }
        """
        try:
            items = current_metadata.get("items", [])
            if not items or len(items) == 0:
                logger.error("❌ No items in metadata")
                return None
            
            current_item = items[0]
            current_href = current_item.get("href")
            current_properties = current_item.get("properties", [])
            
            if not current_href:
                logger.error("❌ No href in metadata")
                return None
            
            # Build new properties array with updated values
            updated_properties = []
            
            for current_prop in current_properties:
                prop_id = current_prop.get("propertyId")
                current_value = current_prop.get("value")
                
                # Check if this property should be updated
                new_value = property_updates.get(prop_id)
                
                if new_value is not None:
                    logger.info(f"   Updating {prop_id}: '{current_value}' → '{new_value}'")
                    updated_properties.append({
                        "propertyId": prop_id,
                        "value": new_value
                    })
                else:
                    # Keep existing value
                    updated_properties.append({
                        "propertyId": prop_id,
                        "value": current_value
                    })
            
            if not updated_properties:
                logger.warning("⚠️ No properties to update")
                return None
            
            # Build final body
            body = {
                "items": [{
                    "href": current_href,
                    "properties": updated_properties
                }]
            }
            
            return body
        
        except Exception as e:
            logger.error(f"❌ Error building update body: {str(e)}")
            return None