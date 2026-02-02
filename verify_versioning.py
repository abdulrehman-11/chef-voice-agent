"""
Database Verification Script - Check Recipe Versioning
Verifies if version 1.1 was actually created for Buttered Chicken
"""
import sys
sys.path.append('backend')

import database as db

print("=" * 60)
print("🔍 VERIFYING RECIPE VERSIONING IN DATABASE")
print("=" * 60)

conn = db.get_connection()
cur = conn.cursor()

# 1. Find Buttered Chicken recipe
print("\n1️⃣ Finding 'Buttered Chicken' recipe...")
cur.execute("""
    SELECT id, name, chef_id, created_at, updated_at
    FROM plate_recipes
    WHERE LOWER(name) LIKE '%buttered chicken%'
    ORDER BY created_at DESC
    LIMIT 1
""")

recipe = cur.fetchone()
if not recipe:
    print("❌ No 'Buttered Chicken' recipe found in plate_recipes table")
    cur.close()
    db.return_connection(conn)
    exit(1)

recipe_id, name, chef_id, created_at, updated_at = recipe
print(f"✅ Found recipe:")
print(f"   ID: {recipe_id}")
print(f"   Name: {name}")
print(f"   Chef: {chef_id}")
print(f"   Created: {created_at}")
print(f"   Updated: {updated_at}")

# 2. Check versions for this recipe
print(f"\n2️⃣ Checking versions for recipe ID {recipe_id}...")
cur.execute("""
    SELECT 
        id,
        version_number,
        is_active,
        created_at,
        created_by,
        change_summary,
        name
    FROM plate_recipe_versions
    WHERE recipe_id = %s
    ORDER BY version_number ASC
""", (recipe_id,))

versions = cur.fetchall()
if not versions:
    print(f"❌ NO VERSIONS FOUND for '{name}'")
    print("   This means versioning was NOT actually created!")
else:
    print(f"✅ Found {len(versions)} version(s):")
    for ver in versions:
        ver_id, ver_num, is_active, ver_created, created_by, change_summary, ver_name = ver
        status = "🟢 ACTIVE" if is_active else "⚫ INACTIVE"
        print(f"\n   Version {ver_num} {status}")
        print(f"   - Version ID: {ver_id}")
        print(f"   - Created: {ver_created}")
        print(f"   - Created by: {created_by}")
        print(f"   - Change: {change_summary}")
        print(f"   - Name: {ver_name}")

# 3. Check ingredients for each version
if versions:
    print(f"\n3️⃣ Checking ingredients for each version...")
    for ver in versions:
        ver_id, ver_num, is_active, _, _, _, _ = ver
        cur.execute("""
            SELECT 
                i.name,
                pvi.quantity,
                pvi.unit
            FROM plate_version_ingredients pvi
            JOIN ingredients i ON pvi.ingredient_id = i.id
            WHERE pvi.version_id = %s
            ORDER BY i.name
        """, (ver_id,))
        
        ingredients = cur.fetchall()
        print(f"\n   📦 Version {ver_num} ingredients ({len(ingredients)} total):")
        for ing_name, qty, unit in ingredients:
            print(f"      • {qty} {unit} {ing_name}")

# 4. Check main recipe ingredients (current state)
print(f"\n4️⃣ Checking current ingredients in main plate_ingredients table...")
cur.execute("""
    SELECT 
        i.name,
        pi.quantity,
        pi.unit
    FROM plate_ingredients pi
    JOIN ingredients i ON pi.ingredient_id = i.id
    WHERE pi.plate_recipe_id = %s
    ORDER BY i.name
""", (recipe_id,))

current_ingredients = cur.fetchall()
print(f"   📦 Current ingredients ({len(current_ingredients)} total):")
for ing_name, qty, unit in current_ingredients:
    print(f"      • {qty} {unit} {ing_name}")

print("\n" + "=" * 60)
print("🎯 VERDICT:")
print("=" * 60)

if len(versions) >= 2:
    print("✅ VERSIONING IS WORKING!")
    print(f"   - {len(versions)} versions exist")
    active_versions = [v for v in versions if v[2]]  # is_active
    if active_versions:
        active_ver = active_versions[0]
        print(f"   - Active version: {active_ver[1]}")
        print(f"   - Change: {active_ver[5]}")
elif len(versions) == 1:
    print("⚠️ PARTIAL SUCCESS:")
    print("   - Only version 1.0 exists (initial save)")
    print("   - Version 1.1 was NOT created")
    print("   - This means update_recipe() is NOT creating new versions yet")
else:
    print("❌ VERSIONING NOT WORKING:")
    print("   - No versions found at all")
    print("   - Auto-versioning on save may have failed")

cur.close()
db.return_connection(conn)
