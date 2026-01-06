"""
Sync existing recipes from PostgreSQL to Google Sheets
Run this once to migrate all existing data
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import google_sheets


def main():
    print("=" * 60)
    print("  Recipe Database → Google Sheets Sync")
    print("=" * 60)
    print()
    
    # Initialize database
    print("1. Connecting to database...")
    db.init_db()
    print("   ✅ Database connected")
    print()
    
    # Initialize Google Sheets
    print("2. Connecting to Google Sheets...")
    if not google_sheets.init_sheets():
        print("   ❌ Failed to connect to Google Sheets")
        print("   Make sure you've shared the sheet with the service account email")
        return
    print("   ✅ Google Sheets connected")
    print()
    
    # Sync all data
    print("3. Syncing recipes to Google Sheets...")
    print("   (This will clear existing sheet data and reload from database)")
    print()
    
    stats = google_sheets.sync_all_from_database(db)
    
    if "error" in stats:
        print(f"   ❌ Sync failed: {stats['error']}")
        return
    
    print()
    print("=" * 60)
    print("  SYNC COMPLETE!")
    print("=" * 60)
    print(f"  • Plate Recipes:  {stats.get('plate_recipes', 0)}")
    print(f"  • Batch Recipes:  {stats.get('batch_recipes', 0)}")
    print(f"  • Ingredients:    {stats.get('ingredients', 0)}")
    print("=" * 60)
    print()
    print("Open your Google Sheet to see the synced data:")
    print(f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')}")


if __name__ == "__main__":
    main()
