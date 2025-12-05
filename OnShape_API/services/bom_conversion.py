"""
BOM Unit Converter Service
Converts measurements to MM and calculates volume
Adds custom columns to BOM
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class UnitConverter:
    """Convert units to millimeters"""
    
    # Conversion factors to MM
    CONVERSIONS = {
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
        '"': 25.4,  # " symbol for inches
        "ft": 304.8,
        "foot": 304.8,
        "feet": 304.8,
        "um": 0.001,
        "micrometer": 0.001,
        "micrometers": 0.001,
    }
    
    @staticmethod
    def parse_value_with_unit(value_str: str) -> tuple:
        """
        Parse a string like '10 mm' or '5.5in' into (value, unit)
        Returns: (float_value, unit_string)
        """
        try:
            if not isinstance(value_str, str):
                return float(value_str), "mm"
            
            value_str = value_str.strip().lower()
            
            # Try to extract number and unit
            import re
            match = re.match(r'([\d.]+)\s*([a-z"]*)', value_str)
            
            if match:
                value = float(match.group(1))
                unit = match.group(2).strip() or "mm"
                return value, unit
            
            # If no unit found, assume MM
            return float(value_str), "mm"
        
        except Exception as e:
            logger.warning(f"Could not parse value '{value_str}': {str(e)}")
            return None, None
    
    @staticmethod
    def to_mm(value: float, unit: str) -> float:
        """
        Convert any unit to millimeters
        Returns: value in MM (float)
        """
        try:
            unit_lower = unit.lower().strip()
            
            # Find matching conversion
            if unit_lower in UnitConverter.CONVERSIONS:
                conversion = UnitConverter.CONVERSIONS[unit_lower]
                result = value * conversion
                logger.info(f"✅ Converted {value} {unit} → {result} mm")
                return round(result, 4)
            
            # If unit not found, assume MM
            logger.warning(f"⚠️ Unit '{unit}' not recognized, assuming MM")
            return round(value, 4)
        
        except Exception as e:
            logger.error(f"❌ Conversion error: {str(e)}")
            return value
    
    @staticmethod
    def convert_string_to_mm(value_str: str) -> float:
        """
        Convert a string like '10 in' directly to MM
        Returns: value in MM (float)
        """
        value, unit = UnitConverter.parse_value_with_unit(value_str)
        
        if value is None:
            return None
        
        return UnitConverter.to_mm(value, unit)


class BOMEnhancer:
    """Add custom columns and conversions to BOM"""
    
    @staticmethod
    def add_custom_columns(bom_items: List[Dict], custom_data: Dict = None) -> List[Dict]:
        """
        Add custom columns to BOM items
        Supports: Length, Width, Height, Volume, Custom notes
        
        Args:
            bom_items: List of BOM items
            custom_data: {item_index: {column_name: value}, ...}
        
        Returns: Enhanced BOM items with new columns
        """
        try:
            enhanced = []
            
            for idx, item in enumerate(bom_items):
                enhanced_item = item.copy()
                
                # Initialize custom columns if not present
                if "custom_length_mm" not in enhanced_item:
                    enhanced_item["custom_length_mm"] = None
                if "custom_width_mm" not in enhanced_item:
                    enhanced_item["custom_width_mm"] = None
                if "custom_height_mm" not in enhanced_item:
                    enhanced_item["custom_height_mm"] = None
                if "custom_volume_mm3" not in enhanced_item:
                    enhanced_item["custom_volume_mm3"] = None
                if "custom_notes" not in enhanced_item:
                    enhanced_item["custom_notes"] = ""
                
                # Add user-provided custom data
                if custom_data and idx in custom_data:
                    for col_name, value in custom_data[idx].items():
                        enhanced_item[f"custom_{col_name}"] = value
                
                enhanced.append(enhanced_item)
            
            logger.info(f"✅ Added custom columns to {len(enhanced)} BOM items")
            return enhanced
        
        except Exception as e:
            logger.error(f"❌ Error adding custom columns: {str(e)}")
            return bom_items
    
    @staticmethod
    def convert_bom_dimensions(bom_items: List[Dict]) -> List[Dict]:
        """
        Convert any dimension columns to MM
        Looks for: length, width, height, size, dimension, etc.
        
        Returns: BOM items with all dimensions in MM
        """
        try:
            converted = []
            
            for item in bom_items:
                converted_item = item.copy()
                
                # Look for dimension-related fields
                dimension_fields = ["length", "width", "height", "size", "dimension", "thickness", "radius", "diameter"]
                
                for field in dimension_fields:
                    # Check both exact and case-insensitive
                    for key in converted_item.keys():
                        if field.lower() in key.lower() and converted_item[key] is not None:
                            # Try to convert value
                            if isinstance(converted_item[key], str):
                                mm_value = UnitConverter.convert_string_to_mm(converted_item[key])
                                if mm_value is not None:
                                    converted_item[f"{key}_mm"] = mm_value
                                    logger.info(f"  Converted {key}: {converted_item[key]} → {mm_value} mm")
                
                converted.append(converted_item)
            
            logger.info(f"✅ Converted dimensions in {len(converted)} items to MM")
            return converted
        
        except Exception as e:
            logger.error(f"❌ Error converting dimensions: {str(e)}")
            return bom_items
    
    @staticmethod
    def calculate_volume_from_dimensions(length_mm: float, width_mm: float, height_mm: float) -> float:
        """
        Calculate volume in mm³ from L×W×H
        
        Args:
            length_mm: Length in millimeters
            width_mm: Width in millimeters
            height_mm: Height in millimeters
        
        Returns: Volume in mm³
        """
        try:
            if length_mm is None or width_mm is None or height_mm is None:
                logger.warning("❌ Missing dimension for volume calculation")
                return None
            
            volume = length_mm * width_mm * height_mm
            logger.info(f"✅ Calculated volume: {length_mm}×{width_mm}×{height_mm} = {volume} mm³")
            return round(volume, 2)
        
        except Exception as e:
            logger.error(f"❌ Volume calculation error: {str(e)}")
            return None
    
    @staticmethod
    def add_dimensions_to_item(bom_item: Dict, length: float = None, width: float = None, height: float = None, 
                               length_unit: str = "mm", width_unit: str = "mm", height_unit: str = "mm") -> Dict:
        """
        Add or update dimensions for a single BOM item
        
        Args:
            bom_item: BOM item to update
            length, width, height: Dimension values
            length_unit, width_unit, height_unit: Units for each dimension
        
        Returns: Updated BOM item with dimensions and volume
        """
        try:
            updated_item = bom_item.copy()
            
            # Convert dimensions to MM
            if length is not None:
                length_mm = UnitConverter.to_mm(float(length), length_unit)
                updated_item["custom_length_mm"] = length_mm
            
            if width is not None:
                width_mm = UnitConverter.to_mm(float(width), width_unit)
                updated_item["custom_width_mm"] = width_mm
            
            if height is not None:
                height_mm = UnitConverter.to_mm(float(height), height_unit)
                updated_item["custom_height_mm"] = height_mm
            
            # Calculate volume if all dimensions present
            if "custom_length_mm" in updated_item and "custom_width_mm" in updated_item and "custom_height_mm" in updated_item:
                volume = BOMEnhancer.calculate_volume_from_dimensions(
                    updated_item["custom_length_mm"],
                    updated_item["custom_width_mm"],
                    updated_item["custom_height_mm"]
                )
                updated_item["custom_volume_mm3"] = volume
            
            logger.info(f"✅ Updated item with dimensions")
            return updated_item
        
        except Exception as e:
            logger.error(f"❌ Error adding dimensions: {str(e)}")
            return bom_item
    
    @staticmethod
    def create_bom_with_custom_columns(bom_items: List[Dict], custom_dimensions: Dict = None) -> List[Dict]:
        """
        Create enhanced BOM with custom columns and conversions
        
        Args:
            bom_items: Original BOM items
            custom_dimensions: {item_index: {length: 5, width: 10, height: 20, units: 'in'}, ...}
        
        Returns: Enhanced BOM with custom columns
        """
        try:
            # 1. Add custom column structure
            enhanced = BOMEnhancer.add_custom_columns(bom_items)
            
            # 2. Add user-provided dimensions
            if custom_dimensions:
                for idx, dims in custom_dimensions.items():
                    if idx < len(enhanced):
                        length_unit = dims.get("length_unit", "mm")
                        width_unit = dims.get("width_unit", "mm")
                        height_unit = dims.get("height_unit", "mm")
                        
                        enhanced[idx] = BOMEnhancer.add_dimensions_to_item(
                            enhanced[idx],
                            length=dims.get("length"),
                            width=dims.get("width"),
                            height=dims.get("height"),
                            length_unit=length_unit,
                            width_unit=width_unit,
                            height_unit=height_unit
                        )
            
            # 3. Try to convert any existing dimension fields
            enhanced = BOMEnhancer.convert_bom_dimensions(enhanced)
            
            logger.info(f"✅ Created enhanced BOM with custom columns")
            return enhanced
        
        except Exception as e:
            logger.error(f"❌ Error creating enhanced BOM: {str(e)}")
            return bom_items


# Example usage in routes:
"""
# In routes/bom.py or routes/properties.py

from services.bom_service import BOMEnhancer, UnitConverter

@router.post("/api/bom/add-dimensions")
async def add_dimensions_to_bom(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    bom_items = data.get("bom_items", [])
    custom_dimensions = data.get("custom_dimensions", {})  # {0: {length: 5, width: 10, ...}, ...}
    
    # Enhance BOM with custom columns
    enhanced_bom = BOMEnhancer.create_bom_with_custom_columns(bom_items, custom_dimensions)
    
    return {
        "status": "success",
        "data": enhanced_bom,
        "message": "Added custom columns and converted dimensions to MM"
    }

@router.post("/api/bom/convert-units")
async def convert_units(request: Request):
    data = await request.json()
    
    value_str = data.get("value")  # e.g., "10 in"
    
    mm_value = UnitConverter.convert_string_to_mm(value_str)
    
    return {
        "status": "success",
        "original": value_str,
        "mm": mm_value,
        "message": f"Converted to {mm_value} mm"
    }
"""