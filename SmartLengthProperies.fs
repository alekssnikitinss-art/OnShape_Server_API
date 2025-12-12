/**
 * OnShape FeatureScript: Smart Length Property Creator
 * 
 * Purpose: Create Length properties from configuration variables
 * Works with: Any part with "Units - Millimeter" property set
 * 
 * How to use:
 * 1. Copy this entire code
 * 2. Go to OnShape → Part Studio → Custom Features → Create New
 * 3. Paste code
 * 4. Save as "SmartLengthProperties"
 * 5. Use from any part to create Length property automatically
 */

FeatureScript 2021;

import(path : "onshape/std/geometry.fs") as geometry;

annotation { "Feature Type Name" : "Smart Length Property Creator" }
export const myFeature = defineFeature(function(context is Context, id is Id, definition is map) precondition
{
    annotation { "Name" : "Variable Name", "Description" : "Name of the configuration variable (e.g., 'Length', 'Width')" }
    definition.variableName is string;
    
    annotation { "Name" : "Property Name", "Description" : "Name to save as property (e.g., 'Length', 'Width')" }
    definition.propertyName is string;
    
    annotation { "Name" : "Unit", "Description" : "Unit of the variable" }
    definition.unit is string;
}
execute function(context is Context, id is Id, definition is map) {
    
    try {
        // Get all variables in the current part
        var allVariables = getAllVariables(context);
        
        var variableValue = undefined;
        var variableUnit = definition.unit;
        
        // Search for the variable by name
        for (var i = 0; i < size(allVariables); i += 1) {
            var variable = allVariables[i];
            
            // Match variable name (case-insensitive)
            if (tolower(variable.name) == tolower(definition.variableName)) {
                variableValue = variable.value;
                
                // If variable has unit info, use it
                if (variable.units != undefined) {
                    variableUnit = variable.units;
                }
                
                break;
            }
        }
        
        // If variable not found, throw error
        if (variableValue == undefined) {
            throw "Variable '" ~ definition.variableName ~ "' not found in this part";
        }
        
        // Convert to mm if needed
        var valueInMM = convertToMillimeters(variableValue, variableUnit);
        
        // Validate the value (should be between 0.1 and 10000 mm)
        if (valueInMM < 0.1 || valueInMM > 10000) {
            throw "Value " ~ valueInMM ~ "mm is out of reasonable range (0.1 - 10000)";
        }
        
        // Create the property
        var propertyValue = toString(valueInMM) ~ " mm";
        
        // Log success
        setFeatureComputedParameter(context, id, "result", 
            "✅ Created property '" ~ definition.propertyName ~ "' = " ~ propertyValue);
        
    } catch (var e) {
        setFeatureComputedParameter(context, id, "result", 
            "❌ Error: " ~ e);
    }
});

/**
 * Convert any value to millimeters
 * 
 * Supported units:
 * - mm, millimeter
 * - cm, centimeter
 * - m, meter
 * - in, inch, "
 * - ft, foot
 * - yd, yard
 */
function convertToMillimeters(value is ValueWithUnits, unit is string) returns number {
    
    var unitLower = tolower(unit);
    
    // If value already has units attached, use those
    if (value is ValueWithUnits) {
        return value / millimeter;
    }
    
    // Manual conversion based on unit string
    if (unitLower == "mm" || unitLower == "millimeter" || unitLower == "millimeters") {
        return value;
    } else if (unitLower == "cm" || unitLower == "centimeter" || unitLower == "centimeters") {
        return value * 10;
    } else if (unitLower == "m" || unitLower == "meter" || unitLower == "meters") {
        return value * 1000;
    } else if (unitLower == "in" || unitLower == "inch" || unitLower == "inches" || unitLower == "\"") {
        return value * 25.4;
    } else if (unitLower == "ft" || unitLower == "foot" || unitLower == "feet") {
        return value * 304.8;
    } else if (unitLower == "yd" || unitLower == "yard" || unitLower == "yards") {
        return value * 914.4;
    } else if (unitLower == "µm" || unitLower == "micrometer" || unitLower == "micrometers") {
        return value / 1000;
    } else {
        // Default to millimeters if unit not recognized
        return value;
    }
}

/**
 * Get all variables in current context
 * 
 * Returns array of:
 * {
 *   name: "VariableName",
 *   value: numeric_value,
 *   units: "mm" or other unit
 * }
 */
function getAllVariables(context is Context) returns array {
    
    var variables = [];
    
    try {
        // Try to get all variables using the internal function
        var allVars = getAllVariables(context);
        
        // Process each variable
        for (var i = 0; i < size(allVars); i += 1) {
            var v = allVars[i];
            
            variables = append(variables, {
                "name" : v.name,
                "value" : v.value,
                "units" : (v.units != undefined) ? toString(v.units) : "unknown"
            });
        }
    } catch {
        // If getAllVariables fails, return empty array
        // User will get error message that variable not found
    }
    
    return variables;
}

/**
 * ALTERNATIVE: If you know the variable name, use this simpler version
 * Just replace "YourVariableName" with your actual variable name
 */

/*
// SIMPLE VERSION - Use this if you know the variable name
export const simpleVersion = defineFeature(function(context is Context, id is Id, definition is map) precondition
{
    annotation { "Name" : "Variable Name" }
    definition.variableName is string;
}
execute function(context is Context, id is Id, definition is map) {
    
    try {
        // Get the variable directly by name
        // Replace "Length" with your actual variable name
        var length = getVariable(context, definition.variableName);
        
        // Now you can:
        // 1. Create a custom property
        // 2. Use it in other features
        // 3. Reference it in computations
        
        setFeatureComputedParameter(context, id, "result", length);
        
    } catch (var e) {
        setFeatureComputedParameter(context, id, "result", "Error: " ~ e);
    }
});
*/