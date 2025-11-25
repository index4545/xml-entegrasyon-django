import pdfplumber
import json

pdf_path = "guncel_trendyol_komisyon_oranlari (1).pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        page = pdf.pages[0]
        tables = page.extract_tables()
        
        if tables:
            print("Found tables on page 1:")
            for i, table in enumerate(tables):
                print(f"Table {i}:")
                # Print first 5 rows
                for row in table[:5]:
                    print(row)
        else:
            print("No tables found on page 1. Extracting text...")
            text = page.extract_text()
            print(text[:500])

except Exception as e:
    print(f"Error: {e}")
