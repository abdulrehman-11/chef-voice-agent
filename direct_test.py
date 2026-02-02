"""Direct test to see actual error"""
import sys
sys.path.append('backend')
import database as db
import traceback

CHEF_ID = "test"
RECIPE_NAME = "Direct Test"

# Clean up
try:
    db.delete_recipe(CHEF_ID, RECIPE_NAME, "plate")
except:
    pass

print("Creating recipe...")
try:
    recipe_id = db.save_plate_recipe(
        chef_id=CHEF_ID,
        name=RECIPE_NAME,
        description="Test",
        serves=4,
        ingredients=[{"name": "salt", "quantity": 5, "unit": "grams"}],
        is_complete=True
    )
    print(f"Recipe ID: {recipe_id}")
    
    # Check versions
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM plate_recipe_versions WHERE recipe_id = %s", (recipe_id,))
    count = cur.fetchone()[0]
    print(f"Versions created: {count}")
    
    if count == 0:
        print("ERROR: No version created!")
    else:
        print("SUCCESS: Version created!")
    
    cur.close()
    db.return_connection(conn)
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
