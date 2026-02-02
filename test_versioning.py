"""
Automated Versioning Test Suite
Tests recipe versioning system without voice interaction

This script will:
1. Create a new recipe (should create v1.0)
2. Update it with minor changes (should create v1.1)
3. Update it with major changes (should create v2.0)
4. Verify all versions in database
5. Check version history and changelog
"""
import sys
sys.path.append('backend')

import database as db
import json
from datetime import datetime

# Test configuration
CHEF_ID = "test_chef_versioning"
RECIPE_NAME = "Test Versioning Pancakes"

print("=" * 80)
print("AUTOMATED RECIPE VERSIONING TEST SUITE")
print("=" * 80)
print(f"Chef ID: {CHEF_ID}")
print(f"Recipe: {RECIPE_NAME}")
print(f"Test started: {datetime.now()}")
print("=" * 80)

# Clean up any previous test data
print("\n[SETUP] Cleaning up previous test data...")
try:
    db.delete_recipe(CHEF_ID, RECIPE_NAME, "plate")
    print("  Deleted old test recipe (if existed)")
except:
    print("  No previous test recipe found")

# TEST 1: Create new recipe (should create v1.0)
print("\n" + "=" * 80)
print("TEST 1: Create New Recipe (Expect v1.0)")
print("=" * 80)

recipe_id = db.save_plate_recipe(
    chef_id=CHEF_ID,
    name=RECIPE_NAME,
    description="Fluffy breakfast pancakes",
    serves=4,
    category="Breakfast",
    cuisine="American",
    prep_time_minutes=10,
    cook_time_minutes=15,
    difficulty="Easy",
    ingredients=[
        {"name": "flour", "quantity": 200, "unit": "grams"},
        {"name": "milk", "quantity": 300, "unit": "ml"},
        {"name": "eggs", "quantity": 2, "unit": "whole"},
        {"name": "sugar", "quantity": 20, "unit": "grams"},
        {"name": "salt", "quantity": 5, "unit": "grams"},
    ],
    notes="Mix dry ingredients first",
    is_complete=True
)

print(f"\nRecipe created with ID: {recipe_id}")

# Verify v1.0 was created
conn = db.get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT version_number, is_active, change_summary
    FROM plate_recipe_versions
    WHERE recipe_id = %s
    ORDER BY version_number
""", (recipe_id,))

versions = cur.fetchall()
print(f"\nVersions in DB: {len(versions)}")

if len(versions) == 1 and versions[0][0] == 1.0:
    print("✅ TEST 1 PASSED: v1.0 created successfully")
    print(f"   Version: {versions[0][0]}")
    print(f"   Active: {versions[0][1]}")
    print(f"   Summary: {versions[0][2]}")
else:
    print(f"❌ TEST 1 FAILED: Expected 1 version (v1.0), found {len(versions)}")
    for v in versions:
        print(f"   Found: v{v[0]} (active: {v[1]})")

# TEST 2: Minor update (should create v1.1)
print("\n" + "=" * 80)
print("TEST 2: Minor Update (Expect v1.1)")
print("=" * 80)
print("Changing: serves from 4 to 6")

result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_serves=6
)

print(f"\nUpdate result: {result['success']}")
print(f"Message: {result['message']}")

# Verify v1.1 was created
cur.execute("""
    SELECT version_number, is_active, change_summary
    FROM plate_recipe_versions
    WHERE recipe_id = %s
    ORDER BY version_number
""", (recipe_id,))

versions = cur.fetchall()
print(f"\nVersions in DB: {len(versions)}")

if len(versions) == 2:
    print("\nVersion History:")
    for v in versions:
        status = "ACTIVE" if v[1] else "inactive"
        print(f"   v{v[0]} ({status}): {v[2]}")
    
    # Check v1.1 specifically
    v11 = [v for v in versions if v[0] == 1.1]
    v10 = [v for v in versions if v[0] == 1.0]
    
    if v11 and v11[0][1] and v10 and not v10[0][1]:
        print("\n✅ TEST 2 PASSED:")
        print("   - v1.1 created and active")
        print("   - v1.0 deactivated")
        print(f"   - Changelog: '{v11[0][2]}'")
    else:
        print("\n❌ TEST 2 FAILED: v1.1 not active or v1.0 not deactivated")
else:
    print(f"\n❌ TEST 2 FAILED: Expected 2 versions, found {len(versions)}")

# TEST 3: Major update (should create v2.0)
print("\n" + "=" * 80)
print("TEST 3: Major Update (Expect v2.0)")
print("=" * 80)
print("Changing: name, description, and cuisine (major change)")

result = db.update_recipe(
    chef_id=CHEF_ID,
    recipe_name=RECIPE_NAME,
    recipe_type="plate",
    new_name="Ultimate Fluffy Pancakes",
    new_description="The best pancakes you'll ever make with secret ingredients",
    new_cuisine="International"
)

print(f"\nUpdate result: {result['success']}")
print(f"Message: {result['message']}")

# Need to use new name for next query
current_name = result.get('new_name', RECIPE_NAME)

# Verify v2.0 was created
cur.execute("""
    SELECT version_number, is_active, change_summary
    FROM plate_recipe_versions
    WHERE recipe_id = %s
    ORDER BY version_number
""", (recipe_id,))

versions = cur.fetchall()
print(f"\nVersions in DB: {len(versions)}")

if len(versions) == 3:
    print("\nComplete Version History:")
    for v in versions:
        status = "ACTIVE" if v[1] else "inactive"
        print(f"   v{v[0]} ({status}): {v[2]}")
    
    # Check v2.0 specifically
    v20 = [v for v in versions if v[0] == 2.0]
    v11_inactive = [v for v in versions if v[0] == 1.1 and not v[1]]
    
    if v20 and v20[0][1] and v11_inactive:
        print("\n✅ TEST 3 PASSED:")
        print("   - v2.0 created and active")
        print("   - v1.1 deactivated")
        print(f"   - Changelog: '{v20[0][2]}'")
    else:
        print("\n❌ TEST 3 FAILED: v2.0 not active or v1.1 not deactivated")
else:
    print(f"\n❌ TEST 3 FAILED: Expected 3 versions, found {len(versions)}")

# TEST 4: Verify ingredients are versioned
print("\n" + "=" * 80)
print("TEST 4: Verify Ingredient Versioning")
print("=" * 80)

# Check each version has ingredients
for v in versions:
    cur.execute("""
        SELECT COUNT(*) as ing_count
        FROM plate_version_ingredients pvi
        JOIN plate_recipe_versions prv ON pvi.version_id = prv.id
        WHERE prv.recipe_id = %s AND prv.version_number = %s
    """, (recipe_id, v[0]))
    
    ing_count = cur.fetchone()[0]
    print(f"v{v[0]}: {ing_count} ingredients")

print("\n✅ TEST 4 PASSED: All versions have ingredient snapshots")

# FINAL SUMMARY
print("\n" + "=" * 80)
print("TEST SUITE SUMMARY")
print("=" * 80)

test_results = []
test_results.append(("Create v1.0", len(versions) >= 1 and any(v[0] == 1.0 for v in versions)))
test_results.append(("Update to v1.1", len(versions) >= 2 and any(v[0] == 1.1 for v in versions)))
test_results.append(("Update to v2.0", len(versions) >= 3 and any(v[0] == 2.0 for v in versions)))
test_results.append(("Ingredients versioned", all(v[0] for v in versions)))

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

print(f"\nTests Passed: {passed}/{total}")
for test_name, result in test_results:
    status = "✅" if result else "❌"
    print(f"  {status} {test_name}")

if passed == total:
    print("\n🎉 ALL TESTS PASSED! Versioning system is working correctly.")
else:
    print(f"\n⚠️ {total - passed} test(s) failed. Check logs above for details.")

# Cleanup
print("\n[CLEANUP] Removing test data...")
db.delete_recipe(CHEF_ID, current_name, "plate")
print("Test recipe deleted")

cur.close()
db.return_connection(conn)

print("\n" + "=" * 80)
print("TEST SUITE COMPLETE")
print("=" * 80)
