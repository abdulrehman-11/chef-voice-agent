"""
Gemini Function Calling Tools
Define function schemas for structured recipe operations
"""
from typing import Dict, List, Any

# Tool: Classify recipe type
CLASSIFY_RECIPE_TYPE_TOOL = {
    "name": "classify_recipe_type",
    "description": "Classify whether the chef is describing a Batch Recipe (large-scale component) or Plate Recipe (final plated dish)",
    "parameters": {
        "type": "object",
        "properties": {
            "recipe_type": {
                "type": "string",
                "enum": ["batch", "plate"],
                "description": "Type of recipe: 'batch' for large-scale components/bases, 'plate' for final assembled dishes"
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Confidence level in classification"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this classification was chosen"
            }
        },
        "required": ["recipe_type", "confidence"]
    }
}

# Tool: Save batch recipe
SAVE_BATCH_RECIPE_TOOL = {
    "name": "save_batch_recipe",
    "description": "Save a batch recipe (large-scale component like sauce, stock, dough) to the database",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the batch recipe (e.g., 'Tomato Concasse', 'Chicken Stock')"
            },
            "description": {
                "type": "string",
                "description": "Brief description of the batch recipe"
            },
            "yield_quantity": {
                "type": "number",
                "description": "Total yield quantity as a number"
            },
            "yield_unit": {
                "type": "string",
                "description": "Unit of yield (kg, liters, grams, etc.)"
            },
            "prep_time_minutes": {
                "type": "integer",
                "description": "Preparation time in minutes"
            },
            "cook_time_minutes": {
                "type": "integer",
                "description": "Cooking time in minutes"
            },
            "temperature": {
                "type": "number",
                "description": "Cooking temperature"
            },
            "temperature_unit": {
                "type": "string",
                "enum": ["C", "F"],
                "description": "Temperature unit (Celsius or Fahrenheit)"
            },
            "equipment": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of equipment needed"
            },
            "instructions": {
                "type": "string",
                "description": "Step-by-step cooking instructions"
            },
            "ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string"},
                        "preparation_notes": {"type": "string"},
                        "is_optional": {"type": "boolean"}
                    },
                    "required": ["name", "quantity", "unit"]
                },
                "description": "List of ingredients with quantities"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes or tips"
            }
        },
        "required": ["name", "yield_quantity", "yield_unit", "ingredients"]
    }
}

# Tool: Save plate recipe
SAVE_PLATE_RECIPE_TOOL = {
    "name": "save_plate_recipe",
    "description": "Save a plate recipe (final assembled dish) to the database",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the dish (e.g., 'Seared Scallops with Pea Puree')"
            },
            "description": {
                "type": "string",
                "description": "Brief description of the plate"
            },
            "serves": {
                "type": "integer",
                "description": "Number of servings/portions"
            },
            "category": {
                "type": "string",
                "description": "Category (appetizer, main, dessert, etc.)"
            },
            "cuisine": {
                "type": "string",
                "description": "Cuisine type (French, Italian, Asian, etc.)"
            },
            "plating_instructions": {
                "type": "string",
                "description": "How to plate and present the dish"
            },
            "garnish": {
                "type": "string",
                "description": "Garnish details"
            },
            "presentation_notes": {
                "type": "string",
                "description": "Presentation and visual notes"
            },
            "prep_time_minutes": {
                "type": "integer",
                "description": "Preparation time in minutes"
            },
            "cook_time_minutes": {
                "type": "integer",
                "description": "Cooking time in minutes"
            },
            "difficulty": {
                "type": "string",
                "enum": ["easy", "medium", "hard"],
                "description": "Difficulty level"
            },
            "batch_recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string"},
                        "preparation_notes": {"type": "string"}
                    },
                    "required": ["name"]
                },
                "description": "Batch recipes used in this dish"
            },
            "ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string"},
                        "preparation_notes": {"type": "string"},
                        "is_garnish": {"type": "boolean"},
                        "is_optional": {"type": "boolean"}
                    },
                    "required": ["name"]
                },
                "description": "Direct ingredients (not from batch recipes)"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes"
            }
        },
        "required": ["name", "serves"]
    }
}

# Tool: Search recipes
SEARCH_RECIPES_TOOL = {
    "name": "search_recipes",
    "description": "Search for recipes by name or keyword in the chef's recipe library",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Recipe name or search keyword"
            },
            "recipe_type": {
                "type": "string",
                "enum": ["batch", "plate", "both"],
                "description": "Type of recipe to search for"
            }
        },
        "required": ["query"]
    }
}

# Tool: Get recipe details
GET_RECIPE_DETAILS_TOOL = {
    "name": "get_recipe_details",
    "description": "Retrieve full details of a specific recipe",
    "parameters": {
        "type": "object",
        "properties": {
            "recipe_name": {
                "type": "string",
                "description": "Exact or partial name of the recipe"
            },
            "recipe_type": {
                "type": "string",
                "enum": ["batch", "plate"],
                "description": "Type of recipe if known"
            }
        },
        "required": ["recipe_name"]
    }
}

# Tool: Analyze recipe completeness
ANALYZE_COMPLETENESS_TOOL = {
    "name": "analyze_completeness",
    "description": "Check if a recipe has all required information and identify missing fields",
    "parameters": {
        "type": "object",
        "properties": {
            "recipe_data": {
                "type": "object",
                "description": "Current recipe data as an object"
            },
            "recipe_type": {
                "type": "string",
                "enum": ["batch", "plate"],
                "description": "Type of recipe"
            }
        },
        "required": ["recipe_data", "recipe_type"]
    }
}

# Tool: List all recipes
LIST_RECIPES_TOOL = {
    "name": "list_recipes",
    "description": "List all recipes saved by the chef",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of recipes to return",
                "default": 50
            }
        }
    }
}

# All tools array for Gemini
ALL_TOOLS = [
    CLASSIFY_RECIPE_TYPE_TOOL,
    SAVE_BATCH_RECIPE_TOOL,
    SAVE_PLATE_RECIPE_TOOL,
    SEARCH_RECIPES_TOOL,
    GET_RECIPE_DETAILS_TOOL,
    ANALYZE_COMPLETENESS_TOOL,
    LIST_RECIPES_TOOL
]

def get_tool_by_name(name: str) -> Dict[str, Any]:
    """Get tool definition by name"""
    for tool in ALL_TOOLS:
        if tool["name"] == name:
            return tool
    return None
