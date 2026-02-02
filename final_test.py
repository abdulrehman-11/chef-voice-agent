"""
Final Verification Test for Versioning System
This test will:
1. Create a new recipe (v1.0)
2. Make minor update (v1.1)
3. Make major update (v2.0)
4. Show version history
5. Keep the data for user verification
"""
import sys
sys.path.append('backend')
import database as db

CHEF_ID = "mock_user"
RECIPE_NAME = "Versioning Test Chocolate Cake"

print("=" * 70)
print("FINAL VERSIONING VERIFICATION TEST")
print("=" * 70)

# Clean up old test if exists
try:
    db.delete_recipe(CHEF_ID, RECIPE_NAME, "plate")
except:
    pass

print("\n[STEP 1] Creating new recipe (should create v1.0)...")
recipe_id = db.save_plate_recipe(
    chef_id=CHEF_ID,
    name=RECIPE_NAME,
    description="Rich chocolate cake",
    serves=8,
    category="Dessert",
    cuisine="French",
    difficulty="Medium",
    prep_time_minutes=30,
    cook_time_minutes=45,
    ingredients=[
        {"name": "chocolate", "quantity": 200, "unit": "grams"},
        {"name": "flour", "quantity": 250, "unit": "grams"},
        {"name": "sugar", "quantity": 150, "unit": "grams"},
        {"name": "eggs", "quantity": 4, "unit": "whole"},
    ],
    is_complete=True
)

print(f"Recipe ID: {recipe_id}")

# Check v1.0
conn = db.get_connection()
cur = conn.cursor()
cur.execute("SELECT version_number, is_active FROM plate_recipe_versions WHERE recipe_id = %s", (recipe_id,))
versions = cur.fetchall()
print(f"Versions: {[(v[0], 'ACTIVE' if v[1] else 'inactive') for v in versions]}")

if 1.0 in [v[0] for v in versions]:
    print("SUCCESS: v1.0 created!")
else:
    print("FAIL: v1.0 NOT created")

print("\n[STEP 2] Minor update: change serves from 8 to 10...")
result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_serves=10
)

print(f"Update result: {result['success']}")

cur.execute("SELECT version_number, is_active, change_summary FROM plate_recipe_versions WHERE recipe_id = %s ORDER BY version_number", (recipe_id,))
versions = cur.fetchall()
print(f"Versions: {len(versions)}")
for v_num, v_active, v_summary in versions:
    print(f"  v{v_num} ({'ACTIVE' if v_active else 'inactive'}): {v_summary}")

print("\n[STEP 3] Major update: change name, description, and category...")
result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_name="Ultimate Chocolate Indulgence",
    new_description="Decadent triple-layer chocolate masterpiece",
    new_category="Fine Dining Dessert"
)

print(f"Update result: {result['success']}")

cur.execute("""
    SELECT version_number, is_active, change_summary, created_at
    FROM plate_recipe_versions 
    WHERE recipe_id = %s 
    ORDER BY version_number
""", (recipe_id,))

versions = cur.fetchall()

print("\n" + "=" * 70)
print("FINAL VERSION HISTORY:")
print("=" * 70)

for v_num, v_active, v_summary, v_created in versions:
    status = "[ACTIVE]" if v_active else "[inactive]"
    print(f"\nVersion {v_num} {status}")
    print(f"  Created: {v_created}")
    print(f"  Changes: {v_summary}")

print("\n" + "=" * 70)
print("TEST SUMMARY:")
print("=" * 70)

has_v10 = any(v[0] == 1.0 for v in versions)
has_v11 = any(v[0] == 1.1 for v in versions)
has_v20 = any(v[0] == 2.0 for v in versions)
active_version = [v[0] for v in versions if v[1]]

print(f"v1.0 created: {has_v10}")
print(f"v1.1 created: {has_v11}")
print(f"v2.0 created: {has_v20}")
print(f"Active version: {active_version[0] if active_version else 'NONE'}")
print(f"Total versions: {len(versions)}")

if has_v10 and has_v11 and has_v20 and active_version == [2.0]:
    print("\n*** ALL TESTS PASSED! Versioning is FULLY FUNCTIONAL! ***")
else:
    print("\n*** SOME TESTS FAILED ***")

print("\nRecipe kept in database for verification.")
print(f"Recipe ID: {recipe_id}")
print(f"Current name: {result.get('new_name', RECIPE_NAME)}")

cur.close()
db.return_connection(conn)

print("\n" + "=" * 70)
