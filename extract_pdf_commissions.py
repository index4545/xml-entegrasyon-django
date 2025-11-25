import pdfplumber
import json
import re

pdf_path = "guncel_trendyol_komisyon_oranlari (1).pdf"
output_path = "trendyol_commissions.json"

data = []

def parse_percentage(val):
    if not val: return 0.0
    # Remove % and whitespace
    val = val.replace('%', '').strip()
    try:
        return float(val)
    except ValueError:
        return 0.0

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Processing {len(pdf.pages)} pages...")
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if "Bardak" in text:
                print(f"Page {page_num+1} contains 'Bardak'")
                
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if "Bardak" in str(row):
                        print(f"FOUND Bardak in ROW: {row}")

                    # Check if this is a data row
                    # Check if this is a data row
                    # Data rows usually start with a number in column 0
                    col0 = row[0]
                    if not col0:
                        continue
                    
                    # Clean col0 to check if digit
                    col0_clean = str(col0).strip()
                    if not col0_clean.isdigit():
                        # Debug: Print what we are skipping
                        if "Ev & Yaşam" in str(row):
                             print(f"SKIPPED ROW containing 'Ev & Yaşam': {row}")
                        continue
                    
                    # Extract fields
                    # Indices based on inspection:
                    # 1: Kategori
                    # 2: Alt Kategori
                    # 3: Ürün Grubu
                    # 5: Komisyon
                    
                    if len(row) < 6:
                        continue
                    
                    category = row[1] or ""
                    sub_category = row[2] or ""
                    product_group = row[3] or ""
                    commission_str = row[5]
                    
                    # Clean up newlines
                    category = category.replace('\n', ' ').strip()
                    sub_category = sub_category.replace('\n', ' ').strip()
                    product_group = product_group.replace('\n', ' ').strip()
                    
                    # Construct full name
                    parts = [p for p in [category, sub_category, product_group] if p and p != '-']
                    full_name = " > ".join(parts)
                    
                    commission = parse_percentage(commission_str)
                    
                    item = {
                        "name": full_name,
                        "category": category,
                        "sub_category": sub_category,
                        "product_group": product_group,
                        "commission": commission
                    }
                    data.append(item)
            
            if (page_num + 1) % 5 == 0:
                print(f"Processed {page_num + 1} pages...")

    print(f"Extracted {len(data)} items.")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")

except Exception as e:
    print(f"Error: {e}")
