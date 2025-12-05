
import requests
from requests.exceptions import HTTPError  
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
        self.timeout = 30
    
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
        """Get BOM for assembly or parts list for PartStudio"""
        try:
            logger.info(f"🔄 Trying Assembly BOM endpoint...")
            url = f"{settings.ONSHAPE_API_URL}/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/bom"
            params = {"indented": "true" if indented else "false"}
            
            logger.info(f"📍 URL: {url}")
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                logger.info(f"✅ Got BOM from Assembly endpoint")
                return response.json()
            
            logger.warning(f"⚠️ Assembly endpoint returned {response.status_code}, trying PartStudio parts...")
            
            url_parts = f"{settings.ONSHAPE_API_URL}/parts/d/{document_id}/w/{workspace_id}/e/{element_id}"
            logger.info(f"📍 Trying PartStudio parts: {url_parts}")
            
            response_parts = requests.get(url_parts, headers=self.headers, timeout=self.timeout)
            
            if response_parts.status_code == 200:
                logger.info(f"✅ Got parts from PartStudio endpoint")
                parts_data = response_parts.json()
                
                bom_items = []
                if isinstance(parts_data, list):
                    for idx, part in enumerate(parts_data, 1):
                        bom_items.append({
                            "item": idx,
                            "partNumber": part.get("partNumber", part.get("name", "-")),
                            "name": part.get("name", "-"),
                            "quantity": 1,
                            "description": part.get("description", ""),
                            "partId": part.get("id", "")
                        })
                
                return {
                    "bomTable": {
                        "items": bom_items
                    },
                    "type": "PartStudio"
                }
            
            logger.error(f"❌ Both Assembly and PartStudio endpoints failed")
            raise Exception(f"Element is neither Assembly nor PartStudio, or not accessible")
            
        except Exception as e:
            logger.error(f"❌ get_bom error: {str(e)}")
            raise
    
    def get_bounding_boxes(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get bounding boxes for part studio OR assembly"""
        try:
            url = f"{settings.ONSHAPE_API_URL}/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/boundingboxes"
            
            logger.info(f"📏 Fetching bounding boxes (timeout={self.timeout}s)...")
            logger.info(f"   URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            logger.info(f"   Response status: {response.status_code}")
            
            # If PartStudio works, return it
            if response.status_code == 200:
                logger.info(f"✅ Got bounding boxes from PartStudio endpoint")
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, dict):
                    if "items" in result:
                        bboxes = result["items"]
                    elif "boundingBoxes" in result:
                        bboxes = result["boundingBoxes"]
                    else:
                        bboxes = result
                elif isinstance(result, list):
                    bboxes = result
                else:
                    bboxes = []
                
                return bboxes if isinstance(bboxes, list) else [bboxes]
            
            # If PartStudio fails (400), try Assembly approach
            logger.warning(f"⚠️ PartStudio endpoint returned {response.status_code}")
            logger.info(f"🔄 Trying Assembly approach: get all parts and their bboxes...")
            
            # Get all parts in the assembly
            try:
                parts_url = f"{settings.ONSHAPE_API_URL}/parts/d/{document_id}/w/{workspace_id}/e/{element_id}"
                logger.info(f"   Fetching parts from: {parts_url}")
                
                parts_response = requests.get(parts_url, headers=self.headers, timeout=self.timeout)
                parts_response.raise_for_status()
                
                parts_data = parts_response.json()
                logger.info(f"✅ Got {len(parts_data) if isinstance(parts_data, list) else '?'} parts")
                
                # If we got parts, return them as-is
                # (Assembly parts don't have traditional bounding boxes)
                if isinstance(parts_data, list):
                    logger.info(f"📦 Returning {len(parts_data)} parts from Assembly")
                    return parts_data
                else:
                    logger.warning(f"⚠️ Parts response is not a list: {type(parts_data)}")
                    return []
                    
            except Exception as e:
                logger.error(f"❌ Assembly approach also failed: {str(e)}")
                # If both fail, raise original error
                raise HTTPError(f"Element is neither PartStudio nor accessible Assembly", response=response)
        
        except Exception as e:
            logger.error(f"❌ get_bounding_boxes error: {str(e)}")
            raise