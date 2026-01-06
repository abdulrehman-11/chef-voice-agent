"""
Database Migration Script
Connects to NeonDB and creates all required tables for the Chef Voice AI Agent.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Execute database migration from schema.sql"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    print("🔄 Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        
        # Read schema file
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        if not os.path.exists(schema_path):
            print(f"❌ ERROR: Schema file not found at {schema_path}")
            sys.exit(1)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("🔄 Executing schema migration...")
        
        # Execute schema
        cursor.execute(schema_sql)
        
        print("✅ Schema migration completed successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   ✓ {table[0]}")
        
        # Verify extensions
        cursor.execute("""
            SELECT extname FROM pg_extension 
            WHERE extname IN ('uuid-ossp', 'pg_trgm')
            ORDER BY extname;
        """)
        
        extensions = cursor.fetchall()
        print(f"\n🔌 Enabled {len(extensions)} extensions:")
        for ext in extensions:
            print(f"   ✓ {ext[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✨ Database setup complete! Ready to use.")
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("   Chef Voice AI Agent - Database Migration")
    print("=" * 60)
    run_migration()
