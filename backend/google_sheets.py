"""
Google Sheets Integration for Chef Voice AI Agent
Handles real-time syncing of recipes to Google Sheets
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# Configure logging
logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Sheet tab names
PLATE_RECIPES_TAB = "Plate Recipes"
BATCH_RECIPES_TAB = "Batch Recipes"
INGREDIENTS_TAB = "Ingredients"

# Column headers for each tab
PLATE_HEADERS = [
    "Recipe ID", "Recipe Name", "Chef ID", "Description", "Serves",
    "Category", "Cuisine", "Ingredients", "Plating Instructions", "Created At"
]

BATCH_HEADERS = [
    "Recipe ID", "Recipe Name", "Chef ID", "Description", "Yield Quantity",
    "Yield Unit", "Ingredients", "Instructions", "Storage Instructions", "Created At"
]

INGREDIENT_HEADERS = [
    "Ingredient ID", "Name", "Chef ID", "Unit", "Category", "Created At"
]


class GoogleSheetsClient:
    """Client for Google Sheets operations"""
    
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.initialized = False
        
    def init(self) -> bool:
        """Initialize the Google Sheets client"""
        try:
            # Get credentials file path or JSON content
            creds_env = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
            
            if not creds_env or not spreadsheet_id:
                logger.warning("Google Sheets not configured - missing environment variables")
                return False
            
            # Check if it's a JSON string or file path
            import json
            
            if creds_env.strip().startswith('{'):
                # It's JSON content - parse it directly
                try:
                    import tempfile
                    creds_info = json.loads(creds_env)
                    
                    # Create credentials from dict
                    credentials = Credentials.from_service_account_info(
                        creds_info,
                        scopes=SCOPES
                    )
                    logger.info("📋 Using JSON credentials from environment variable")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GOOGLE_SHEETS_CREDENTIALS as JSON: {e}")
                    return False
            else:
                # It's a file path - load from file
                backend_dir = Path(__file__).parent
                creds_path = backend_dir / creds_env
                
                if not creds_path.exists():
                    logger.warning(f"Google Sheets credentials file not found: {creds_path}")
                    return False
                
                # Authenticate from file
                credentials = Credentials.from_service_account_file(
                    str(creds_path),
                    scopes=SCOPES
                )
                logger.info(f"📄 Using credentials from file: {creds_path}")
            
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            # Setup sheet tabs
            self._setup_tabs()
            
            self.initialized = True
            logger.info("📊 Google Sheets initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            self.initialized = False
            return False
    
    def _setup_tabs(self):
        """Create sheet tabs with headers if they don't exist"""
        existing_tabs = [ws.title for ws in self.spreadsheet.worksheets()]
        
        # Setup Plate Recipes tab
        if PLATE_RECIPES_TAB not in existing_tabs:
            ws = self.spreadsheet.add_worksheet(title=PLATE_RECIPES_TAB, rows=1000, cols=len(PLATE_HEADERS))
            ws.update('A1', [PLATE_HEADERS])
            ws.format('A1:J1', {'textFormat': {'bold': True}})
            logger.info(f"Created '{PLATE_RECIPES_TAB}' tab")
        
        # Setup Batch Recipes tab
        if BATCH_RECIPES_TAB not in existing_tabs:
            ws = self.spreadsheet.add_worksheet(title=BATCH_RECIPES_TAB, rows=1000, cols=len(BATCH_HEADERS))
            ws.update('A1', [BATCH_HEADERS])
            ws.format('A1:J1', {'textFormat': {'bold': True}})
            logger.info(f"Created '{BATCH_RECIPES_TAB}' tab")
        
        # Setup Ingredients tab
        if INGREDIENTS_TAB not in existing_tabs:
            ws = self.spreadsheet.add_worksheet(title=INGREDIENTS_TAB, rows=1000, cols=len(INGREDIENT_HEADERS))
            ws.update('A1', [INGREDIENT_HEADERS])
            ws.format('A1:F1', {'textFormat': {'bold': True}})
            logger.info(f"Created '{INGREDIENTS_TAB}' tab")
    
    def add_plate_recipe(self, recipe: Dict[str, Any], ingredients: List[Dict[str, Any]] = None) -> bool:
        """Add a plate recipe to the sheets"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized, skipping sync")
            return False
        
        try:
            ws = self.spreadsheet.worksheet(PLATE_RECIPES_TAB)
            
            # Format ingredients as comma-separated string
            ing_str = ""
            if ingredients:
                ing_names = [f"{ing.get('name', '')} ({ing.get('quantity', '')} {ing.get('unit', '')})" 
                            for ing in ingredients]
                ing_str = ", ".join(ing_names)
            
            # Prepare row data
            row = [
                str(recipe.get('id', '')),
                recipe.get('name', ''),
                recipe.get('chef_id', ''),
                recipe.get('description', ''),
                str(recipe.get('serves', '')),
                recipe.get('category', ''),
                recipe.get('cuisine', ''),
                ing_str,
                recipe.get('plating_instructions', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            ws.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"📊 Synced plate recipe to Sheets: {recipe.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add plate recipe to Sheets: {e}")
            return False
    
    def add_batch_recipe(self, recipe: Dict[str, Any], ingredients: List[Dict[str, Any]] = None) -> bool:
        """Add a batch recipe to the sheets"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized, skipping sync")
            return False
        
        try:
            ws = self.spreadsheet.worksheet(BATCH_RECIPES_TAB)
            
            # Format ingredients as comma-separated string
            ing_str = ""
            if ingredients:
                ing_names = [f"{ing.get('name', '')} ({ing.get('quantity', '')} {ing.get('unit', '')})" 
                            for ing in ingredients]
                ing_str = ", ".join(ing_names)
            
            # Prepare row data
            row = [
                str(recipe.get('id', '')),
                recipe.get('name', ''),
                recipe.get('chef_id', ''),
                recipe.get('description', ''),
                str(recipe.get('yield_quantity', '')),
                recipe.get('yield_unit', ''),
                ing_str,
                recipe.get('instructions', ''),
                recipe.get('storage_instructions', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            ws.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"📊 Synced batch recipe to Sheets: {recipe.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add batch recipe to Sheets: {e}")
            return False
    
    def add_ingredient(self, ingredient: Dict[str, Any]) -> bool:
        """Add an ingredient to the sheets"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized, skipping sync")
            return False
        
        try:
            ws = self.spreadsheet.worksheet(INGREDIENTS_TAB)
            
            row = [
                str(ingredient.get('id', '')),
                ingredient.get('name', ''),
                ingredient.get('chef_id', ''),
                ingredient.get('unit', ''),
                ingredient.get('category', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            ws.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"📊 Synced ingredient to Sheets: {ingredient.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add ingredient to Sheets: {e}")
            return False
    
    def update_recipe(self, recipe_id: str, recipe_type: str, updates: Dict[str, Any]) -> bool:
        """Update a recipe row in the sheets by finding it via recipe_id"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized, skipping sync")
            return False
        
        try:
            # Choose the right tab
            if recipe_type == "plate":
                ws = self.spreadsheet.worksheet(PLATE_RECIPES_TAB)
                name_col = 2  # Column B is Recipe Name
            else:
                ws = self.spreadsheet.worksheet(BATCH_RECIPES_TAB)
                name_col = 2
            
            # Find the row with this recipe_id (column A)
            cell = ws.find(str(recipe_id), in_column=1)
            
            if not cell:
                logger.warning(f"Recipe {recipe_id} not found in Sheets for update")
                return False
            
            row_num = cell.row
            
            # Update specific cells based on what changed
            if 'name' in updates and updates['name']:
                ws.update_cell(row_num, name_col, updates['name'])
            if 'description' in updates and updates['description']:
                ws.update_cell(row_num, 4, updates['description'])  # Column D
            if 'serves' in updates and updates['serves']:
                ws.update_cell(row_num, 5, str(updates['serves']))  # Column E
            if 'cuisine' in updates and updates['cuisine']:
                ws.update_cell(row_num, 7, updates['cuisine'])  # Column G
            if 'category' in updates and updates['category']:
                ws.update_cell(row_num, 6, updates['category'])  # Column F
            
            logger.info(f"📊 Updated recipe in Sheets: {recipe_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update recipe in Sheets: {e}")
            return False
    
    def delete_recipe(self, recipe_id: str, recipe_type: str) -> bool:
        """Delete a recipe row from the sheets"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized, skipping sync")
            return False
        
        try:
            # Choose the right tab
            if recipe_type == "plate":
                ws = self.spreadsheet.worksheet(PLATE_RECIPES_TAB)
            else:
                ws = self.spreadsheet.worksheet(BATCH_RECIPES_TAB)
            
            # Find the row with this recipe_id (column A)
            cell = ws.find(str(recipe_id), in_column=1)
            
            if not cell:
                logger.warning(f"Recipe {recipe_id} not found in Sheets for deletion")
                return False
            
            # Delete the entire row
            ws.delete_rows(cell.row)
            
            logger.info(f"📊 Deleted recipe from Sheets: {recipe_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete recipe from Sheets: {e}")
            return False
    
    def sync_all_from_database(self, db_module) -> Dict[str, int]:
        """Sync all existing recipes from database to sheets"""
        if not self.initialized:
            logger.warning("Google Sheets not initialized")
            return {"error": "Not initialized"}
        
        try:
            stats = {"plate_recipes": 0, "batch_recipes": 0, "ingredients": 0}
            
            # Clear existing data (keep headers)
            for tab_name in [PLATE_RECIPES_TAB, BATCH_RECIPES_TAB, INGREDIENTS_TAB]:
                try:
                    ws = self.spreadsheet.worksheet(tab_name)
                    # Get all values to count rows
                    all_values = ws.get_all_values()
                    if len(all_values) > 1:
                        # Clear all except header row
                        ws.delete_rows(2, len(all_values))
                except:
                    pass
            
            # Get connection from database module
            from database import get_connection, return_connection
            from psycopg2.extras import RealDictCursor
            
            conn = get_connection()
            if not conn:
                return {"error": "Database not connected"}
            
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                
                # Sync plate recipes
                cur.execute("""
                    SELECT pr.id, pr.chef_id, pr.name, pr.description, pr.serves,
                           pr.category, pr.cuisine, pr.plating_instructions, pr.created_at
                    FROM plate_recipes pr
                    ORDER BY pr.created_at DESC
                """)
                plate_recipes = cur.fetchall()
                
                for recipe in plate_recipes:
                    # Get ingredients for this recipe
                    cur.execute("""
                        SELECT i.name, pi.quantity, pi.unit
                        FROM plate_ingredients pi
                        JOIN ingredients i ON i.id = pi.ingredient_id
                        WHERE pi.plate_recipe_id = %s
                    """, (recipe['id'],))
                    ingredients = cur.fetchall()
                    
                    recipe_dict = dict(recipe)
                    ingredients_list = [dict(ing) for ing in ingredients]
                    
                    if self.add_plate_recipe(recipe_dict, ingredients_list):
                        stats["plate_recipes"] += 1
                
                # Sync batch recipes
                cur.execute("""
                    SELECT br.id, br.chef_id, br.name, br.description,
                           br.yield_quantity, br.yield_unit, br.instructions,
                           br.storage_instructions, br.created_at
                    FROM batch_recipes br
                    ORDER BY br.created_at DESC
                """)
                batch_recipes = cur.fetchall()
                
                for recipe in batch_recipes:
                    # Get ingredients for this recipe
                    cur.execute("""
                        SELECT i.name, bi.quantity, bi.unit
                        FROM batch_ingredients bi
                        JOIN ingredients i ON i.id = bi.ingredient_id
                        WHERE bi.batch_recipe_id = %s
                    """, (recipe['id'],))
                    ingredients = cur.fetchall()
                    
                    recipe_dict = dict(recipe)
                    ingredients_list = [dict(ing) for ing in ingredients]
                    
                    if self.add_batch_recipe(recipe_dict, ingredients_list):
                        stats["batch_recipes"] += 1
                
                # Sync ingredients
                cur.execute("""
                    SELECT id, name, chef_id, unit, category, created_at
                    FROM ingredients
                    ORDER BY created_at DESC
                """)
                ingredients = cur.fetchall()
                
                for ing in ingredients:
                    if self.add_ingredient(dict(ing)):
                        stats["ingredients"] += 1
                
                cur.close()
            finally:
                return_connection(conn)
            
            logger.info(f"✅ Full sync complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync from database: {e}")
            return {"error": str(e)}


# Global client instance
sheets_client = GoogleSheetsClient()


def init_sheets() -> bool:
    """Initialize the global sheets client"""
    return sheets_client.init()


def add_plate_recipe(recipe: Dict[str, Any], ingredients: List[Dict[str, Any]] = None) -> bool:
    """Add a plate recipe to Google Sheets"""
    return sheets_client.add_plate_recipe(recipe, ingredients)


def add_batch_recipe(recipe: Dict[str, Any], ingredients: List[Dict[str, Any]] = None) -> bool:
    """Add a batch recipe to Google Sheets"""
    return sheets_client.add_batch_recipe(recipe, ingredients)


def add_ingredient(ingredient: Dict[str, Any]) -> bool:
    """Add an ingredient to Google Sheets"""
    return sheets_client.add_ingredient(ingredient)


def sync_all_from_database(db_module=None) -> Dict[str, int]:
    """Sync all recipes from database to Google Sheets"""
    return sheets_client.sync_all_from_database(db_module)


def update_recipe(recipe_id: str, recipe_type: str, updates: Dict[str, Any]) -> bool:
    """Update a recipe in Google Sheets"""
    return sheets_client.update_recipe(recipe_id, recipe_type, updates)


def delete_recipe(recipe_id: str, recipe_type: str) -> bool:
    """Delete a recipe from Google Sheets"""
    return sheets_client.delete_recipe(recipe_id, recipe_type)


def test_connection():
    """Test the Google Sheets connection"""
    print("Testing Google Sheets connection...")
    if init_sheets():
        print("✅ Successfully connected to Google Sheets!")
        print(f"   Spreadsheet: {sheets_client.spreadsheet.title}")
        print(f"   Tabs: {[ws.title for ws in sheets_client.spreadsheet.worksheets()]}")
    else:
        print("❌ Failed to connect to Google Sheets")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_connection()
