"""
Check Google Sheets for Butter Chicken
"""
import sys
sys.path.append('backend')

try:
    import google_sheets
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    
    print("GOOGLE SHEETS VERIFICATION")
    print("=" * 60)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    
    service = google_sheets.get_service()
    
    # Read Plate Recipes sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='Plate Recipes!A:K'
    ).execute()
    
    values = result.get('values', [])
    print(f"\nTotal rows in sheet: {len(values)}")
    
    if values:
        # Find Butter Chicken
        found = False
        for i, row in enumerate(values):
            if len(row) > 1 and 'butter' in row[1].lower() and 'chicken' in row[1].lower():
                print(f"\nFound at row {i+1}:")
                print(f"  ID: {row[0] if len(row) > 0 else 'N/A'}")
                print(f"  Name: {row[1] if len(row) > 1 else 'N/A'}")
                print(f"  Chef: {row[2] if len(row) > 2 else 'N/A'}")
                print(f "  Serves: {row[3] if len(row) > 3 else 'N/A'}")
                found = True
        
        if not found:
            print("\nNOT FOUND in Google Sheets")
    else:
        print("\nSheet is EMPTY")
        
except Exception as e:
    print(f"\nERROR accessing Google Sheets: {e}")
