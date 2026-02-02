"""
Simple verification without emojis
"""
import sys
sys.path.append('backend')
import database as db

conn = db.get_connection()
cur = conn.cursor()

print("DATABASE VERIFICATION FOR BUTTER CHICKEN")
print("=" * 60)

# Find Butter Chicken
cur.execute("""
    SELECT id, name, chef_id, created_at
    FROM plate_recipes
    WHERE LOWER(name) LIKE '%butter%chicken%'
    ORDER BY created_at DESC
""")

recipes = cur.fetchall()
print(f"\nRecipes found: {len(recipes)}")

if recipes:
    for recipe in recipes:
        recipe_id, name, chef_id, created_at = recipe
        print(f"\nRecipe: {name}")
        print(f"ID: {recipe_id}")
        print(f"Chef: {chef_id}")
        print(f"Created: {created_at}")
        
        # Check versions
        cur.execute("""
            SELECT version_number, is_active, change_summary, created_at
            FROM plate_recipe_versions
            WHERE recipe_id = %s
            ORDER BY version_number
        """, (recipe_id,))
        
        versions = cur.fetchall()
        print(f"\nVersions found: {len(versions)}")
        
        if versions:
            for ver in versions:
                ver_num, is_active, change_summary, ver_created = ver
                status = "ACTIVE" if is_active else "inactive"
                print(f"  - Version {ver_num} ({status})")
                print(f"    Created: {ver_created}")
                print(f"    Change: {change_summary}")
        else:
            print("  NO VERSIONS FOUND - Versioning failed!")
            
print("\n" + "=" * 60)
print("VERDICT:")
print("=" * 60)

if not recipes:
    print("FAIL: No Butter Chicken recipe found")
elif not versions:
    print("FAIL: Recipe exists but NO versions created")
    print("AI claim about version 1.1 is FALSE")
else:
    v11 = [v for v in versions if v[0] == 1.1]
    if v11:
        print("SUCCESS: Version 1.1 EXISTS!")
    else:
        print(f"PARTIAL: {len(versions)} versions exist but NOT version 1.1")
        print(f"Versions found: {[v[0] for v in versions]}")

cur.close()
db.return_connection(conn)
