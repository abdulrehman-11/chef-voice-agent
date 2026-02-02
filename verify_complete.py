"""
Complete Verification: Database + Google Sheets
Check if "Butter Chicken" recipe with version 1.1 exists
"""
import sys
sys.path.append('backend')

import database as db
from datetime import datetime

print("=" * 70)
print("🔍 COMPLETE VERIFICATION: DATABASE + GOOGLE SHEETS")
print("=" * 70)

conn = db.get_connection()
cur = conn.cursor()

# ========== PART 1: DATABASE CHECK ==========
print("\n" + "=" * 70)
print("📊 PART 1: DATABASE VERIFICATION")
print("=" * 70)

# 1. Find ALL recipes with "Butter Chicken" in name
print("\n1️⃣ Searching for 'Butter Chicken' recipes...")
cur.execute("""
    SELECT id, name, chef_id, created_at, updated_at
    FROM plate_recipes
    WHERE LOWER(name) LIKE '%butter%chicken%'
    ORDER BY created_at DESC
""")

recipes = cur.fetchall()
print(f"\n📋 Found {len(recipes)} recipe(s) matching 'Butter Chicken':")

if not recipes:
    print("   ❌ NO RECIPES FOUND")
    print("\n🎯 VERDICT: AI is hallucinating - recipe doesn't exist!")
    cur.close()
    db.return_connection(conn)
    exit()

for recipe in recipes:
    recipe_id, name, chef_id, created_at, updated_at = recipe
    print(f"\n   Recipe: {name}")
    print(f"   - ID: {recipe_id}")
    print(f"   - Chef: {chef_id}")
    print(f"   - Created: {created_at}")
    print(f"   - Updated: {updated_at}")
    
    # Check versions for this recipe
    print(f"\n   🔍 Checking versions for '{name}'...")
    cur.execute("""
        SELECT 
            id, version_number, is_active, created_at, 
            created_by, change_summary
        FROM plate_recipe_versions
        WHERE recipe_id = %s
        ORDER BY version_number ASC
    """, (recipe_id,))
    
    versions = cur.fetchall()
    
    if not versions:
        print(f"   ❌ NO VERSIONS FOUND for this recipe!")
        print(f"      This means versioning FAILED during save")
    else:
        print(f"   ✅ Found {len(versions)} version(s):")
        for ver in versions:
            ver_id, ver_num, is_active, ver_created, created_by, change_summary = ver
            status = "🟢 ACTIVE" if is_active else "⚫ INACTIVE"
            print(f"\n      Version {ver_num} {status}")
            print(f"      - Created: {ver_created}")
            print(f"      - Created by: {created_by}")
            print(f"      - Change: {change_summary}")
            
            # Check ingredients for this version
            cur.execute("""
                SELECT i.name, pvi.quantity, pvi.unit
                FROM plate_version_ingredients pvi
                JOIN ingredients i ON pvi.ingredient_id = i.id
                WHERE pvi.version_id = %s
                ORDER BY i.name
            """, (ver_id,))
            
            ing_list = cur.fetchall()
            if ing_list:
                print(f"      - Ingredients ({len(ing_list)}):")
                for ing_name, qty, unit in ing_list[:5]:  # Show first 5
                    print(f"         • {qty} {unit} {ing_name}")
                if len(ing_list) > 5:
                    print(f"         ... and {len(ing_list) - 5} more")

print("\n" + "=" * 70)
print("📊 PART 2: GOOGLE SHEETS VERIFICATION")
print("=" * 70)

# Check if Google Sheets is enabled
try:
    import google_sheets
    SHEETS_ENABLED = True
    print("\n✅ Google Sheets integration is enabled")
    
    # Get spreadsheet ID
    import os
    from dotenv import load_dotenv
    load_dotenv()
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    print(f"📄 Spreadsheet ID: {spreadsheet_id}")
    
    # Try to read plate recipes sheet
    try:
        from google_sheets import get_service
        service = get_service()
        
        # Read from "Plate Recipes" sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Plate Recipes!A:K'  # Assuming columns A-K
        ).execute()
        
        values = result.get('values', [])
        print(f"\n📊 Found {len(values)} rows in 'Plate Recipes' sheet")
        
        if values:
            # Header row
            headers = values[0] if values else []
            print(f"\n   Headers: {', '.join(headers)}")
            
            # Find Butter Chicken
            butter_chicken_rows = []
            for i, row in enumerate(values[1:], start=2):  # Skip header
                if len(row) > 1 and 'butter' in row[1].lower() and 'chicken' in row[1].lower():
                    butter_chicken_rows.append((i, row))
            
            if butter_chicken_rows:
                print(f"\n   ✅ Found {len(butter_chicken_rows)} 'Butter Chicken' entries:")
                for row_num, row in butter_chicken_rows:
                    recipe_id = row[0] if len(row) > 0 else "N/A"
                    name = row[1] if len(row) > 1 else "N/A"
                    serves = row[3] if len(row) > 3 else "N/A"
                    cuisine = row[5] if len(row) > 5 else "N/A"
                    print(f"\n      Row {row_num}:")
                    print(f"      - ID: {recipe_id}")
                    print(f"      - Name: {name}")
                    print(f"      - Serves: {serves}")
                    print(f"      - Cuisine: {cuisine}")
            else:
                print(f"\n   ❌ NO 'Butter Chicken' found in Google Sheets")
        else:
            print("\n   ⚠️ Sheet is empty")
            
    except Exception as sheets_error:
        print(f"\n   ❌ Error reading Google Sheets: {sheets_error}")
        print(f"      This might be a permissions issue or invalid spreadsheet ID")
        
except ImportError:
    print("\n⚠️ Google Sheets integration is NOT available")
    print("   (google_sheets.py not imported or dependencies missing)")

# ========== FINAL VERDICT ==========
print("\n" + "=" * 70)
print("🎯 FINAL VERDICT:")
print("=" * 70)

if recipes:
    recipe_name = recipes[0][1]
    print(f"\n✅ Recipe '{recipe_name}' EXISTS in database")
    
    # Check versions
    cur.execute("""
        SELECT COUNT(*) FROM plate_recipe_versions 
        WHERE recipe_id = %s
    """, (recipes[0][0],))
    version_count = cur.fetchone()[0]
    
    if version_count == 0:
        print(f"❌ BUT: NO VERSIONS CREATED")
        print(f"   AI's claim about 'version 1.1' is FABRICATED")
        print(f"   Versioning code is NOT working!")
    elif version_count == 1:
        print(f"⚠️ PARTIAL: Only v1.0 exists (initial save)")
        print(f"   AI's claim about 'version 1.1' is FALSE")
        print(f"   Update didn't create new version")
    elif version_count >= 2:
        print(f"✅ SUCCESS: {version_count} versions exist!")
        print(f"   Versioning is WORKING correctly")
        # Check if 1.1 specifically exists
        cur.execute("""
            SELECT version_number, is_active 
            FROM plate_recipe_versions 
            WHERE recipe_id = %s AND version_number = 1.1
        """, (recipes[0][0],))
        v11 = cur.fetchone()
        if v11:
            print(f"   ✅ Version 1.1 CONFIRMED (Active: {v11[1]})")
        else:
            print(f"   ⚠️ Version 1.1 NOT FOUND (AI may be hallucinating specific version number)")
else:
    print(f"\n❌ NO 'Butter Chicken' recipe found")
    print(f"   AI is completely hallucinating!")

cur.close()
db.return_connection(conn)

print("\n" + "=" * 70)
