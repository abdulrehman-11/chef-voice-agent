"""Direct DB query - no emojis"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = os.getenv('DATABASE_URL')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Step 1: Check if versioning table exists
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'plate_recipe_versions'
    );
""")
table_exists = cur.fetchone()[0]
print(f"Table 'plate_recipe_versions' exists: {table_exists}")

if not table_exists:
    print("CRITICAL: Versioning table does NOT exist!")
    print("Migration was never run!")
    cur.close()
    conn.close()
    exit()

# Step 2: Find Butter Chicken
cur.execute("""
    SELECT id, name
    FROM plate_recipes
    WHERE LOWER(name) LIKE '%butter%chicken%'
    LIMIT 1
""")

recipe = cur.fetchone()
if recipe:
    recipe_id, name = recipe
    print(f"\nRecipe found: {name}")
    print(f"Recipe ID: {recipe_id}")
    
    # Step 3: Count versions
    cur.execute("""
        SELECT COUNT(*) FROM plate_recipe_versions WHERE recipe_id = %s
    """, (recipe_id,))
    
    version_count = cur.fetchone()[0]
    print(f"Version count: {version_count}")
    
    if version_count == 0:
        print("\nFINDING: Recipe exists but ZERO versions created")
        print("This means versioning code FAILED")
    else:
        # Get version details
        cur.execute("""
            SELECT version_number, is_active, change_summary
            FROM plate_recipe_versions
            WHERE recipe_id = %s
            ORDER BY version_number
        """, (recipe_id,))
        
        versions = cur.fetchall()
        print(f"\nVersions found: {version_count}")
        for v in versions:
            ver_num, is_active, change_summary = v
            status = "ACTIVE" if is_active else "inactive"
            print(f"  v{ver_num} ({status}): {change_summary}")
            
        # Check for v1.1 specifically
        has_v11 = any(v[0] == 1.1 for v in versions)
        if has_v11:
            print("\nVERDICT: Version 1.1 EXISTS - AI claim is TRUE")
        else:
            print(f"\nVERDICT: Version 1.1 NOT FOUND - AI claim is FALSE")
            print(f"Versions present: {[v[0] for v in versions]}")
else:
    print("Recipe NOT found")

cur.close()
conn.close()
