"""
Seed database with British and American famous dishes
Clears all existing data and populates with curated English cuisine
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')

# Famous British and American dishes
DISHES = [
    # British Classics
    {
        "type": "plate",
        "name": "Fish and Chips",
        "serves": 4,
        "description": "Classic British dish of battered fish with chunky chips",
        "plating_instructions": "Place fish fillet on plate, pile chips alongside, add mushy peas, lemon wedge, and tartar sauce",
        "category": "main",
        "cuisine": "British",
        "notes": "Best with cod or haddock. Serve with malt vinegar",
        "ingredients": [
            {"name": "Cod Fillet", "quantity": "200", "unit": "grams", "preparation_notes": "boneless"},
            {"name": "Potatoes", "quantity": "300", "unit": "grams", "preparation_notes": "cut into thick chips"},
            {"name": "Beer Batter", "quantity": "150", "unit": "ml"},
            {"name": "Mushy Peas", "quantity": "100", "unit": "grams"},
            {"name": "Lemon", "quantity": "1", "unit": "wedge", "is_garnish": True}
        ]
    },
    {
        "type": "plate",
        "name": "Shepherd's Pie",
        "serves": 6,
        "description": "Traditional British comfort food with minced lamb and mashed potato topping",
        "plating_instructions": "Scoop generous portion onto plate, ensure crispy potato topping is visible",
        "category": "main",
        "cuisine": "British",
        "notes": "Use beef for Cottage Pie variation",
        "ingredients": [
            {"name": "Ground Lamb", "quantity": "500", "unit": "grams"},
            {"name": "Potatoes", "quantity": "1", "unit": "kg", "preparation_notes": "mashed"},
            {"name": "Carrots", "quantity": "2", "unit": "pieces", "preparation_notes": "diced"},
            {"name": "Onions", "quantity": "1", "unit": "large", "preparation_notes": "diced"},
            {"name": "Beef Stock", "quantity": "300", "unit": "ml"},
            {"name": "Worcestershire Sauce", "quantity": "2", "unit": "tbsp"}
        ]
    },
    {
        "type": "plate",
        "name": "Bangers and Mash",
        "serves": 4,
        "description": "British sausages with creamy mashed potatoes and onion gravy",
        "plating_instructions": "Mound mashed potato in center, place sausages on top, pour gravy over",
        "category": "main",
        "cuisine": "British",
        "notes": "Use Cumberland or pork sausages",
        "ingredients": [
            {"name": "Pork Sausages", "quantity": "8", "unit": "pieces"},
            {"name": "Potatoes", "quantity": "800", "unit": "grams", "preparation_notes": "mashed with butter and cream"},
            {"name": "Onions", "quantity": "2", "unit": "large", "preparation_notes": "sliced"},
            {"name": "Beef Gravy", "quantity": "200", "unit": "ml"},
            {"name": "Butter", "quantity": "50", "unit": "grams"}
        ]
    },
    {
        "type": "plate",
        "name": "Beef Wellington",
        "serves": 6,
        "description": "Luxurious British dish of beef fillet wrapped in mushroom duxelles and puff pastry",
        "plating_instructions": "Slice into portions, fan out on plate with red wine jus, add roasted vegetables",
        "category": "main",
        "cuisine": "British",
        "notes": "Allow to rest 10 minutes before slicing",
        "ingredients": [
            {"name": "Beef Tenderloin", "quantity": "1.2", "unit": "kg"},
            {"name": "Puff Pastry", "quantity": "500", "unit": "grams"},
            {"name": "Mushrooms", "quantity": "400", "unit": "grams", "preparation_notes": "finely chopped for duxelles"},
            {"name": "Pâté", "quantity": "150", "unit": "grams"},
            {"name": "Prosciutto", "quantity": "8", "unit": "slices"},
            {"name": "Egg Yolk", "quantity": "1", "unit": "piece", "preparation_notes": "for egg wash"}
        ]
    },
    {
        "type": "plate",
        "name": "Sunday Roast",
        "serves": 8,
        "description": "Traditional British Sunday dinner with roast beef, Yorkshire pudding and all the trimmings",
        "plating_instructions": "Slice roast beef, add Yorkshire pudding, roast potatoes, vegetables, pour gravy over",
        "category": "main",
        "cuisine": "British",
        "notes": "Serve with horseradish cream",
        "ingredients": [
            {"name": "Beef Rib Roast", "quantity": "2", "unit": "kg"},
            {"name": "Yorkshire Pudding", "quantity": "8", "unit": "pieces"},
            {"name": "Roast Potatoes", "quantity": "1.5", "unit": "kg"},
            {"name": "Carrots", "quantity": "500", "unit": "grams", "preparation_notes": "roasted"},
            {"name": "Green Beans", "quantity": "300", "unit": "grams"},
            {"name": "Beef Gravy", "quantity": "500", "unit": "ml"}
        ]
    },
    
    # American Classics
    {
        "type": "plate",
        "name": "Classic Burger",
        "serves": 4,
        "description": "All-American beef burger with cheese, lettuce, tomato, and special sauce",
        "plating_instructions": "Stack burger on toasted bun, add fries on the side, pickle spear",
        "category": "main",
        "cuisine": "American",
        "notes": "Best with 80/20 ground beef for juiciness",
        "ingredients": [
            {"name": "Ground Beef", "quantity": "800", "unit": "grams"},
            {"name": "Burger Buns", "quantity": "4", "unit": "pieces"},
            {"name": "Cheddar Cheese", "quantity": "4", "unit": "slices"},
            {"name": "Iceberg Lettuce", "quantity": "4", "unit": "leaves"},
            {"name": "Tomato", "quantity": "2", "unit": "sliced"},
            {"name": "Pickles", "quantity": "8", "unit": "slices"},
            {"name": "Special Sauce", "quantity": "100", "unit": "ml"}
        ]
    },
    {
        "type": "plate",
        "name": "BBQ Ribs",
        "serves": 4,
        "description": "Slow-cooked American BBQ pork ribs with tangy sauce",
        "plating_instructions": "Stack ribs on plate, brush with extra BBQ sauce, serve with coleslaw and cornbread",
        "category": "main",
        "cuisine": "American",
        "notes": "Low and slow cooking is key",
        "ingredients": [
            {"name": "Pork Ribs", "quantity": "2", "unit": "kg", "preparation_notes": "St. Louis cut"},
            {"name": "BBQ Rub", "quantity": "50", "unit": "grams"},
            {"name": "BBQ Sauce", "quantity": "300", "unit": "ml"},
            {"name": "Coleslaw", "quantity": "400", "unit": "grams"},
            {"name": "Cornbread", "quantity": "4", "unit": "pieces"}
        ]
    },
    {
        "type": "plate",
        "name": "Mac and Cheese",
        "serves": 6,
        "description": "Creamy American comfort food with three cheeses",
        "plating_instructions": "Scoop into bowl, top with breadcrumb crust, garnish with parsley",
        "category": "main",
        "cuisine": "American",
        "notes": "Can add bacon or jalapeños for variation",
        "ingredients": [
            {"name": "Elbow Macaroni", "quantity": "500", "unit": "grams"},
            {"name": "Cheddar Cheese", "quantity": "300", "unit": "grams", "preparation_notes": "shredded"},
            {"name": "Gruyere Cheese", "quantity": "150", "unit": "grams", "preparation_notes": "shredded"},
            {"name": "Parmesan", "quantity": "100", "unit": "grams", "preparation_notes": "grated"},
            {"name": "Heavy Cream", "quantity": "400", "unit": "ml"},
            {"name": "Butter", "quantity": "60", "unit": "grams"},
            {"name": "Breadcrumbs", "quantity": "50", "unit": "grams", "preparation_notes": "for topping"}
        ]
    },
    {
        "type": "plate",
        "name": "Fried Chicken",
        "serves": 6,
        "description": "Southern-style crispy fried chicken",
        "plating_instructions": "Arrange pieces on platter, serve with mashed potatoes, gravy, and biscuits",
        "category": "main",
        "cuisine": "American",
        "notes": "Buttermilk marinade is essential",
        "ingredients": [
            {"name": "Chicken Pieces", "quantity": "1.5", "unit": "kg", "preparation_notes": "mix of breast, thigh, drumstick"},
            {"name": "Buttermilk", "quantity": "500", "unit": "ml", "preparation_notes": "for marinating"},
            {"name": "All-Purpose Flour", "quantity": "300", "unit": "grams"},
            {"name": "Seasoning Mix", "quantity": "40", "unit": "grams", "preparation_notes": "paprika, garlic powder, cayenne"},
            {"name": "Vegetable Oil", "quantity": "1", "unit": "liter", "preparation_notes": "for frying"}
        ]
    },
    {
        "type": "plate",
        "name": "New York Strip Steak",
        "serves": 2,
        "description": "Classic American steakhouse cut, grilled to perfection",
        "plating_instructions": "Slice steak against grain, fan on plate with garlic butter, add asparagus and potatoes",
        "category": "main",
        "cuisine": "American",
        "notes": "Let rest 5 minutes before slicing",
        "ingredients": [
            {"name": "NY Strip Steak", "quantity": "500", "unit": "grams", "preparation_notes": "2 inch thick"},
            {"name": "Garlic Butter", "quantity": "50", "unit": "grams"},
            {"name": "Asparagus", "quantity": "200", "unit": "grams", "preparation_notes": "grilled"},
            {"name": "Baby Potatoes", "quantity": "300", "unit": "grams", "preparation_notes": "roasted"},
            {"name": "Sea Salt", "quantity": "5", "unit": "grams", "preparation_notes": "flaky"},
            {"name": "Black Pepper", "quantity": "3", "unit": "grams", "preparation_notes": "freshly cracked"}
        ]
    },
    {
        "type": "plate",
        "name": "Clam Chowder",
        "serves": 6,
        "description": "New England style creamy clam soup",
        "plating_instructions": "Ladle into bread bowl, garnish with oyster crackers and parsley",
        "category": "soup",
        "cuisine": "American",
        "notes": "Manhattan style uses tomato base instead of cream",
        "ingredients": [
            {"name": "Fresh Clams", "quantity": "1", "unit": "kg", "preparation_notes": "chopped"},
            {"name": "Potatoes", "quantity": "400", "unit": "grams", "preparation_notes": "diced"},
            {"name": "Bacon", "quantity": "150", "unit": "grams", "preparation_notes": "diced"},
            {"name": "Onion", "quantity": "1", "unit": "large", "preparation_notes": "diced"},
            {"name": "Heavy Cream", "quantity": "300", "unit": "ml"},
            {"name": "Clam Juice", "quantity": "500", "unit": "ml"},
            {"name": "Oyster Crackers", "quantity": "100", "unit": "grams", "is_garnish": True}
        ]
    },
    {
        "type": "plate",
        "name": "Philly Cheesesteak",
        "serves": 4,
        "description": "Philadelphia's iconic sandwich with thinly sliced steak and melted cheese",
        "plating_instructions": "Serve in hoagie roll with chips and pickle",
        "category": "main",
        "cuisine": "American",
        "notes": "Wit or witout onions - that is the question",
        "ingredients": [
            {"name": "Ribeye Steak", "quantity": "600", "unit": "grams", "preparation_notes": "thinly sliced"},
            {"name": "Hoagie Rolls", "quantity": "4", "unit": "pieces"},
            {"name": "Provolone Cheese", "quantity": "8", "unit": "slices"},
            {"name": "Onions", "quantity": "2", "unit": "large", "preparation_notes": "sautéed"},
            {"name": "Bell Peppers", "quantity": "2", "unit": "pieces", "preparation_notes": "sliced and sautéed", "is_optional": True}
        ]
    },
    {
        "type": "plate",
        "name": "Chicken Pot Pie",
        "serves": 6,
        "description": "American comfort food with chicken and vegetables in creamy sauce under flaky crust",
        "plating_instructions": "Cut into portions, serve in bowl to catch sauce",
        "category": "main",
        "cuisine": "American",
        "notes": "Can use puff pastry or pie crust",
        "ingredients": [
            {"name": "Chicken Breast", "quantity": "600", "unit": "grams", "preparation_notes": "cooked and diced"},
            {"name": "Pie Crust", "quantity": "500", "unit": "grams"},
            {"name": "Mixed Vegetables", "quantity": "400", "unit": "grams", "preparation_notes": "peas, carrots, celery"},
            {"name": "Chicken Stock", "quantity": "500", "unit": "ml"},
            {"name": "Heavy Cream", "quantity": "200", "unit": "ml"},
            {"name": "Butter", "quantity": "50", "unit": "grams"}
        ]
    },
    
    # British Desserts
    {
        "type": "plate",
        "name": "Sticky Toffee Pudding",
        "serves": 8,
        "description": "Moist British dessert with dates and warm toffee sauce",
        "plating_instructions": "Place warm pudding on plate, pour toffee sauce over, add vanilla ice cream",
        "category": "dessert",
        "cuisine": "British",
        "notes": "Best served warm",
        "ingredients": [
            {"name": "Dates", "quantity": "200", "unit": "grams", "preparation_notes": "chopped and soaked"},
            {"name": "Self-Raising Flour", "quantity": "175", "unit": "grams"},
            {"name": "Brown Sugar", "quantity": "150", "unit": "grams"},
            {"name": "Butter", "quantity": "50", "unit": "grams"},
            {"name": "Toffee Sauce", "quantity": "300", "unit": "ml"},
            {"name": "Vanilla Ice Cream", "quantity": "400", "unit": "ml", "is_garnish": True}
        ]
    },
    {
        "type": "plate",
        "name": "Apple Crumble",
        "serves": 6,
        "description": "Classic British dessert with baked apples and buttery crumb topping",
        "plating_instructions": "Scoop into bowl, add custard or cream",
        "category": "dessert",
        "cuisine": "British",
        "notes": "Granny Smith apples work best",
        "ingredients": [
            {"name": "Cooking Apples", "quantity": "1", "unit": "kg", "preparation_notes": "peeled and sliced"},
            {"name": "Plain Flour", "quantity": "200", "unit": "grams"},
            {"name": "Butter", "quantity": "100", "unit": "grams", "preparation_notes": "cold and cubed"},
            {"name": "Demerara Sugar", "quantity": "100", "unit": "grams"},
            {"name": "Cinnamon", "quantity": "1", "unit": "tsp"},
            {"name": "Custard", "quantity": "400", "unit": "ml", "is_garnish": True}
        ]
    },
    
    # American Desserts
    {
        "type": "plate",
        "name": "Apple Pie",
        "serves": 8,
        "description": "Classic American dessert with spiced apple filling in flaky crust",
        "plating_instructions": "Slice and serve warm with vanilla ice cream",
        "category": "dessert",
        "cuisine": "American",
        "notes": "As American as... well, apple pie",
        "ingredients": [
            {"name": "Apples", "quantity": "1.2", "unit": "kg", "preparation_notes": "peeled and sliced"},
            {"name": "Pie Crust", "quantity": "600", "unit": "grams", "preparation_notes": "top and bottom"},
            {"name": "Sugar", "quantity": "150", "unit": "grams"},
            {"name": "Cinnamon", "quantity": "2", "unit": "tsp"},
            {"name": "Nutmeg", "quantity": "0.5", "unit": "tsp"},
            {"name": "Vanilla Ice Cream", "quantity": "500", "unit": "ml", "is_garnish": True}
        ]
    },
    {
        "type": "plate",
        "name": "New York Cheesecake",
        "serves": 12,
        "description": "Rich and creamy American-style cheesecake",
        "plating_instructions": "Slice into portions, top with berry compote",
        "category": "dessert",
        "cuisine": "American",
        "notes": "Chill overnight for best results",
        "ingredients": [
            {"name": "Cream Cheese", "quantity": "900", "unit": "grams", "preparation_notes": "room temperature"},
            {"name": "Graham Cracker Crust", "quantity": "300", "unit": "grams"},
            {"name": "Sugar", "quantity": "300", "unit": "grams"},
            {"name": "Eggs", "quantity": "5", "unit": "large"},
            {"name": "Sour Cream", "quantity": "200", "unit": "grams"},
            {"name": "Vanilla Extract", "quantity": "2", "unit": "tsp"},
            {"name": "Berry Compote", "quantity": "300", "unit": "ml", "is_garnish": True}
        ]
    }
]

def clear_database():
    """Clear all existing data from database"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        print("🗑️  Clearing database...")
        
        # Delete in correct order due to foreign keys
        cur.execute("DELETE FROM plate_ingredients;")
        cur.execute("DELETE FROM batch_ingredients;")
        cur.execute("DELETE FROM plate_batches;")
        cur.execute("DELETE FROM batch_recipes;")
        cur.execute("DELETE FROM plate_recipes;")
        cur.execute("DELETE FROM ingredients WHERE chef_id = 'mock_user';")
        cur.execute("DELETE FROM chefs WHERE chef_id != 'mock_user';")  # Keep mock_user
        
        conn.commit()
        print("✅ Database cleared")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error clearing database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()

def seed_dishes():
    """Populate database with British and American dishes"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Ensure mock_user exists in chefs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chefs (
                chef_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255)
            );
        """)
        
        cur.execute("""
            INSERT INTO chefs (chef_id, name, email) 
            VALUES ('mock_user', 'Demo Chef', 'demo@tullia.ai')
            ON CONFLICT (chef_id) DO NOTHING;
        """)
        
        print(f"\n📝 Adding {len(DISHES)} British and American dishes...")
        
        for dish in DISHES:
            print(f"   Adding: {dish['name']} ({dish['cuisine']})...")
            
            if dish['type'] == 'plate':
                # Insert plate recipe
                cur.execute("""
                    INSERT INTO plate_recipes (
                        chef_id, name, serves, description, plating_instructions,
                        notes, category, cuisine, is_complete
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    'mock_user',
                    dish['name'],
                    dish['serves'],
                    dish.get('description'),
                    dish.get('plating_instructions'),
                    dish.get('notes'),
                    dish.get('category'),
                    dish.get('cuisine'),
                    True
                ))
                
                recipe_id = cur.fetchone()[0]
                
                # Add ingredients
                for ing in dish.get('ingredients', []):
                    # First, ensure ingredient exists
                    cur.execute("""
                        INSERT INTO ingredients (chef_id, name, unit)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                    """, ('mock_user', ing['name'], ing.get('unit')))
                    
                    result = cur.fetchone()
                    if result:
                        ing_id = result[0]
                    else:
                        # Ingredient already exists, fetch it
                        cur.execute("""
                            SELECT id FROM ingredients 
                            WHERE chef_id = %s AND name = %s
                            LIMIT 1;
                        """, ('mock_user', ing['name']))
                        ing_id = cur.fetchone()[0]
                    
                    # Link ingredient to plate recipe
                    cur.execute("""
                        INSERT INTO plate_ingredients (
                            plate_recipe_id, ingredient_id, quantity, unit,
                            preparation_notes, is_garnish, is_optional
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        recipe_id,
                        ing_id,
                        ing.get('quantity'),
                        ing.get('unit'),
                        ing.get('preparation_notes'),
                        ing.get('is_garnish', False),
                        ing.get('is_optional', False)
                    ))
                
            else:  # batch recipe
                cur.execute("""
                    INSERT INTO batch_recipes (
                        chef_id, name, yield_quantity, yield_unit, description,
                        notes, category, cuisine, is_complete
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    'mock_user',
                    dish['name'],
                    dish.get('yield_quantity'),
                    dish.get('yield_unit'),
                    dish.get('description'),
                    dish.get('notes'),
                    dish.get('category'),
                    dish.get('cuisine'),
                    True
                ))
                
                recipe_id = cur.fetchone()[0]
                
                # Add ingredients
                for ing in dish.get('ingredients', []):
                    # First, ensure ingredient exists
                    cur.execute("""
                        INSERT INTO ingredients (chef_id, name, unit)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                    """, ('mock_user', ing['name'], ing.get('unit')))
                    
                    result = cur.fetchone()
                    if result:
                        ing_id = result[0]
                    else:
                        # Ingredient already exists, fetch it
                        cur.execute("""
                            SELECT id FROM ingredients 
                            WHERE chef_id = %s AND name = %s
                            LIMIT 1;
                        """, ('mock_user', ing['name']))
                        ing_id = cur.fetchone()[0]
                    
                    # Link ingredient to batch recipe
                    cur.execute("""
                        INSERT INTO batch_ingredients (
                            batch_recipe_id, ingredient_id, quantity, unit,
                            preparation_notes, is_optional
                        ) VALUES (%s, %s, %s, %s, %s, %s);
                    """, (
                        recipe_id,
                        ing_id,
                        ing.get('quantity'),
                        ing.get('unit'),
                        ing.get('preparation_notes'),
                        ing.get('is_optional', False)
                    ))
        
        conn.commit()
        print(f"\n✅ Successfully added {len(DISHES)} dishes to database!")
        print(f"🍽️  Cuisines: British and American")
        print(f"👨‍🍳 Chef: mock_user")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  TULLIA - Database Seed: British & American Cuisine")
    print("=" * 60)
    
    # clear_database()  # Commented out - tables might not exist yet
    seed_dishes()
    
    print("\n" + "=" * 60)
    print("  Database ready for TULLIA!")
    print("=" * 60)
