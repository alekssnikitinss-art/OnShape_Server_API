"""
services/metadata_service.py - CORRECTED Implementation
Using EXACT OnShape API format from official documentation
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
            "Content-Type": "application/json;charset=UTF-8"
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
        """
        try:
            url = f"{settings.ONSHAPE_API_URL}/v10/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            logger.info(f"📖 GET metadata for part: {part_id}")
            logger.info(f"   URL: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code == 404:
                logger.info(f"⚠️ No metadata found (part has no custom properties)")
                return None
            
            if response.status_code != 200:
                logger.error(f"❌ GET error {response.status_code}: {response.text}")
                raise Exception(f"GET metadata failed: {response.text}")
            
            metadata = response.json()
            logger.info(f"✅ Retrieved metadata with properties")
            
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
            property_updates: Dict of {propertyId: newValue}
                Example: {"propertyId_123": "100", "propertyId_456": "Aluminum"}
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"✏️ Updating metadata for part: {part_id}")
            logger.info(f"   Properties to update: {property_updates}")
            
            # Get current metadata to verify properties exist
            current_metadata = self.get_part_metadata(doc_id, workspace_id, element_id, part_id)
            
            if current_metadata is None:
                logger.warning(f"⚠️ Part has no existing metadata")
                return False
            
            # Build request body using EXACT OnShape format from documentation
            # The key difference: jsonType field and correct structure
            request_body = {
                "jsonType": "metadata-part",
                "partId": part_id,
                "properties": []
            }
            
            # Add properties from the updates dict
            for property_id, new_value in property_updates.items():
                logger.info(f"   Updating property {property_id}: → '{new_value}'")
                request_body["properties"].append({
                    "value": new_value,
                    "propertyId": property_id
                })
            
            if not request_body["properties"]:
                logger.warning(f"⚠️ No valid properties to update")
                return False
            
            # POST to update metadata - CORRECT ENDPOINT with v10
            url = f"{settings.ONSHAPE_API_URL}/v10/metadata/d/{doc_id}/w/{workspace_id}/e/{element_id}/p/{part_id}"
            
            logger.info(f"📤 POST to: {url}")
            logger.info(f"   Body: {request_body}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=request_body,
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
                "updates": {
                    "propertyId_123": "new_value"
                }
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