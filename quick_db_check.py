"""
Quick DB check - Find all recipes and their versions
"""
import sys
sys.path.append('backend')
import database as db

conn = db.get_connection()
cur = conn.cursor()

# Check all plate recipes
print("📋 ALL PLATE RECIPES:")
cur.execute("SELECT id, name, chef_id FROM plate_recipes ORDER BY created_at DESC LIMIT 10")
recipes = cur.fetchall()
print(f"Found {len(recipes)} recipes:")
for r in recipes:
    print(f"  - {r[1]} (ID: {r[0]}, Chef: {r[2]})")

print("\n📦 ALL PLATE RECIPE VERSIONS:")
cur.execute("""
    SELECT 
        prv.recipe_id,
        pr.name,
        prv.version_number,
        prv.is_active,
        prv.change_summary
    FROM plate_recipe_versions prv
    JOIN plate_recipes pr ON prv.recipe_id = pr.id
    ORDER BY pr.name, prv.version_number
""")
versions = cur.fetchall()
print(f"Found {len(versions)} versions:")
for v in versions:
    status = "ACTIVE" if v[3] else "inactive"
    print(f"  - {v[1]} v{v[2]} ({status}): {v[4]}")

cur.close()
db.return_connection(conn)
