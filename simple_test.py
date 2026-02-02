"""
Simple Versioning Test - No Emojis
"""
import sys
sys.path.append('backend')

import database as db

CHEF_ID = "test_chef"
RECIPE_NAME = "Test Pancakes"

print("VERSIONING TEST")
print("=" * 60)

# Clean up
try:
    db.delete_recipe(CHEF_ID, RECIPE_NAME, "plate")
except:
    pass

# TEST 1: Create recipe (should make v1.0)
print("\n[TEST 1] Creating new recipe...")
recipe_id = db.save_plate_recipe(
    chef_id=CHEF_ID,
    name=RECIPE_NAME,
    description="Fluffy pancakes",
    serves=4,
    ingredients=[
        {"name": "flour", "quantity": 200, "unit": "grams"},
        {"name": "milk", "quantity": 300, "unit": "ml"},
    ],
    is_complete=True
)

# Check v1.0
conn = db.get_connection()
cur = conn.cursor()
cur.execute("SELECT version_number FROM plate_recipe_versions WHERE recipe_id = %s", (recipe_id,))
versions = [row[0] for row in cur.fetchall()]

print(f"Recipe ID: {recipe_id}")
print(f"Versions: {versions}")

if 1.0 in versions:
    print("PASS: v1.0 created")
else:
    print("FAIL: v1.0 NOT created")

# TEST 2: Minor update (should make v1.1)
print("\n[TEST 2] Updating serves to 6 (minor change)...")
result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_serves=6
)

print(f"Update result: {result['success']}")

cur.execute("SELECT version_number, is_active FROM plate_recipe_versions WHERE recipe_id = %s ORDER BY version_number", (recipe_id,))
versions = cur.fetchall()

print(f"Total versions: {len(versions)}")
for v_num, v_active in versions:
    status = "ACTIVE" if v_active else "inactive"
    print(f"  v{v_num} ({status})")

if len(versions) == 2 and any(v[0] == 1.1 and v[1] for v in versions):
    print("PASS: v1.1 created and active")
else:
    print("FAIL: v1.1 NOT created")

# TEST 3: Major update (should make v2.0)
print("\n[TEST 3] Updating name + description (major change)...")
result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_name="Ultimate Pancakes",
    new_description="Best pancakes ever"
)

print(f"Update result: {result['success']}")

cur.execute("SELECT version_number, is_active, change_summary FROM plate_recipe_versions WHERE recipe_id = %s ORDER BY version_number", (recipe_id,))
versions = cur.fetchall()

print(f"Total versions: {len(versions)}")
for v_num, v_active, v_summary in versions:
    status = "ACTIVE" if v_active else "inactive"
    print(f"  v{v_num} ({status}): {v_summary}")

if len(versions) == 3 and any(v[0] == 2.0 and v[1] for v in versions):
    print("PASS: v2.0 created and active")
else:
    print("FAIL: v2.0 NOT created")

# Summary
print("\n" + "=" * 60)
has_v10 = any(v[0] == 1.0 for v in versions)
has_v11 = any(v[0] == 1.1 for v in versions)
has_v20 = any(v[0] == 2.0 for v in versions)

if has_v10 and has_v11 and has_v20:
    print("ALL TESTS PASSED!")
else:
    print(f"TESTS FAILED: v1.0={has_v10}, v1.1={has_v11}, v2.0={has_v20}")

# Cleanup
db.delete_recipe(CHEF_ID, "Ultimate Pancakes", "plate")
cur.close()
db.return_connection(conn)
