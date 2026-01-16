"""
Script to insert intermediate function tools into main.py
"""

# Read the tools to insert
with open('backend/main_intermediate_tools.py', 'r', encoding='utf-8') as f:
    tools_code = f.read()

# Read main.py
with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find insertion point (line 127, after send_recipe_event method)
insert_idx = 127  # 0-indexed, so this is line 128 in the file

# Insert the tools
new_lines = (
    lines[:insert_idx] +
    ['\n', '    # ============ INTERMEDIATE FUNCTION TOOLS FOR LIVE RECIPE BUILDING ============\n', '\n'] +
    [('   ' + line) if line.strip() and not line.startswith(' ') else line for line in tools_code.split('\n')] +
    ['\n', '    # ============ END INTERMEDIATE TOOLS ============\n', '\n'] +
    lines[insert_idx:]
)

# Write back
with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Successfully inserted intermediate tools into main.py")
print(f"Inserted at line {insert_idx + 1}")
print(f"Added {len(tools_code.split(chr(10)))} lines of code")
