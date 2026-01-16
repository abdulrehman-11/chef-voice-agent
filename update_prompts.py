"""
Script to update prompts.py with live recipe building instructions
"""

# Read prompts.py
with open('backend/prompts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the insertion point (after "**IMPORTANT - Search Flow:**" section)
search_flow_end = content.find('**IMPORTANT - Duplicate Handling:**')

if search_flow_end == -1:
    print("❌ Could not find insertion point")
    exit(1)

# New content to insert
new_section = '''
**CRITICAL - LIVE RECIPE BUILDING:**
When a chef starts describing a recipe, you MUST use these intermediate tools IN REAL-TIME:

1. **As soon as** chef says "I'm making X" → IMMEDIATELY call start_recipe(name="X", recipe_type="plate" or "batch")

2. **When** chef mentions serves/yield/cuisine/etc → call update_recipe_metadata(serves=N, cuisine="X", ...)

3. **For EACH ingredient** mentioned → call add_ingredient(name="X", quantity="N", unit="g")
   - If chef says "500g chicken, 300g rice, 2 onions" you MUST call add_ingredient THREE TIMES
   - Once for chicken, once for rice, once for onions
   - NEVER skip this step!

4. **When** chef describes cooking steps → call add_instruction("step text")

5. **ONLY when** chef says "save it" → call save_plate_recipe() or save_batch_recipe()
   - These will use the data you've built up with previous intermediate tool calls

**MANDATORY - Search Before Claiming:**
- You MUST call search_recipes() FIRST before ever saying "I found..." or "You have..."
- NEVER make assumptions about existing recipes
- Only state facts based on actual search results
- If you haven't searched, you don't know what exists!

'''

# Insert the new section
new_content = content[:search_flow_end] + new_section + content[search_flow_end:]

# Write back
with open('backend/prompts.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Successfully updated prompts.py")
print(f"Added {len(new_section)} characters of instructions")
