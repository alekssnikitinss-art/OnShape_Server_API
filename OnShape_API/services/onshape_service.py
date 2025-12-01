import requests
from config import settings
from typing import List, Dict, Any

class OnShapeService:
    """Service for interacting with OnShape API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_documents(self) -> List[Dict]:
        """Get user's documents"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/documents",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("items", [])
    
    def get_elements(self, document_id: str, workspace_id: str) -> List[Dict]:
        """Get elements in a document/workspace"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/documents/d/{document_id}/w/{workspace_id}/elements",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_bom(self, document_id: str, workspace_id: str, element_id: str, indented: bool = False) -> Dict:
        """Get BOM for assembly"""
        url = f"{settings.ONSHAPE_API_URL}/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/bom"
        params = {"indented": "true" if indented else "false"}
        
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_bounding_boxes(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get bounding boxes for part studio"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/boundingboxes",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_parts(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get parts in part studio"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/parts/d/{document_id}/w/{workspace_id}/e/{element_id}",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_metadata(self, document_id: str, workspace_id: str, element_id: str, part_id: str) -> Dict:
        """Get metadata for a part"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def update_metadata(self, document_id: str, workspace_id: str, element_id: str, 
                       part_id: str, properties: List[Dict]) -> Dict:
        """Update metadata for a part"""
        metadata_url = f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}"
        
        payload = {
            "items": [{
                "href": f"{settings.ONSHAPE_API_URL}/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
                "properties": properties
            }]
        }
        
        response = requests.post(metadata_url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_configuration_variables(self, document_id: str, workspace_id: str, element_id: str) -> Dict:
        """Get configuration variables"""
        response = requests.get(
            f"{settings.ONSHAPE_API_URL}/elements/d/{document_id}/w/{workspace_id}/e/{element_id}/configuration",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()