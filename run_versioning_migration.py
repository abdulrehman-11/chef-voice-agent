"""
Quick migration runner for versioning tables
Uses backend database connection
"""
import sys
sys.path.append('backend')

import database as db

def run_migration():
    """Execute the versioning migration"""
    print("🔄 Starting versioning migration...")
    
    # Read SQL file
    with open('database/versioning_migration.sql', 'r') as f:
        migration_sql = f.read()
    
    conn = db.get_connection()
    cur = conn.cursor()
    
    try:
        print("📝 Creating version tables...")
        cur.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed!")
        
        # Verify
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%version%'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print("\n✓ Verified tables:")
        for table in tables:
            print(f"  ✓ {table[0]}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        cur.close()
        db.return_connection(conn)

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
