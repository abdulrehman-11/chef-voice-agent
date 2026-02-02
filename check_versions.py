"""Check if versions were created successfully"""
import sys
sys.path.append('backend')
import database as db

conn = db.get_connection()
cur = conn.cursor()

# Count total versions
cur.execute("SELECT COUNT(*) FROM plate_recipe_versions")
total = cur.fetchone()[0]

print(f"Total plate recipe versions in DB: {total}")

if total > 0:
    # Show recent versions
    cur.execute("""
        SELECT 
            pr.name,
            prv.version_number,
            prv.is_active,
            prv.change_summary,
            prv.created_at
        FROM plate_recipe_versions prv
        JOIN plate_recipes pr ON prv.recipe_id = pr.id
        ORDER BY prv.created_at DESC
        LIMIT 5
    """)
    
    print("\nRecent versions:")
    for row in cur.fetchall():
        name, ver_num, is_active, summary, created = row
        status = "ACTIVE" if is_active else "inactive"
        print(f"  {name} v{ver_num} ({status}): {summary}")
        print(f"    Created: {created}")
    
    print("\nVERSIONING IS WORKING!")
else:
    print("\nNO VERSIONS FOUND - Still failing")

cur.close()
db.return_connection(conn)
