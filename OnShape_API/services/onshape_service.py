import requests
from config import settings
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OnShapeService:
    """Service for interacting with OnShape API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        # INCREASED TIMEOUT: OnShape API can be slow
        self.timeout = 30  # 30 seconds instead of 10
    
    def get_documents(self) -> List[Dict]:
        """Get user's documents"""
        try:
            response = requests.get(
                f"{settings.ONSHAPE_API_URL}/documents",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"❌ get_documents error: {str(e)}")
            raise
    
    def get_elements(self, document_id: str, workspace_id: str) -> List[Dict]:
        """Get elements in a document/workspace"""
        try:
            response = requests.get(
                f"{settings.ONSHAPE_API_URL}/documents/d/{document_id}/w/{workspace_id}/elements",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ get_elements error: {str(e)}")
            raise
    
    def get_bom(self, document_id: str, workspace_id: str, element_id: str, indented: bool = False) -> Dict:
        """Get BOM for assembly"""
        try:
            url = f"{settings.ONSHAPE_API_URL}/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/bom"
            params = {"indented": "true" if indented else "false"}
            
            logger.info(f"🔄 Fetching BOM from OnShape (timeout={self.timeout}s)...")
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ get_bom error: {str(e)}")
            raise
    
    def get_bounding_boxes(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get bounding boxes for part studio"""
        try:
            url = f"{settings.ONSHAPE_API_URL}/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/boundingboxes"
            
            logger.info(f"📏 Fetching bounding boxes (timeout={self.timeout}s)...")
            logger.info(f"   URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            logger.info(f"   Response status: {response.status_code}")
            logger.info(f"   Response headers: {response.headers}")
            logger.info(f"   Response body (first 500 chars): {response.text[:500]}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"   Parsed JSON type: {type(result)}")
            
            # Handle different response formats
            if isinstance(result, dict):
                # If it's wrapped, unwrap it
                if "items" in result:
                    bboxes = result["items"]
                    logger.info(f"✅ Got {len(bboxes)} bboxes from 'items' field")
                elif "boundingBoxes" in result:
                    bboxes = result["boundingBoxes"]
                    logger.info(f"✅ Got {len(bboxes)} bboxes from 'boundingBoxes' field")
                elif "data" in result:
                    bboxes = result["data"]
                    logger.info(f"✅ Got {len(bboxes)} bboxes from 'data' field")
                else:
                    # Assume the dict itself is a bbox list or return as-is
                    bboxes = result
                    logger.warning(f"⚠️ Unknown response format, returning as-is")
            elif isinstance(result, list):
                bboxes = result
                logger.info(f"✅ Got {len(bboxes)} bboxes from list")
            else:
                logger.error(f"❌ Unexpected response type: {type(result)}")
                raise Exception(f"Unexpected response type: {type(result)}")
            
            # Ensure it's a list of dicts, not strings
            if isinstance(bboxes, list) and len(bboxes) > 0:
                logger.info(f"   First bbox type: {type(bboxes[0])}")
                if isinstance(bboxes[0], str):
                    logger.error(f"❌ Bboxes are strings, not dicts!")
                    return []
            
            return bboxes if isinstance(bboxes, list) else [bboxes]
            
        except Exception as e:
            logger.error(f"❌ get_bounding_boxes error: {str(e)}")
            raise
    
    def get_parts(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get parts in part studio"""
        try:
            response = requests.get(
                f"{settings.ONSHAPE_API_URL}/parts/d/{document_id}/w/{workspace_id}/e/{element_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ get_parts error: {str(e)}")
            raise
    
    def get_metadata(self, document_id: str, workspace_id: str, element_id: str, part_id: str) -> Dict:
        """Get metadata for a part"""
        try:
            response = requests.get(
                f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ get_metadata error: {str(e)}")
            raise
    
    def update_metadata(self, document_id: str, workspace_id: str, element_id: str, 
                       part_id: str, properties: List[Dict]) -> Dict:
        """Update metadata for a part"""
        try:
            metadata_url = f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}"
            
            payload = {
                "items": [{
                    "href": f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
                    "properties": properties
                }]
            }
            
            response = requests.post(metadata_url, headers=self.headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ update_metadata error: {str(e)}")
            raise
    
    def get_configuration_variables(self, document_id: str, workspace_id: str, element_id: str) -> Dict:
        """Get configuration variables"""
        try:
            response = requests.get(
                f"{settings.ONSHAPE_API_URL}/elements/d/{document_id}/w/{workspace_id}/e/{element_id}/configuration",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ get_configuration_variables error: {str(e)}")
            raise