"""
ABSOLUTE VERIFICATION - Check exact DATABASE_URL and query it directly
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load .env
load_dotenv()
db_url = os.getenv('DATABASE_URL')

print("=" * 70)
print("ABSOLUTE DATABASE VERIFICATION")
print("=" * 70)
print(f"\nDATABASE_URL from .env:")
print(f"  {db_url[:50]}..." if len(db_url) > 50 else f"  {db_url}")

# Connect DIRECTLY using this URL
conn = psycopg2.connect(db_url)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n" + "=" * 70)
print("STEP 1: Check if versioning tables exist")
print("=" * 70)

# Check if plate_recipe_versions table exists
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'plate_recipe_versions'
    );
""")
table_exists = cur.fetchone()['exists']
print(f"\nTable 'plate_recipe_versions' exists: {table_exists}")

if not table_exists:
    print("\n❌ VERSIONING TABLES DON'T EXIST!")
    print("   Migration was NEVER run on this database!")
    print("   That's why no versions are being created!")
    cur.close()
    conn.close()
    exit()

print("\n" + "=" * 70)
print("STEP 2: Find Butter Chicken recipe")
print("=" * 70)

cur.execute("""
    SELECT id, name, chef_id, created_at, updated_at
    FROM plate_recipes
    WHERE LOWER(name) LIKE '%butter%chicken%'
    ORDER BY updated_at DESC
    LIMIT 1
""")

recipe = cur.fetchone()
if not recipe:
    print("\n❌ NO Butter Chicken found!")
    cur.close()
    conn.close()
    exit()

print(f"\n✅ Found: {recipe['name']}")
print(f"   ID: {recipe['id']}")
print(f"   Chef: {recipe['chef_id']}")
print(f"   Created: {recipe['created_at']}")
print(f"   Updated: {recipe['updated_at']}")

recipe_id = recipe['id']

print("\n" + "=" * 70)
print("STEP 3: Check ALL versions for this recipe")
print("=" * 70)

cur.execute("""
    SELECT 
        version_number,
        is_active,
        created_at,
        change_summary,
        name as version_name
    FROM plate_recipe_versions
    WHERE recipe_id = %s
    ORDER BY version_number ASC
""", (recipe_id,))

versions = cur.fetchall()

print(f"\nVersions found: {len(versions)}")

if len(versions) == 0:
    print("\n❌ ZERO VERSIONS - This confirms:")
    print("   1. Table exists")
    print("   2. Recipe exists")
    print("   3. But NO versions were created")
    print("   4. The save_plate_recipe() versioning code FAILED")
else:
    print("\n✅ Versions exist:")
    for v in versions:
        status = "ACTIVE" if v['is_active'] else "inactive"
        print(f"\n   v{v['version_number']} ({status})")
        print(f"   Created: {v['created_at']}")
        print(f"   Change: {v['change_summary']}")
        print(f"   Name: {v['version_name']}")

print("\n" + "=" * 70)
print("STEP 4: Check update_recipe logs")
print("=" * 70)

# The backend log shows "UPDATING RECIPE" was called
# But update_recipe() doesn't create versions yet!
print("\nBackend log shows: 'UPDATING RECIPE: butter chicken'")
print("\n⚠️ KEY INSIGHT:")
print("   update_recipe() function does NOT create versions yet!")
print("   I only added versioning to save_plate_recipe()/save_batch_recipe()")
print("   update_recipe() still needs to be modified")

print("\n" + "=" * 70)
print("FINAL VERDICT")
print("=" * 70)

if len(versions) == 0:
    print("\n❌ AI CLAIM IS FALSE")
    print("   Version 1.1 does NOT exist")
    print("\nPossible reasons:")
    print("   1. Recipe was created BEFORE I added versioning code")
    print("   2. Versioning code in save_plate_recipe() failed silently")
    print("   3. update_recipe() doesn't create versions (confirmed)")
else:
    print("\n✅ VERSIONS EXIST")
    if any(v['version_number'] == 1.1 for v in versions):
        print("   ✅ Version 1.1 confirmed!")
    else:
        print(f"   ⚠️ But v1.1 not found. Versions: {[v['version_number'] for v in versions]}")

cur.close()
conn.close()

print("\n" + "=" * 70)
