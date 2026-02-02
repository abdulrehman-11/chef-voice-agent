"""Debug version creation - capture actual exception"""
import sys
sys.path.append('backend')
import database as db
import traceback
from psycopg2.extras import RealDictCursor

# Clean up first
try:
    db.delete_recipe("debug_chef", "Debug Recipe", "plate")
except:
    pass

# Create a recipe manually and try creating version
conn = db.get_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

try:
    # Step 1: Create recipe WITHOUT versioning
    print("Creating recipe in DB...")
    cur.execute("""
        INSERT INTO plate_recipes (chef_id, name, description, serves)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, ("debug_chef", "Debug Recipe", "Test description", 4))
    
    recipe_id = cur.fetchone()['id']
    print(f"Recipe ID: {recipe_id}")
    
    # Step 2: Try to call _create_recipe_version directly
    print("\nAttempting to create version 1.0...")
    
    recipe_data = {
        "name": "Debug Recipe",
        "description": "Test description",
        "serves": 4,
        "category": None,
        "cuisine": None,
        "plating_instructions": None,
        "garnish": None,
        "presentation_notes": None,
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "difficulty": None,
        "notes": None
    }
    
    ingredients = []
    
    version_id = db._create_recipe_version(
        cur=cur,
        recipe_id=str(recipe_id),
        recipe_type="plate",
        version_number=1.0,
        recipe_data=recipe_data,
        ingredients=ingredients,
        created_by="debug_chef",
        change_summary="Initial version",
        change_reason=None
    )
    
    conn.commit()
    print(f"SUCCESS! Version ID: {version_id}")
    
    # Verify
    cur.execute("SELECT * FROM plate_recipe_versions WHERE recipe_id = %s", (recipe_id,))
    version = cur.fetchone()
    
    if version:
        print(f"\nVersion details:")
        print(f"  Version number: {version['version_number']}")
        print(f"  Is active: {version['is_active']}")
        print(f"  Change summary: {version['change_summary']}")
    
except Exception as e:
    conn.rollback()
    print(f"\nERROR CAUGHT: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

finally:
    # Cleanup
    cur.execute("DELETE FROM plate_recipes WHERE chef_id = 'debug_chef'")
    conn.commit()
    cur.close()
    db.return_connection(conn)
