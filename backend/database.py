"""
Database Operations Module
Handles all database interactions for recipes, ingredients, and conversations
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import json
import logging

# Import Google Sheets module for real-time sync
try:
    import google_sheets
    SHEETS_ENABLED = True
except ImportError:
    SHEETS_ENABLED = False

load_dotenv()

logger = logging.getLogger(__name__)

# Connection pool
pool = None

def init_db():
    """Initialize database connection pool"""
    global pool
    if pool is None:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment")
        
        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url
        )
        print("✅ Database connection pool initialized")

def get_connection():
    """Get a connection from the pool with retry for stale connections"""
    global pool
    if pool is None:
        init_db()
    
    conn = pool.getconn()
    
    # Test if connection is alive
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        logger.warning(f"⚠️ Stale connection detected, refreshing: {e}")
        # Close bad connection and get a new one
        try:
            pool.putconn(conn, close=True)
        except:
            pass
        
        # Reinitialize pool if needed
        try:
            conn = pool.getconn()
            return conn
        except:
            # Pool might be corrupted, reinitialize
            logger.info("🔄 Reinitializing connection pool...")
            pool = None
            init_db()
            return pool.getconn()

def return_connection(conn):
    """Return connection to the pool"""
    if pool and conn:
        try:
            pool.putconn(conn)
        except:
            pass

def close_connection(conn):
    """Close a bad connection instead of returning to pool"""
    if pool and conn:
        try:
            pool.putconn(conn, close=True)
        except:
            pass


# ==================== HELPER FUNCTIONS ====================

def _get_unique_recipe_name(cur, chef_id: str, name: str, recipe_type: str) -> str:
    """
    Check if recipe name exists and return unique version if needed.
    If 'Tomato Sauce' exists, returns 'Tomato Sauce 2', then 'Tomato Sauce 3', etc.
    
    Args:
        cur: Database cursor
        chef_id: Chef ID
        name: Desired recipe name
        recipe_type: 'batch' or 'plate'
    
    Returns:
        Unique name (original or versioned)
    """
    table = 'batch_recipes' if recipe_type == 'batch' else 'plate_recipes'
    base_name = name.strip()
    
    # Check if base name exists
    cur.execute(f"""
        SELECT name FROM {table}
        WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
    """, (chef_id, base_name))
    
    if not cur.fetchone():
        return base_name  # Name is unique, use it as-is
    
    # Name exists, find next available version number
    logger.info(f"Recipe '{base_name}' already exists, finding unique version...")
    
    version = 2
    while version < 100:  # Safety limit
        versioned_name = f"{base_name} {version}"
        cur.execute(f"""
            SELECT name FROM {table}
            WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
        """, (chef_id, versioned_name))
        
        if not cur.fetchone():
            logger.info(f"✅ Using versioned name: '{versioned_name}'")
            return versioned_name
        
        version += 1
    
    # If we somehow hit 100 versions, add timestamp
    import time
    timestamp = int(time.time())
    return f"{base_name} {timestamp}"


def check_recipe_exists(chef_id: str, name: str, recipe_type: str) -> Optional[Dict]:
    """
    Check if a recipe with this name already exists.
    Used for interactive duplicate detection.
    
    Args:
        chef_id: Chef ID
        name: Recipe name to check
        recipe_type: 'batch' or 'plate'
    
    Returns:
        Recipe details dict if found, None otherwise
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        table = 'batch_recipes' if recipe_type == 'batch' else 'plate_recipes'
        
        cur.execute(f"""
            SELECT id, name, description, created_at
            FROM {table}
            WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
            LIMIT 1
        """, (chef_id, name.strip()))
        
        result = cur.fetchone()
        if result:
            return dict(result)
        return None
        
    finally:
        cur.close()
        return_connection(conn)


# ==================== VERSIONING HELPER FUNCTIONS ====================

def _calculate_next_version(current_version: float, change_type: str = "minor") -> float:
    """
    Calculate the next version number based on current version and change type.
    
    Semantic versioning logic:
    - 1.0 + minor → 1.1
    - 1.9 + minor → 1.10
    - 1.5 + major → 2.0
    
    Args:
        current_version: Current version number (e.g., 1.0, 1.5)
        change_type: Type of change ("minor" or "major")
    
    Returns:
        Next version number as float
    """
    if change_type == "major":
        # Increment major version (1.5 → 2.0)
        return float(int(current_version) + 1)
    else:
        # Increment minor version (1.0 → 1.1, 1.9 → 1.10)
        major = int(current_version)
        minor = round((current_version - major) * 10)  # Extract minor (1.5 → 5)
        new_minor = minor + 1
        return major + (new_minor / 10)


def _detect_recipe_changes(
    old_data: Dict,
    new_data: Dict,
    old_ingredients: List[Dict],
    new_ingredients: List[Dict]
) -> Dict:
    """
    Detect what changed between two recipe versions.
    Generates human-readable change summary.
    
    Args:
        old_data: Previous recipe metadata
        new_data: New recipe metadata
        old_ingredients: Previous ingredients list
        new_ingredients: New ingredients list
    
    Returns:
        {
            'summary': 'Reduced salt from 10g to 7g, Added garlic',
            'fields_changed': ['salt', 'garlic', 'description'],
            'change_type': 'minor'  # or 'major'
        }
    """
    changes = []
    fields_changed = []
    
    # Check metadata changes
    metadata_fields = ['name', 'description', 'serves', 'cuisine', 'category', 
                      'prep_time_minutes', 'cook_time_minutes', 'difficulty']
    
    for field in metadata_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        if old_val != new_val and new_val is not None:
            fields_changed.append(field)
            if field == 'name':
                changes.append(f"Renamed to '{new_val}'")
            elif field in ['serves', 'prep_time_minutes', 'cook_time_minutes']:
                changes.append(f"Changed {field.replace('_', ' ')} from {old_val} to {new_val}")
    
    # Check ingredient changes
    old_ing_map = {ing['name'].lower(): ing for ing in old_ingredients if 'name' in ing}
    new_ing_map = {ing['name'].lower(): ing for ing in new_ingredients if 'name' in ing}
    
    # Removed ingredients
    removed = set(old_ing_map.keys()) - set(new_ing_map.keys())
    for ing_name in removed:
        changes.append(f"Removed {ing_name}")
        fields_changed.append(ing_name)
    
    # Added ingredients
    added = set(new_ing_map.keys()) - set(old_ing_map.keys())
    for ing_name in added:
        changes.append(f"Added {ing_name}")
        fields_changed.append(ing_name)
    
    # Modified quantities
    for ing_name in set(old_ing_map.keys()) & set(new_ing_map.keys()):
        old_ing = old_ing_map[ing_name]
        new_ing = new_ing_map[ing_name]
        
        old_qty = old_ing.get('quantity', 0)
        new_qty = new_ing.get('quantity', 0)
        
        if old_qty != new_qty:
            old_unit = old_ing.get('unit', '')
            new_unit = new_ing.get('unit', '')
            unit = new_unit if new_unit == old_unit else f"{old_unit} to {new_unit}"
            changes.append(f"Changed {ing_name} from {old_qty}{old_unit} to {new_qty}{new_unit}")
            fields_changed.append(ing_name)
    
    # Determine change type
    # Major change: name change, > 3 ingredient changes, or complete recipe overhaul
    major_indicators = ['name' in fields_changed, len(fields_changed) > 3, 
                       len(removed) > 2, len(added) > 2]
    change_type = "major" if any(major_indicators) else "minor"
    
    summary = ", ".join(changes[:5]) if changes else "Minor adjustments"
    if len(changes) > 5:
        summary += f" and {len(changes) - 5} more changes"
    
    return {
        'summary': summary,
        'fields_changed': fields_changed,
        'change_type': change_type
    }


def _create_recipe_version(
    cur,
    recipe_id: str,
    recipe_type: str,
    version_number: float,
    recipe_data: Dict,
    ingredients: List[Dict],
    created_by: str,
    change_summary: Optional[str] = None,
    change_reason: Optional[str] = None
) -> str:
    """
    Create a new version snapshot for a recipe.
    Stores complete recipe state at this version.
    
    Args:
        cur: Database cursor
        recipe_id: Parent recipe UUID
        recipe_type: 'plate' or 'batch'
        version_number: Version number (1.0, 1.1, etc.)
        recipe_data: Complete recipe metadata dict
        ingredients: List of ingredient dicts
        created_by: Chef ID who created this version
        change_summary: Auto-generated change description
        change_reason: User-provided reason for change
    
    Returns:
        version_id (UUID string)
    """
    if recipe_type == "plate":
        # Insert into plate_recipe_versions
        cur.execute("""
            INSERT INTO plate_recipe_versions (
                recipe_id, version_number, is_active, created_by,
                change_summary, change_reason,
                name, description, serves, category, cuisine,
                plating_instructions, garnish, presentation_notes,
                prep_time_minutes, cook_time_minutes, difficulty, notes
            ) VALUES (
                %s, %s, true, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            recipe_id, version_number, created_by, change_summary, change_reason,
            recipe_data.get('name'), recipe_data.get('description'),
            recipe_data.get('serves'), recipe_data.get('category'),
            recipe_data.get('cuisine'), recipe_data.get('plating_instructions'),
            recipe_data.get('garnish'), recipe_data.get('presentation_notes'),
            recipe_data.get('prep_time_minutes'), recipe_data.get('cook_time_minutes'),
            recipe_data.get('difficulty'), recipe_data.get('notes')
        ))
        
        version_id = cur.fetchone()[0]
        
        # Insert ingredients for this version
        for ing in ingredients:
            # Get ingredient ID from ingredients table
            cur.execute("""
                SELECT id FROM ingredients 
                WHERE name = %s
            """, (ing['name'],))
            
            ing_result = cur.fetchone()
            if not ing_result:
                # Create ingredient if it doesn't exist
                cur.execute("""
                    INSERT INTO ingredients (name, unit, category)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (ing['name'], ing.get('unit', ''), ing.get('category', 'Other')))
                ingredient_id = cur.fetchone()[0]
            else:
                ingredient_id = ing_result[0]
            
            # Insert into plate_version_ingredients
            cur.execute("""
                INSERT INTO plate_version_ingredients (
                    version_id, ingredient_id, quantity, unit,
                    preparation_notes, is_garnish, is_optional
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                version_id, ingredient_id,
                ing.get('quantity', 0), ing.get('unit', ''),
                ing.get('preparation_notes'), ing.get('is_garnish', False),
                ing.get('is_optional', False)
            ))
    
    else:  # batch recipe
        # Insert into batch_recipe_versions
        cur.execute("""
            INSERT INTO batch_recipe_versions (
                recipe_id, version_number, is_active, created_by,
                change_summary, change_reason,
                name, description, yield_quantity, yield_unit,
                prep_time_minutes, cook_time_minutes,
                storage_instructions, temperature, temperature_unit,
                equipment, instructions, notes
            ) VALUES (
                %s, %s, true, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            recipe_id, version_number, created_by, change_summary, change_reason,
            recipe_data.get('name'), recipe_data.get('description'),
            recipe_data.get('yield_quantity'), recipe_data.get('yield_unit'),
            recipe_data.get('prep_time_minutes'), recipe_data.get('cook_time_minutes'),
            recipe_data.get('storage_instructions'), recipe_data.get('temperature'),
            recipe_data.get('temperature_unit'), recipe_data.get('equipment'),
            recipe_data.get('instructions'), recipe_data.get('notes')
        ))
        
        version_id = cur.fetchone()[0]
        
        # Insert ingredients
        for ing in ingredients:
            cur.execute("""
                SELECT id FROM ingredients WHERE name = %s
            """, (ing['name'],))
            
            ing_result = cur.fetchone()
            if not ing_result:
                cur.execute("""
                    INSERT INTO ingredients (name, unit, category)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (ing['name'], ing.get('unit', ''), ing.get('category', 'Other')))
                ingredient_id = cur.fetchone()[0]
            else:
                ingredient_id = ing_result[0]
            
            # Insert into batch_version_ingredients
            cur.execute("""
                INSERT INTO batch_version_ingredients (
                    version_id, ingredient_id, quantity, unit,
                    preparation_notes, is_optional
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                version_id, ingredient_id,
                ing.get('quantity', 0), ing.get('unit', ''),
                ing.get('preparation_notes'), ing.get('is_optional', False)
            ))
    
    return str(version_id)


# ==================== BATCH RECIPES ====================

def save_batch_recipe(
    chef_id: str,
    name: str,
    description: Optional[str] = None,
    yield_quantity: Optional[float] = None,
    yield_unit: Optional[str] = None,
    prep_time_minutes: Optional[int] = None,
    cook_time_minutes: Optional[int] = None,
    temperature: Optional[float] = None,
    temperature_unit: str = 'C',
    equipment: Optional[List[str]] = None,
    instructions: Optional[str] = None,
    ingredients: Optional[List[Dict]] = None,
    notes: Optional[str] = None,
    is_complete: bool = False
) -> str:
    """
    Save a batch recipe with ingredients
    Returns: recipe_id (UUID)
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for duplicate name and get unique version if needed
        unique_name = _get_unique_recipe_name(cur, chef_id, name, 'batch')
        if unique_name != name:
            logger.info(f"📝 Recipe name '{name}' already exists, using '{unique_name}' instead")
            name = unique_name  # Use the versioned name
        
        # Insert batch recipe
        cur.execute("""
            INSERT INTO batch_recipes (
                chef_id, name, description, yield_quantity, yield_unit,
                prep_time_minutes, cook_time_minutes, temperature, temperature_unit,
                equipment, instructions, notes, is_complete
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            chef_id, name, description, yield_quantity, yield_unit,
            prep_time_minutes, cook_time_minutes, temperature, temperature_unit,
            equipment, instructions, notes, is_complete
        ))
        
        recipe_id = cur.fetchone()['id']
        
        # Add ingredients if provided
        if ingredients:
            for ing in ingredients:
                # First, ensure ingredient exists or create it
                ing_id = _get_or_create_ingredient(
                    cur, chef_id, ing.get('name'), ing.get('unit'), ing.get('category')
                )
                
                # Link ingredient to batch recipe
                cur.execute("""
                    INSERT INTO batch_ingredients (
                        batch_recipe_id, ingredient_id, quantity, unit, preparation_notes, is_optional
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    recipe_id, ing_id, ing.get('quantity'), ing.get('unit'),
                    ing.get('preparation_notes'), ing.get('is_optional', False)
                ))
        
        conn.commit()
        print(f"✅ Saved batch recipe: {name} ({recipe_id})")
        
        # ==================== CREATE VERSION 1.0 ====================
        # Automatically create version 1.0 for new batch recipes
        try:
            recipe_data = {
                'name': name,
                'description': description,
                'yield_quantity': yield_quantity,
                'yield_unit': yield_unit,
                'prep_time_minutes': prep_time_minutes,
                'cook_time_minutes': cook_time_minutes,
                'storage_instructions': notes,
                'temperature': temperature,
                'temperature_unit': temperature_unit,
                'equipment': equipment,
                'instructions': instructions,
                'notes': notes
            }
            
            version_ingredients = ingredients if ingredients else []
            
            version_id = _create_recipe_version(
                cur=cur,
                recipe_id=str(recipe_id),
                recipe_type="batch",
                version_number=1.0,
                recipe_data=recipe_data,
                ingredients=version_ingredients,
                created_by=chef_id,
                change_summary="Initial recipe creation (v1.0)",
                change_reason=None
            )
            
            conn.commit()
            logger.info(f"✅ Created version 1.0 for batch recipe '{name}' (version_id: {version_id})")
            
        except Exception as version_error:
            logger.error(f"⚠️ Failed to create v1.0 for batch '{name}': {version_error}")
            conn.rollback()
        
        # ==================== END VERSION CREATION ====================
        
        
        # Sync to Google Sheets (non-blocking, failures don't affect DB save)
        if SHEETS_ENABLED:
            try:
                recipe_data = {
                    'id': recipe_id,
                    'chef_id': chef_id,
                    'name': name,
                    'description': description,
                    'yield_quantity': yield_quantity,
                    'yield_unit': yield_unit,
                    'instructions': instructions,
                    'storage_instructions': notes  # Using notes as storage instructions
                }
                google_sheets.add_batch_recipe(recipe_data, ingredients)
            except Exception as sheets_error:
                logger.warning(f"Google Sheets sync failed (DB save succeeded): {sheets_error}")
        
        return str(recipe_id)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving batch recipe: {e}")
        raise
    finally:
        cur.close()
        return_connection(conn)

# ==================== PLATE RECIPES ====================

def save_plate_recipe(
    chef_id: str,
    name: str,
    description: Optional[str] = None,
    serves: Optional[int] = None,
    category: Optional[str] = None,
    cuisine: Optional[str] = None,
    plating_instructions: Optional[str] = None,
    garnish: Optional[str] = None,
    presentation_notes: Optional[str] = None,
    prep_time_minutes: Optional[int] = None,
    cook_time_minutes: Optional[int] = None,
    difficulty: Optional[str] = None,
    batch_recipes: Optional[List[Dict]] = None,
    ingredients: Optional[List[Dict]] = None,
    notes: Optional[str] = None,
    is_complete: bool = False
) -> str:
    """
    Save a plate recipe with batch recipes and/or direct ingredients
    Returns: recipe_id (UUID)
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for duplicate name and get unique version if needed
        unique_name = _get_unique_recipe_name(cur, chef_id, name, 'plate')
        if unique_name != name:
            logger.info(f"📝 Recipe name '{name}' already exists, using '{unique_name}' instead")
            name = unique_name  # Use the versioned name
        
        # Insert plate recipe
        cur.execute("""
            INSERT INTO plate_recipes (
                chef_id, name, description, serves, category, cuisine,
                plating_instructions, garnish, presentation_notes,
                prep_time_minutes, cook_time_minutes, difficulty, notes, is_complete
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            chef_id, name, description, serves, category, cuisine,
            plating_instructions, garnish, presentation_notes,
            prep_time_minutes, cook_time_minutes, difficulty, notes, is_complete
        ))
        
        recipe_id = cur.fetchone()['id']
        
        # Link batch recipes if provided
        if batch_recipes:
            for i, batch in enumerate(batch_recipes):
                batch_id = batch.get('batch_id') or _find_batch_recipe_by_name(cur, chef_id, batch.get('name'))
                if batch_id:
                    cur.execute("""
                        INSERT INTO plate_batches (
                            plate_recipe_id, batch_recipe_id, quantity, unit, assembly_order, preparation_notes
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        recipe_id, batch_id, batch.get('quantity'), batch.get('unit'),
                        i + 1, batch.get('preparation_notes')
                    ))
        
        # Link direct ingredients if provided
        if ingredients:
            for ing in ingredients:
                ing_id = _get_or_create_ingredient(
                    cur, chef_id, ing.get('name'), ing.get('unit'), ing.get('category')
                )
                cur.execute("""
                    INSERT INTO plate_ingredients (
                        plate_recipe_id, ingredient_id, quantity, unit, preparation_notes, is_garnish, is_optional
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    recipe_id, ing_id, ing.get('quantity'), ing.get('unit'),
                    ing.get('preparation_notes'), ing.get('is_garnish', False), ing.get('is_optional', False)
                ))
        
        conn.commit()
        print(f"✅ Saved plate recipe: {name} ({recipe_id})")
        
        # ==================== CREATE VERSION 1.0 ====================
        # Automatically create version 1.0 for new recipes to enable version tracking
        try:
            # Prepare recipe data for version snapshot
            recipe_data = {
                'name': name,
                'description': description,
                'serves': serves,
                'category': category,
                'cuisine': cuisine,
                'plating_instructions': plating_instructions,
                'garnish': garnish,
                'presentation_notes': presentation_notes,
                'prep_time_minutes': prep_time_minutes,
                'cook_time_minutes': cook_time_minutes,
                'difficulty': difficulty,
                'notes': notes
            }
            
            # Prepare ingredients list for versioning
            version_ingredients = ingredients if ingredients else []
            
            # Create v1.0 in versioning system
            version_id = _create_recipe_version(
                cur=cur,
                recipe_id=str(recipe_id),
                recipe_type="plate",
                version_number=1.0,
                recipe_data=recipe_data,
                ingredients=version_ingredients,
                created_by=chef_id,
                change_summary="Initial recipe creation (v1.0)",
                change_reason=None
            )
            
            conn.commit()
            logger.info(f"✅ Created version 1.0 for plate recipe '{name}' (version_id: {version_id})")
            
        except Exception as version_error:
            # Version creation failure shouldn't block recipe save
            logger.error(f"⚠️ Failed to create v1.0 for '{name}': {version_error}")
            conn.rollback()  # Rollback version, but recipe is still saved
        
        # ==================== END VERSION CREATION ====================
        
        
        # Sync to Google Sheets (non-blocking, failures don't affect DB save)
        if SHEETS_ENABLED:
            try:
                recipe_data = {
                    'id': recipe_id,
                    'chef_id': chef_id,
                    'name': name,
                    'description': description,
                    'serves': serves,
                    'category': category,
                    'cuisine': cuisine,
                    'plating_instructions': plating_instructions
                }
                google_sheets.add_plate_recipe(recipe_data, ingredients)
            except Exception as sheets_error:
                logger.warning(f"Google Sheets sync failed (DB save succeeded): {sheets_error}")
        
        return str(recipe_id)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving plate recipe: {e}")
        raise
    finally:
        cur.close()
        return_connection(conn)


# ==================== RECIPE UPDATE ====================

def update_recipe(
    chef_id: str,
    recipe_name: str,
    recipe_type: str = "plate",
    new_name: Optional[str] = None,
    new_description: Optional[str] = None,
    new_serves: Optional[int] = None,
    new_cuisine: Optional[str] = None,
    new_category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing recipe's fields.
    Returns: {"success": True/False, "message": str, "recipe_id": str}
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find the recipe first
        if recipe_type == "plate":
            cur.execute("""
                SELECT id, name FROM plate_recipes 
                WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
            """, (chef_id, recipe_name))
        else:
            cur.execute("""
                SELECT id, name FROM batch_recipes 
                WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
            """, (chef_id, recipe_name))
        
        recipe = cur.fetchone()
        
        if not recipe:
            return {
                "success": False,
                "message": f"Recipe '{recipe_name}' not found",
                "recipe_id": None
            }
        
        recipe_id = recipe['id']
        old_name = recipe['name']
        
        # Build dynamic UPDATE query
        updates = []
        params = []
        
        if new_name:
            updates.append("name = %s")
            params.append(new_name)
        if new_description:
            updates.append("description = %s")
            params.append(new_description)
        
        if recipe_type == "plate":
            if new_serves:
                updates.append("serves = %s")
                params.append(new_serves)
            if new_cuisine:
                updates.append("cuisine = %s")
                params.append(new_cuisine)
            if new_category:
                updates.append("category = %s")
                params.append(new_category)
        
        if not updates:
            return {
                "success": False,
                "message": "No fields to update",
                "recipe_id": str(recipe_id)
            }
        
        # Add recipe_id to params
        params.append(recipe_id)
        
        # Execute update
        if recipe_type == "plate":
            cur.execute(f"""
                UPDATE plate_recipes 
                SET {', '.join(updates)}, updated_at = NOW()
                WHERE id = %s
            """, params)
        else:
            cur.execute(f"""
                UPDATE batch_recipes 
                SET {', '.join(updates)}, updated_at = NOW()
                WHERE id = %s
            """, params)
        
        conn.commit()
        
        # Build success message
        changed_fields = []
        if new_name:
            changed_fields.append(f"name from '{old_name}' to '{new_name}'")
        if new_description:
            changed_fields.append("description")
        if new_serves:
            changed_fields.append(f"serves to {new_serves}")
        if new_cuisine:
            changed_fields.append(f"cuisine to '{new_cuisine}'")
        if new_category:
            changed_fields.append(f"category to '{new_category}'")
        
        message = f"Updated {', '.join(changed_fields)} for recipe"
        print(f"✅ {message}")
        
        # Sync update to Google Sheets
        if SHEETS_ENABLED:
            try:
                updates = {}
                if new_name:
                    updates['name'] = new_name
                if new_description:
                    updates['description'] = new_description
                if new_serves:
                    updates['serves'] = new_serves
                if new_cuisine:
                    updates['cuisine'] = new_cuisine
                if new_category:
                    updates['category'] = new_category
                google_sheets.update_recipe(str(recipe_id), recipe_type, updates)
            except Exception as sheets_error:
                logger.warning(f"Google Sheets update sync failed: {sheets_error}")
        
        return {
            "success": True,
            "message": message,
            "recipe_id": str(recipe_id),
            "new_name": new_name or old_name
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating recipe: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "recipe_id": None
        }
    finally:
        cur.close()
        return_connection(conn)


def delete_recipe(
    chef_id: str,
    recipe_name: str,
    recipe_type: str = "plate"
) -> Dict[str, Any]:
    """
    Delete a recipe from the database.
    Returns: {"success": True/False, "message": str}
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find the recipe first
        if recipe_type == "plate":
            cur.execute("""
                SELECT id, name FROM plate_recipes 
                WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
            """, (chef_id, recipe_name))
        else:
            cur.execute("""
                SELECT id, name FROM batch_recipes 
                WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
            """, (chef_id, recipe_name))
        
        recipe = cur.fetchone()
        
        if not recipe:
            return {
                "success": False,
                "message": f"Recipe '{recipe_name}' not found"
            }
        
        recipe_id = recipe['id']
        actual_name = recipe['name']
        
        # Delete the recipe
        if recipe_type == "plate":
            cur.execute("DELETE FROM plate_recipes WHERE id = %s", (recipe_id,))
        else:
            cur.execute("DELETE FROM batch_recipes WHERE id = %s", (recipe_id,))
        
        conn.commit()
        print(f"✅ Deleted {recipe_type} recipe: {actual_name}")
        
        # Sync deletion to Google Sheets
        if SHEETS_ENABLED:
            try:
                google_sheets.delete_recipe(str(recipe_id), recipe_type)
            except Exception as sheets_error:
                logger.warning(f"Google Sheets delete sync failed: {sheets_error}")
        
        return {
            "success": True,
            "message": f"Deleted {recipe_type} recipe '{actual_name}'"
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting recipe: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }
    finally:
        cur.close()
        return_connection(conn)

# ==================== RECIPE RETRIEVAL ====================

def get_recipe_by_name(chef_id: str, name: str, recipe_type: Optional[str] = None) -> Optional[Dict]:
    """
    Search for a recipe by name (supports partial/fuzzy search)
    recipe_type: 'batch', 'plate', or None (searches both)
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Try batch recipes if type is None or 'batch'
        if recipe_type in (None, 'batch'):
            cur.execute("""
                SELECT * FROM batch_recipes
                WHERE chef_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (chef_id, f'%{name}%'))
            
            result = cur.fetchone()
            if result:
                # Get ingredients
                cur.execute("""
                    SELECT i.name, bi.quantity, bi.unit, bi.preparation_notes, bi.is_optional
                    FROM batch_ingredients bi
                    JOIN ingredients i ON bi.ingredient_id = i.id
                    WHERE bi.batch_recipe_id = %s
                """, (result['id'],))
                
                result['ingredients'] = cur.fetchall()
                result['type'] = 'batch'
                return dict(result)
        
        # Try plate recipes if type is None or 'plate'
        if recipe_type in (None, 'plate'):
            cur.execute("""
                SELECT * FROM plate_recipes
                WHERE chef_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (chef_id, f'%{name}%'))
            
            result = cur.fetchone()
            if result:
                # Get batch recipes used
                cur.execute("""
                    SELECT br.name, pb.quantity, pb.unit, pb.preparation_notes
                    FROM plate_batches pb
                    JOIN batch_recipes br ON pb.batch_recipe_id = br.id
                    WHERE pb.plate_recipe_id = %s
                    ORDER BY pb.assembly_order
                """, (result['id'],))
                
                result['batch_recipes'] = cur.fetchall()
                
                # Get direct ingredients
                cur.execute("""
                    SELECT i.name, pi.quantity, pi.unit, pi.preparation_notes, pi.is_garnish, pi.is_optional
                    FROM plate_ingredients pi
                    JOIN ingredients i ON pi.ingredient_id = i.id
                    WHERE pi.plate_recipe_id = %s
                """, (result['id'],))
                
                result['ingredients'] = cur.fetchall()
                result['type'] = 'plate'
                return dict(result)
        
        return None
        
    finally:
        cur.close()
        return_connection(conn)


def smart_search_recipes(chef_id: str, query: str) -> Dict:
    """
    Smart search with PRIORITY:
    1. EXACT match (highest priority)
    2. Contains full query  
    3. Keyword partial match (lowest priority)
    
    Returns best_match with full details when exact/good match found.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query_clean = query.strip()
        query_lower = query_clean.lower()
        
        # ===== STEP 1: Try EXACT match first =====
        # Check plate recipes for exact match
        cur.execute("""
            SELECT id, name, description, serves, category, cuisine, 
                   plating_instructions, garnish, presentation_notes, notes, is_complete
            FROM plate_recipes
            WHERE chef_id = %s AND LOWER(name) = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (chef_id, query_lower))
        
        exact_plate = cur.fetchone()
        if exact_plate:
            # Get full details including ingredients
            full_recipe = get_recipe_by_name(chef_id, exact_plate['name'], 'plate')
            return {
                'exact_match': True,
                'total_found': 1,
                'recipe_type': 'plate',
                'recipe': full_recipe,
                'batch_recipes': [],
                'plate_recipes': [dict(exact_plate)]
            }
        
        # Check batch recipes for exact match
        cur.execute("""
            SELECT id, name, description, yield_quantity, yield_unit,
                   instructions, notes, is_complete
            FROM batch_recipes
            WHERE chef_id = %s AND LOWER(name) = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (chef_id, query_lower))
        
        exact_batch = cur.fetchone()
        if exact_batch:
            full_recipe = get_recipe_by_name(chef_id, exact_batch['name'], 'batch')
            return {
                'exact_match': True,
                'total_found': 1,
                'recipe_type': 'batch',
                'recipe': full_recipe,
                'batch_recipes': [dict(exact_batch)],
                'plate_recipes': []
            }
        
        # ===== STEP 2: Try CONTAINS full query =====
        # This catches "Hyderabadi Chicken Biryani" when searching "chicken biryani"
        cur.execute("""
            SELECT id, name, description, serves, category, cuisine,
                   plating_instructions, notes, is_complete
            FROM plate_recipes
            WHERE chef_id = %s AND name ILIKE %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (chef_id, f'%{query_clean}%'))
        
        contains_plate = cur.fetchone()
        if contains_plate:
            full_recipe = get_recipe_by_name(chef_id, contains_plate['name'], 'plate')
            return {
                'exact_match': False,
                'best_match': True,
                'total_found': 1,
                'recipe_type': 'plate',
                'recipe': full_recipe,
                'batch_recipes': [],
                'plate_recipes': [dict(contains_plate)]
            }
        
        cur.execute("""
            SELECT id, name, description, yield_quantity, yield_unit,
                   instructions, notes, is_complete
            FROM batch_recipes
            WHERE chef_id = %s AND name ILIKE %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (chef_id, f'%{query_clean}%'))
        
        contains_batch = cur.fetchone()
        if contains_batch:
            full_recipe = get_recipe_by_name(chef_id, contains_batch['name'], 'batch')
            return {
                'exact_match': False,
                'best_match': True,
                'total_found': 1,
                'recipe_type': 'batch',
                'recipe': full_recipe,
                'batch_recipes': [dict(contains_batch)],
                'plate_recipes': []
            }
        
        # ===== STEP 3: Keyword search (fallback) =====
        # Only used when no exact/contains match found
        results = {
            'exact_match': False,
            'best_match': False,
            'batch_recipes': [],
            'plate_recipes': [],
            'total_found': 0
        }
        
        keywords = [kw for kw in query_lower.split() if len(kw) > 2]
        if not keywords:
            keywords = [query_lower]
        
        # Collect unique matches
        seen_plates = set()
        seen_batches = set()
        
        for kw in keywords:
            pattern = f'%{kw}%'
            
            cur.execute("""
                SELECT id, name, description, serves, category, cuisine, is_complete
                FROM plate_recipes
                WHERE chef_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (chef_id, pattern))
            
            for row in cur.fetchall():
                if row['id'] not in seen_plates:
                    seen_plates.add(row['id'])
                    results['plate_recipes'].append(dict(row))
            
            cur.execute("""
                SELECT id, name, description, yield_quantity, yield_unit, is_complete
                FROM batch_recipes
                WHERE chef_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (chef_id, pattern))
            
            for row in cur.fetchall():
                if row['id'] not in seen_batches:
                    seen_batches.add(row['id'])
                    results['batch_recipes'].append(dict(row))
        
        results['total_found'] = len(results['batch_recipes']) + len(results['plate_recipes'])
        
        # If only ONE total match, get full details
        if results['total_found'] == 1:
            if results['plate_recipes']:
                full_recipe = get_recipe_by_name(chef_id, results['plate_recipes'][0]['name'], 'plate')
                results['recipe'] = full_recipe
                results['recipe_type'] = 'plate'
            else:
                full_recipe = get_recipe_by_name(chef_id, results['batch_recipes'][0]['name'], 'batch')
                results['recipe'] = full_recipe
                results['recipe_type'] = 'batch'
        
        return results
        
    finally:
        cur.close()
        return_connection(conn)




def list_chef_recipes(chef_id: str, limit: int = 50) -> Dict[str, List]:
    """Get all recipes for a chef"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get batch recipes
        cur.execute("""
            SELECT id, name, description, yield_quantity, yield_unit, created_at, is_complete
            FROM batch_recipes
            WHERE chef_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (chef_id, limit))
        batch_recipes = cur.fetchall()
        
        # Get plate recipes
        cur.execute("""
            SELECT id, name, description, serves, category, cuisine, created_at, is_complete
            FROM plate_recipes
            WHERE chef_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (chef_id, limit))
        plate_recipes = cur.fetchall()
        
        return {
            'batch_recipes': [dict(r) for r in batch_recipes],
            'plate_recipes': [dict(r) for r in plate_recipes]
        }
        
    finally:
        cur.close()
        return_connection(conn)

# ==================== CONVERSATIONS ====================

def save_conversation(chef_id: str, session_id: str, context: Dict, messages: List[Dict]) -> None:
    """Save or update conversation state"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO conversations (chef_id, session_id, current_context, message_history, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT (session_id) DO UPDATE
            SET current_context = EXCLUDED.current_context,
                message_history = EXCLUDED.message_history,
                updated_at = NOW()
        """, (chef_id, session_id, json.dumps(context), json.dumps(messages)))
        
        conn.commit()
        
    finally:
        cur.close()
        return_connection(conn)

def get_conversation(session_id: str) -> Optional[Dict]:
    """Retrieve conversation state"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM conversations WHERE session_id = %s
        """, (session_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
        
    finally:
        cur.close()
        return_connection(conn)

# ==================== HELPER FUNCTIONS ====================

def _get_or_create_ingredient(cur, chef_id: str, name: str, unit: Optional[str], category: Optional[str]) -> str:
    """Get existing ingredient or create new one"""
    # Try to find existing
    cur.execute("""
        SELECT id FROM ingredients
        WHERE chef_id = %s AND LOWER(name) = LOWER(%s)
        LIMIT 1
    """, (chef_id, name))
    
    result = cur.fetchone()
    if result:
        return result['id']
    
    # Create new
    cur.execute("""
        INSERT INTO ingredients (chef_id, name, unit, category)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (chef_id, name, unit, category))
    
    return cur.fetchone()['id']

def _find_batch_recipe_by_name(cur, chef_id: str, name: str) -> Optional[str]:
    """Find batch recipe ID by name"""
    cur.execute("""
        SELECT id FROM batch_recipes
        WHERE chef_id = %s AND name ILIKE %s
        LIMIT 1
    """, (chef_id, f'%{name}%'))
    
    result = cur.fetchone()
    return result['id'] if result else None
