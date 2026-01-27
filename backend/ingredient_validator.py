"""
Ingredient Validation Module
Validates ingredient quantities and units based on culinary standards
Provides smart suggestions and normalization for recipe ingredients
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Standard culinary units by category (based on professional cooking standards)
STANDARD_UNITS = {
    # Mass (Weight) - Metric
    'mass_metric': {
        'mg': 'milligrams',
        'milligram': 'milligrams',
        'milligrams': 'milligrams',
        'g': 'grams',
        'gram': 'grams',
        'grams': 'grams',
        'kg': 'kilograms',
        'kilogram': 'kilograms',
        'kilograms': 'kilograms',
    },
    
    # Mass (Weight) - Imperial
    'mass_imperial': {
        'oz': 'ounces',
        'ounce': 'ounces',
        'ounces': 'ounces',
        'lb': 'pounds',
        'lbs': 'pounds',
        'pound': 'pounds',
        'pounds': 'pounds',
    },
    
    # Volume - Metric
    'volume_metric': {
        'ml': 'milliliters',
        'milliliter': 'milliliters',
        'milliliters': 'milliliters',
        'l': 'liters',
        'liter': 'liters',
        'liters': 'liters',
    },
    
    # Volume - Imperial/US
    'volume_imperial': {
        'tsp': 'teaspoon',
        'teaspoon': 'teaspoon',
        'teaspoons': 'teaspoon',
        'tbsp': 'tablespoon',
        'tablespoon': 'tablespoon',
        'tablespoons': 'tablespoon',
        'cup': 'cup',
        'cups': 'cup',
        'pint': 'pint',
        'pints': 'pint',
        'quart': 'quart',
        'quarts': 'quart',
        'gallon': 'gallon',
        'gallons': 'gallon',
        'fl oz': 'fluid ounce',
        'fluid ounce': 'fluid ounce',
        'fluid ounces': 'fluid ounce',
    },
    
    # Count-based (Whole items)
    'count': {
        'piece': 'piece',
        'pieces': 'piece',
        'whole': 'whole',
        'clove': 'clove',
        'cloves': 'clove',
        'slice': 'slice',
        'slices': 'slice',
        'stick': 'stick',
        'sticks': 'stick',
        'leaf': 'leaf',
        'leaves': 'leaf',
        'sprig': 'sprig',
        'sprigs': 'sprig',
    },
    
    # Approximate/Subjective (requires follow-up or contextual understanding)
    'approximate': {
        'pinch': 'pinch',
        'dash': 'dash',
        'handful': 'handful',
        'bunch': 'bunch',
        'small': 'small',
        'medium': 'medium',
        'large': 'large',
        'to taste': 'to taste',
    }
}

# Common ingredient to unit mappings (for suggestions)
INGREDIENT_UNIT_SUGGESTIONS = {
    # Proteins (typically weight)
    'chicken': ['grams', 'kilograms', 'pounds'],
    'beef': ['grams', 'kilograms', 'pounds'],
    'pork': ['grams', 'kilograms', 'pounds'],
    'fish': ['grams', 'kilograms', 'pounds'],
    'paneer': ['grams', 'kilograms'],
    'tofu': ['grams', 'kilograms'],
    
    # Vegetables (weight or count)
    'onion': ['grams', 'piece', 'kilograms'],
    'onions': ['grams', 'piece', 'kilograms'],
    'tomato': ['grams', 'piece', 'kilograms'],
    'tomatoes': ['grams', 'piece', 'kilograms'],
    'potato': ['grams', 'piece', 'kilograms'],
    'potatoes': ['grams', 'piece', 'kilograms'],
    'garlic': ['clove', 'grams'],
    
    # Spices (typically small volumes or weight)
    'salt': ['teaspoon', 'tablespoon', 'grams', 'pinch'],
    'pepper': ['teaspoon', 'tablespoon', 'grams', 'pinch'],
    'cumin': ['teaspoon', 'tablespoon', 'grams'],
    'coriander': ['teaspoon', 'tablespoon', 'grams'],
    'turmeric': ['teaspoon', 'tablespoon', 'grams'],
    
    # Liquids (volume)
    'water': ['milliliters', 'liters', 'cup'],
    'milk': ['milliliters', 'liters', 'cup'],
    'cream': ['milliliters', 'liters', 'cup'],
    'oil': ['milliliters', 'liters', 'tablespoon'],
    'stock': ['milliliters', 'liters', 'cup'],
    
    # Grains/Dry goods (weight)
    'rice': ['grams', 'kilograms', 'cup'],
    'flour': ['grams', 'kilograms', 'cup'],
    'sugar': ['grams', 'kilograms', 'cup', 'tablespoon'],
}


def normalize_unit(unit: str) -> str:
    """
    Normalize a unit to its standard form.
    
    Args:
        unit: Raw unit string (e.g., "tsp", "g", "cups")
        
    Returns:
        Normalized unit string (e.g., "teaspoon", "grams", "cup")
    """
    if not unit:
        return ""
    
    # Convert to lowercase and strip whitespace
    unit = unit.lower().strip()
    
    # Search all categories for the unit
    for category, units in STANDARD_UNITS.items():
        if unit in units:
            return units[unit]
    
    # If not found, return original (might be a custom/rare unit)
    return unit


def is_valid_unit(unit: str) -> bool:
    """
    Check if a unit is in the standard units list.
    
    Args:
        unit: Unit string to validate
        
    Returns:
        True if unit is valid, False otherwise
    """
    if not unit:
        return True  # Empty unit is acceptable (e.g., "5 eggs")
    
    unit_lower = unit.lower().strip()
    
    for category, units in STANDARD_UNITS.items():
        if unit_lower in units:
            return True
    
    return False


def is_ambiguous(quantity: str, unit: str, ingredient_name: str = "") -> bool:
    """
    Determine if an ingredient quantity/unit combination is ambiguous.
    
    Examples of ambiguous:
    - "10 onions" (should be grams or pieces?)
    - "2 chicken" (should be grams, kilograms, or pieces?)
    - "5 garlic" (should be cloves, grams, or pieces?)
    
    Args:
        quantity: Quantity string
        unit: Unit string
        ingredient_name: Name of the ingredient
        
    Returns:
        True if ambiguous and needs follow-up, False otherwise
    """
    # If unit is empty and quantity is numeric, it's potentially ambiguous
    if not unit and quantity:
        try:
            qty = float(quantity)
            # Count-based ingredients without unit are acceptable (e.g., "5 eggs", "2 cloves")
            # But for common ingredients that could be measured, ask for clarification
            common_weighted_ingredients = [
                'onion', 'onions', 'tomato', 'tomatoes', 'potato', 'potatoes',
                'chicken', 'beef', 'pork', 'fish', 'paneer'
            ]
            
            if any(ing in ingredient_name.lower() for ing in common_weighted_ingredients):
                return True
        except ValueError:
            pass
    
    # Unit is "pieces" or "whole" but could be weight for precision
    if unit.lower() in ['piece', 'pieces', 'whole'] and ingredient_name:
        return False  # Actually, pieces is acceptable for count items
    
    return False


def suggest_unit_for_ingredient(ingredient_name: str) -> List[str]:
    """
    Suggest appropriate units for a given ingredient.
    
    Args:
        ingredient_name: Name of the ingredient
        
    Returns:
        List of suggested units
    """
    name_lower = ingredient_name.lower().strip()
    
    # Check direct matches
    if name_lower in INGREDIENT_UNIT_SUGGESTIONS:
        return INGREDIENT_UNIT_SUGGESTIONS[name_lower]
    
    # Check partial matches (e.g., "chicken breast" contains "chicken")
    for ing, units in INGREDIENT_UNIT_SUGGESTIONS.items():
        if ing in name_lower or name_lower in ing:
            return units
    
    # Default suggestions
    return ['grams', 'piece', 'tablespoon']


def validate_ingredient(name: str, quantity: str, unit: str) -> Dict:
    """
    Validate an ingredient's quantity and unit combination.
    
    Args:
        name: Ingredient name
        quantity: Quantity value (numeric or text like "1/2")
        unit: Unit of measurement
        
    Returns:
        Dictionary with validation results:
        {
            'valid': bool,
            'normalized_unit': str,
            'message': str (if invalid),
            'suggestion': str (optional),
            'is_ambiguous': bool
        }
    """
    result = {
        'valid': True,
        'normalized_unit': unit,
        'message': '',
        'suggestion': '',
        'is_ambiguous': False
    }
    
    # Normalize the unit
    if unit:
        normalized = normalize_unit(unit)
        if normalized != unit:
            result['normalized_unit'] = normalized
            logger.info(f"Normalized unit '{unit}' to '{normalized}'")
    
    # Check if unit is valid
    if unit and not is_valid_unit(unit):
        result['valid'] = False
        suggestions = suggest_unit_for_ingredient(name)
        result['message'] = f"I'm not sure about the unit '{unit}'. Did you mean {', '.join(suggestions[:2])}?"
        result['suggestion'] = suggestions[0]
        return result
    
    # Check if ambiguous (no unit for weighted ingredients)
    if is_ambiguous(quantity, unit, name):
        result['is_ambiguous'] = True
        suggestions = suggest_unit_for_ingredient(name)
        result['suggestion'] = f"{quantity} {suggestions[0]} {name}"
        result['normalized_unit'] = 'piece'  # Default to count-based if no unit
        # Still valid, but we'll let the AI suggest improvement
    
    return result


def parse_quantity(quantity_str: str) -> Optional[float]:
    """
    Parse a quantity string to a float.
    Handles fractions like "1/2", "1 1/2", decimals, and whole numbers.
    
    Args:
        quantity_str: String representation of quantity
        
    Returns:
        Float value or None if cannot parse
    """
    try:
        # Handle simple numbers
        if quantity_str.replace('.', '').replace('-', '').isdigit():
            return float(quantity_str)
        
        # Handle fractions like "1/2"
        if '/' in quantity_str:
            parts = quantity_str.split()
            if len(parts) == 1:
                # Simple fraction like "1/2"
                num, denom = parts[0].split('/')
                return float(num) / float(denom)
            elif len(parts) == 2:
                # Mixed number like "1 1/2"
                whole = float(parts[0])
                num, denom = parts[1].split('/')
                fraction = float(num) / float(denom)
                return whole + fraction
        
        # Direct float conversion
        return float(quantity_str)
    
    except (ValueError, ZeroDivisionError):
        logger.warning(f"Could not parse quantity: {quantity_str}")
        return None
