"""
Check database connection and existing data
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def check_database():
    """Check database tables and data"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("=" * 60)
        print("  DATABASE CONNECTION: SUCCESS ✅")
        print("=" * 60)
        
        # Check tables exist
        print("\n📋 CHECKING TABLES...")
        tables = ['ingredients', 'plate_recipes', 'batch_recipes', 'plate_ingredients', 'batch_ingredients']
        
        for table in tables:
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                );
            """)
            exists = cur.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"   {status} {table}")
        
        # Count records
        print("\n📊 RECORD COUNTS...")
        
        cur.execute("SELECT COUNT(*) FROM ingredients;")
        ing_count = cur.fetchone()[0]
        print(f"   Ingredients: {ing_count}")
        
        cur.execute("SELECT COUNT(*) FROM plate_recipes;")
        plate_count = cur.fetchone()[0]
        print(f"   Plate Recipes: {plate_count}")
        
        cur.execute("SELECT COUNT(*) FROM batch_recipes;")
        batch_count = cur.fetchone()[0]
        print(f"   Batch Recipes: {batch_count}")
        
        cur.execute("SELECT COUNT(*) FROM plate_ingredients;")
        plate_ing_count = cur.fetchone()[0]
        print(f"   Plate-Ingredient Links: {plate_ing_count}")
        
        # Show sample recipes
        print("\n🍽️  SAMPLE RECIPES (first 10)...")
        cur.execute("""
            SELECT name, cuisine, category FROM plate_recipes 
            ORDER BY name
            LIMIT 10;
        """)
        recipes = cur.fetchall()
        for name, cuisine, category in recipes:
            print(f"   - {name} ({cuisine} - {category})")
        
        print("\n" + "=" * 60)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ DATABASE ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
