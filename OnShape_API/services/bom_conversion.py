"""
services/bom_conversion.py - BOM Unit Conversion & Custom Columns Service
Handles unit conversions and allows custom columns for BOM
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BOMConversionService:
    """Service for converting units and managing custom BOM columns"""
    
    # Conversion factors to MM
    CONVERSION_FACTORS = {
        "mm": 1.0,
        "millimeter": 1.0,
        "millimeters": 1.0,
        "cm": 10.0,
        "centimeter": 10.0,
        "centimeters": 10.0,
        "m": 1000.0,
        "meter": 1000.0,
        "meters": 1000.0,
        "in": 25.4,
        "inch": 25.4,
        "inches": 25.4,
        "ft": 304.8,
        "foot": 304.8,
        "feet": 304.8,
        "yd": 914.4,
        "yard": 914.4,
        "yards": 914.4,
        "µm": 0.001,
        "micrometer": 0.001,
        "micrometers": 0.001,
    }
    
    @staticmethod
    def detect_unit(value_str: str) -> tuple:
        """
        Detect unit from string like "10 mm" or "0.5 in"
        Returns: (number, unit_detected, unit_name)
        """
        try:
            value_str = str(value_str).strip().lower()
            
            # Extract number and unit
            parts = value_str.split()
            if len(parts) >= 1:
                try:
                    number = float(parts[0])
                except ValueError:
                    logger.warning(f"Could not parse number from: {value_str}")
                    return None, None, None
                
                if len(parts) > 1:
                    unit = parts[1].strip()
                else:
                    # No unit specified
                    logger.warning(f"No unit found in: {value_str}")
                    return number, None, None
                
                # Normalize unit
                unit_normalized = unit.lower()
                
                if unit_normalized in BOMConversionService.CONVERSION_FACTORS:
                    return number, unit_normalized, unit_normalized
                else:
                    logger.warning(f"Unknown unit: {unit}")
                    return number, unit_normalized, None
            
            return None, None, None
            
        except Exception as e:
            logger.error(f"Error detecting unit: {str(e)}")
            return None, None, None
    
    @staticmethod
    def convert_to_mm(value: float, unit: str) -> float:
        """Convert value from any unit to millimeters"""
        try:
            if unit is None:
                logger.warning("No unit specified, assuming MM")
                return value
            
            unit_lower = str(unit).lower().strip()
            
            if unit_lower not in BOMConversionService.CONVERSION_FACTORS:
                logger.warning(f"Unknown unit: {unit_lower}, assuming MM")
                return value
            
            factor = BOMConversionService.CONVERSION_FACTORS[unit_lower]
            result = value * factor
            
            logger.info(f"Converted {value} {unit_lower} = {result} mm")
            return result
            
        except Exception as e:
            logger.error(f"Error converting to mm: {str(e)}")
            return value
    
    @staticmethod
    def convert_string_to_mm(value_str: str) -> tuple:
        """
        Convert string like "10 in" to MM
        Returns: (value_in_mm, original_unit, converted_amount)
        """
        try:
            number, unit_found, unit_name = BOMConversionService.detect_unit(value_str)
            
            if number is None:
                logger.warning(f"Could not parse: {value_str}")
                return None, None, None
            
            if unit_found is None:
                logger.warning(f"No unit detected in: {value_str}")
                return number, None, None
            
            mm_value = BOMConversionService.convert_to_mm(number, unit_found)
            return mm_value, unit_name, number
            
        except Exception as e:
            logger.error(f"Error converting string: {str(e)}")
            return None, None, None
    
    @staticmethod
    def calculate_volume_mm3(length_mm: float, width_mm: float, height_mm: float) -> float:
        """Calculate volume in cubic millimeters"""
        try:
            if any(val is None or val <= 0 for val in [length_mm, width_mm, height_mm]):
                logger.warning("Invalid dimensions for volume calculation")
                return 0
            
            volume = length_mm * width_mm * height_mm
            logger.info(f"Volume: {length_mm}mm × {width_mm}mm × {height_mm}mm = {volume} mm³")
            return volume
            
        except Exception as e:
            logger.error(f"Error calculating volume: {str(e)}")
            return 0
    
    @staticmethod
    def add_custom_column_to_bom_item(item: Dict, column_name: str, value: Any) -> Dict:
        """Add a custom column to a BOM item"""
        try:
            item[column_name] = value
            return item
        except Exception as e:
            logger.error(f"Error adding custom column: {str(e)}")
            return item
    
    @staticmethod
    def process_bom_with_dimensions(
        bom_items: List[Dict],
        length_values: List[str] = None,
        width_values: List[str] = None,
        height_values: List[str] = None
    ) -> List[Dict]:
        """
        Process BOM items and add dimension columns
        
        Args:
            bom_items: List of BOM items
            length_values: List of length values (optional, strings with units)
            width_values: List of width values (optional)
            height_values: List of height values (optional)
        
        Returns:
            BOM items with new columns for dimensions and volume
        """
        try:
            for idx, item in enumerate(bom_items):
                # Add dimension columns
                if length_values and idx < len(length_values):
                    length_mm, unit, original = BOMConversionService.convert_string_to_mm(
                        str(length_values[idx])
                    )
                    if length_mm is not None:
                        item["Length (mm)"] = round(length_mm, 2)
                        item["Length_Original"] = f"{original} {unit}" if unit else str(original)
                
                if width_values and idx < len(width_values):
                    width_mm, unit, original = BOMConversionService.convert_string_to_mm(
                        str(width_values[idx])
                    )
                    if width_mm is not None:
                        item["Width (mm)"] = round(width_mm, 2)
                        item["Width_Original"] = f"{original} {unit}" if unit else str(original)
                
                if height_values and idx < len(height_values):
                    height_mm, unit, original = BOMConversionService.convert_string_to_mm(
                        str(height_values[idx])
                    )
                    if height_mm is not None:
                        item["Height (mm)"] = round(height_mm, 2)
                        item["Height_Original"] = f"{original} {unit}" if unit else str(original)
                
                # Calculate volume if all dimensions present
                if "Length (mm)" in item and "Width (mm)" in item and "Height (mm)" in item:
                    volume = BOMConversionService.calculate_volume_mm3(
                        item["Length (mm)"],
                        item["Width (mm)"],
                        item["Height (mm)"]
                    )
                    item["Volume (mm³)"] = round(volume, 2)
            
            logger.info(f"Processed {len(bom_items)} items with dimensions")
            return bom_items
            
        except Exception as e:
            logger.error(f"Error processing BOM with dimensions: {str(e)}")
            return bom_items
    
    @staticmethod
    def add_bounding_box_dimensions_to_bom(
        bom_items: List[Dict],
        bounding_boxes: List[Dict]
    ) -> List[Dict]:
        """
        Add bounding box dimensions from bbox list to BOM items
        Matches by part ID
        """
        try:
            # Create bbox lookup dictionary
            bbox_map = {}
            for bbox in bounding_boxes:
                part_id = bbox.get("partId") or bbox.get("id")
                if part_id:
                    bbox_map[part_id] = bbox
            
            # Add dimensions to BOM items
            for item in bom_items:
                part_id = item.get("partId") or item.get("id")
                
                if part_id and part_id in bbox_map:
                    bbox = bbox_map[part_id]
                    
                    # Extract dimensions
                    if "dimensions" in bbox:
                        dims = bbox["dimensions"]
                        item["Length_BBox (mm)"] = dims.get("length", 0)
                        item["Width_BBox (mm)"] = dims.get("width", 0)
                        item["Height_BBox (mm)"] = dims.get("height", 0)
                        item["Volume_BBox (mm³)"] = dims.get("volume", 0)
                    elif "lowX" in bbox:
                        # Calculate from raw bbox
                        length = (bbox.get("highX", 0) - bbox.get("lowX", 0)) * 1000
                        width = (bbox.get("highY", 0) - bbox.get("lowY", 0)) * 1000
                        height = (bbox.get("highZ", 0) - bbox.get("lowZ", 0)) * 1000
                        
                        item["Length_BBox (mm)"] = round(length, 2)
                        item["Width_BBox (mm)"] = round(width, 2)
                        item["Height_BBox (mm)"] = round(height, 2)
                        item["Volume_BBox (mm³)"] = round(length * width * height, 2)
            
            logger.info(f"Added bounding box dimensions to {len(bom_items)} items")
            return bom_items
            
        except Exception as e:
            logger.error(f"Error adding bbox dimensions: {str(e)}")
            return bom_items
    
    @staticmethod
    def create_conversion_summary(original_value: str, converted_value: float, original_unit: str) -> Dict:
        """Create a summary of conversion for display"""
        return {
            "original": original_value,
            "converted_to_mm": round(converted_value, 2),
            "unit_detected": original_unit,
            "conversion_successful": True if converted_value is not None else False
        }