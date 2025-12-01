from typing import List, Dict, Any

class BOMService:
    """Service for processing BOM data"""
    
    @staticmethod
    def calculate_dimensions(bounding_box: Dict) -> Dict:
        """Calculate Length, Width, Height from bounding box"""
        length_x = (bounding_box.get("highX", 0) - bounding_box.get("lowX", 0)) * 1000  # mm
        length_y = (bounding_box.get("highY", 0) - bounding_box.get("lowY", 0)) * 1000
        length_z = (bounding_box.get("highZ", 0) - bounding_box.get("lowZ", 0)) * 1000
        
        dimensions = sorted([length_x, length_y, length_z], reverse=True)
        
        return {
            "length": round(dimensions[0], 2),
            "width": round(dimensions[1], 2),
            "height": round(dimensions[2], 2),
            "volume": round(dimensions[0] * dimensions[1] * dimensions[2], 2)
        }
    
    @staticmethod
    def process_bom_items(items: List[Dict]) -> List[Dict]:
        """Process and clean BOM items"""
        processed = []
        
        for item in items:
            processed.append({
                "item": item.get("item", "-"),
                "partNumber": item.get("partNumber", item.get("PART_NUMBER", "-")),
                "name": item.get("name", item.get("NAME", "-")),
                "quantity": item.get("quantity", item.get("QUANTITY", "-")),
                "description": item.get("description", item.get("DESCRIPTION", "-")),
                "indentLevel": item.get("indentLevel", 0),
                "hasChildren": item.get("hasChildren", False),
                "parentId": item.get("parentId", None)
            })
        
        return processed
    
    @staticmethod
    def create_property_objects(dimensions: Dict, part_name: str = "") -> List[Dict]:
        """Create property objects for OnShape metadata"""
        return [
            {
                "name": "Length",
                "value": f"{dimensions['length']:.2f} mm",
                "valueType": "STRING"
            },
            {
                "name": "Width",
                "value": f"{dimensions['width']:.2f} mm",
                "valueType": "STRING"
            },
            {
                "name": "Height",
                "value": f"{dimensions['height']:.2f} mm",
                "valueType": "STRING"
            }
        ]