"""
Seed Database with Dummy Data for Testing
Run with: python seed_data.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import database as db

# Chef ID for test data - MUST match what agent uses!
# In console mode, the agent uses "mock_user" as the participant identity
TEST_CHEF_ID = "mock_user"



def seed_data():
    """Insert dummy data for testing"""
    
    print("🌱 Seeding database with test data...")
    print("=" * 60)
    
    # ========== BATCH RECIPES ==========
    
    # 1. Tomato Sauce Base
    print("\n📦 Creating Batch Recipes...")
    
    tomato_sauce_id = db.save_batch_recipe(
        chef_id=TEST_CHEF_ID,
        name="Tomato Sauce Base",
        description="Classic Italian tomato sauce for pasta and pizza",
        yield_quantity=5,
        yield_unit="liters",
        prep_time_minutes=15,
        cook_time_minutes=60,
        temperature=90,
        temperature_unit="C",
        equipment=["Large pot", "Wooden spoon", "Blender"],
        instructions="Saute garlic and onions. Add tomatoes. Simmer for 1 hour. Blend until smooth.",
        ingredients=[
            {"name": "Roma Tomatoes", "quantity": 3, "unit": "kg", "preparation_notes": "roughly chopped"},
            {"name": "Garlic", "quantity": 50, "unit": "grams", "preparation_notes": "minced"},
            {"name": "Onions", "quantity": 500, "unit": "grams", "preparation_notes": "diced"},
            {"name": "Olive Oil", "quantity": 100, "unit": "ml"},
            {"name": "Salt", "quantity": 30, "unit": "grams"},
            {"name": "Basil", "quantity": 50, "unit": "grams", "preparation_notes": "fresh, chopped"},
        ],
        notes="Can be stored refrigerated for 1 week or frozen for 3 months",
        is_complete=True
    )
    print(f"  ✅ Tomato Sauce Base (ID: {tomato_sauce_id})")
    
    # 2. Chicken Stock
    chicken_stock_id = db.save_batch_recipe(
        chef_id=TEST_CHEF_ID,
        name="Chicken Stock",
        description="Rich homemade chicken stock for soups and sauces",
        yield_quantity=10,
        yield_unit="liters",
        prep_time_minutes=20,
        cook_time_minutes=180,
        temperature=85,
        temperature_unit="C",
        equipment=["Stock pot", "Strainer", "Ladle"],
        instructions="Roast bones. Add vegetables and water. Simmer 3 hours. Strain and cool.",
        ingredients=[
            {"name": "Chicken Bones", "quantity": 3, "unit": "kg"},
            {"name": "Carrots", "quantity": 500, "unit": "grams", "preparation_notes": "roughly chopped"},
            {"name": "Celery", "quantity": 300, "unit": "grams", "preparation_notes": "roughly chopped"},
            {"name": "Onions", "quantity": 400, "unit": "grams", "preparation_notes": "quartered"},
            {"name": "Bay Leaves", "quantity": 5, "unit": "pieces"},
            {"name": "Black Peppercorns", "quantity": 10, "unit": "grams"},
            {"name": "Water", "quantity": 12, "unit": "liters"},
        ],
        notes="Reduce by half for demi-glace",
        is_complete=True
    )
    print(f"  ✅ Chicken Stock (ID: {chicken_stock_id})")
    
    # 3. Raita
    raita_id = db.save_batch_recipe(
        chef_id=TEST_CHEF_ID,
        name="Raita",
        description="Cool yogurt-based Indian condiment",
        yield_quantity=2,
        yield_unit="liters",
        prep_time_minutes=10,
        cook_time_minutes=0,
        ingredients=[
            {"name": "Yogurt", "quantity": 1.5, "unit": "kg", "preparation_notes": "whisked smooth"},
            {"name": "Cucumber", "quantity": 300, "unit": "grams", "preparation_notes": "grated and squeezed"},
            {"name": "Cumin Powder", "quantity": 10, "unit": "grams", "preparation_notes": "roasted"},
            {"name": "Salt", "quantity": 15, "unit": "grams"},
            {"name": "Mint", "quantity": 30, "unit": "grams", "preparation_notes": "finely chopped"},
        ],
        notes="Serve chilled. Best made fresh.",
        is_complete=True
    )
    print(f"  ✅ Raita (ID: {raita_id})")
    
    # 4. Biryani Rice (partially complete)
    biryani_rice_id = db.save_batch_recipe(
        chef_id=TEST_CHEF_ID,
        name="Biryani Rice Layer",
        description="Saffron-infused basmati rice for layered biryani",
        yield_quantity=5,
        yield_unit="kg",
        prep_time_minutes=30,
        cook_time_minutes=20,
        temperature=100,
        temperature_unit="C",
        ingredients=[
            {"name": "Basmati Rice", "quantity": 3, "unit": "kg", "preparation_notes": "soaked 30 mins"},
            {"name": "Saffron", "quantity": 2, "unit": "grams", "preparation_notes": "dissolved in warm milk"},
            {"name": "Ghee", "quantity": 200, "unit": "grams"},
            {"name": "Whole Spices", "quantity": 50, "unit": "grams", "preparation_notes": "cardamom, cloves, cinnamon"},
            {"name": "Salt", "quantity": 40, "unit": "grams"},
        ],
        notes="Rice should be 70% cooked before layering",
        is_complete=True
    )
    print(f"  ✅ Biryani Rice Layer (ID: {biryani_rice_id})")
    
    # ========== PLATE RECIPES ==========
    
    print("\n🍽️ Creating Plate Recipes...")
    
    # 1. Chicken Biryani
    biryani_id = db.save_plate_recipe(
        chef_id=TEST_CHEF_ID,
        name="Hyderabadi Chicken Biryani",
        description="Aromatic layered rice dish with spiced chicken",
        serves=10,
        category="main",
        cuisine="Indian",
        plating_instructions="250g rice per plate, 100g chicken on top, drizzle of saffron ghee",
        garnish="Fried onions, fresh mint, lemon wedge",
        presentation_notes="Serve in copper handi or on a large platter. Rice should be fluffy with visible saffron strands.",
        prep_time_minutes=45,
        cook_time_minutes=60,
        difficulty="hard",
        ingredients=[
            {"name": "Chicken", "quantity": 1, "unit": "kg", "preparation_notes": "cut into 8 pieces, marinated"},
            {"name": "Fried Onions", "quantity": 100, "unit": "grams", "is_garnish": True},
            {"name": "Mint Leaves", "quantity": 20, "unit": "grams", "is_garnish": True},
        ],
        notes="Serve with raita on the side. Should be a bit spicier than usual.",
        is_complete=True
    )
    print(f"  ✅ Hyderabadi Chicken Biryani (ID: {biryani_id})")
    
    # 2. Spaghetti Marinara
    marinara_id = db.save_plate_recipe(
        chef_id=TEST_CHEF_ID,
        name="Spaghetti Marinara",
        description="Classic Italian pasta with tomato sauce",
        serves=4,
        category="main",
        cuisine="Italian",
        plating_instructions="Twirl 150g pasta in center of plate, ladle 100ml sauce on top",
        garnish="Fresh basil leaves, grated parmesan",
        presentation_notes="Use white plate for contrast. Basil should be bright green.",
        prep_time_minutes=10,
        cook_time_minutes=15,
        difficulty="easy",
        ingredients=[
            {"name": "Spaghetti", "quantity": 600, "unit": "grams"},
            {"name": "Parmesan", "quantity": 50, "unit": "grams", "preparation_notes": "freshly grated", "is_garnish": True},
            {"name": "Basil", "quantity": 20, "unit": "grams", "is_garnish": True},
        ],
        notes="Uses Tomato Sauce Base batch recipe",
        is_complete=True
    )
    print(f"  ✅ Spaghetti Marinara (ID: {marinara_id})")
    
    # 3. Butter Chicken
    butter_chicken_id = db.save_plate_recipe(
        chef_id=TEST_CHEF_ID,
        name="Butter Chicken",
        description="Creamy tomato-based chicken curry",
        serves=6,
        category="main",
        cuisine="Indian",
        plating_instructions="200g curry in center, rice on side, naan on opposite side",
        garnish="Fresh cream swirl, coriander leaves",
        presentation_notes="Cream should form a decorative spiral on top",
        prep_time_minutes=30,
        cook_time_minutes=45,
        difficulty="medium",
        ingredients=[
            {"name": "Chicken Breast", "quantity": 800, "unit": "grams", "preparation_notes": "cubed, marinated"},
            {"name": "Heavy Cream", "quantity": 200, "unit": "ml"},
            {"name": "Butter", "quantity": 100, "unit": "grams"},
            {"name": "Kashmiri Chili", "quantity": 30, "unit": "grams"},
            {"name": "Garam Masala", "quantity": 20, "unit": "grams"},
        ],
        notes="Can use Tomato Sauce Base as foundation",
        is_complete=True
    )
    print(f"  ✅ Butter Chicken (ID: {butter_chicken_id})")
    
    # 4. Test incomplete recipe
    incomplete_id = db.save_plate_recipe(
        chef_id=TEST_CHEF_ID,
        name="Pasta Primavera",
        description="Spring vegetable pasta - work in progress",
        serves=4,
        category="main",
        cuisine="Italian",
        is_complete=False  # Incomplete!
    )
    print(f"  ✅ Pasta Primavera [INCOMPLETE] (ID: {incomplete_id})")
    
    # ========== SUMMARY ==========
    
    print("\n" + "=" * 60)
    print("✅ Seeding complete!")
    print("=" * 60)
    print(f"\n📍 Test Chef ID: {TEST_CHEF_ID}")
    print("\nCreated:")
    print(f"  • 4 Batch Recipes (sauces, stocks, components)")
    print(f"  • 4 Plate Recipes (final dishes)")
    print("\nYou can now test with:")
    print('  "Find my chicken biryani recipe"')
    print('  "What batch recipes do I have?"')
    print('  "Show me the tomato sauce recipe"')
    print('  "I want to create a new dal recipe"')


if __name__ == "__main__":
    seed_data()
