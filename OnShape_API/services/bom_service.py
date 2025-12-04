from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BOMService:
    """Service for processing BOM data"""
    
    @staticmethod
    def calculate_dimensions(bounding_box: Dict) -> Dict:
        """Calculate Length, Width, Height from bounding box"""
        try:
            # Handle different response formats
            if not isinstance(bounding_box, dict):
                logger.warning(f"⚠️ bounding_box is not a dict: {type(bounding_box)}")
                return {
                    "length": 0,
                    "width": 0,
                    "height": 0,
                    "volume": 0
                }
            
            # Extract coordinates
            low_x = float(bounding_box.get("lowX", 0))
            low_y = float(bounding_box.get("lowY", 0))
            low_z = float(bounding_box.get("lowZ", 0))
            high_x = float(bounding_box.get("highX", 0))
            high_y = float(bounding_box.get("highY", 0))
            high_z = float(bounding_box.get("highZ", 0))
            
            # Convert to millimeters
            length_x = (high_x - low_x) * 1000
            length_y = (high_y - low_y) * 1000
            length_z = (high_z - low_z) * 1000
            
            # Sort to get L, W, H
            dimensions = sorted([length_x, length_y, length_z], reverse=True)
            
            result = {
                "length": round(dimensions[0], 2),
                "width": round(dimensions[1], 2),
                "height": round(dimensions[2], 2),
                "volume": round(dimensions[0] * dimensions[1] * dimensions[2], 2)
            }
            
            logger.info(f"📐 Calculated dimensions: L={result['length']}, W={result['width']}, H={result['height']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ calculate_dimensions error: {str(e)}")
            return {
                "length": 0,
                "width": 0,
                "height": 0,
                "volume": 0
            }
    
    @staticmethod
    def process_bom_items(items: List[Dict]) -> List[Dict]:
        """Process and clean BOM items"""
        try:
            if not isinstance(items, list):
                logger.warning(f"⚠️ items is not a list: {type(items)}")
                return []
            
            processed = []
            
            for item in items:
                if not isinstance(item, dict):
                    logger.warning(f"⚠️ BOM item is not a dict: {type(item)}")
                    continue
                
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
            
            logger.info(f"✅ Processed {len(processed)} BOM items")
            return processed
            
        except Exception as e:
            logger.error(f"❌ process_bom_items error: {str(e)}")
            return []
    
    @staticmethod
    def create_property_objects(dimensions: Dict, part_name: str = "") -> List[Dict]:
        """Create property objects for OnShape metadata"""
        try:
            return [
                {
                    "name": "Length",
                    "value": f"{dimensions.get('length', 0):.2f} mm",
                    "valueType": "STRING"
                },
                {
                    "name": "Width",
                    "value": f"{dimensions.get('width', 0):.2f} mm",
                    "valueType": "STRING"
                },
                {
                    "name": "Height",
                    "value": f"{dimensions.get('height', 0):.2f} mm",
                    "valueType": "STRING"
                }
            ]
        except Exception as e:
            logger.error(f"❌ create_property_objects error: {str(e)}")
            return []