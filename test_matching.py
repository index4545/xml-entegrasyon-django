import re
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from integrations.services import TrendyolService

def parse_measurement(value_str):
    """
    Parses a measurement string (e.g. '3,3 LT', '1500 ml') and returns the value in a standard unit (e.g. Liters).
    Returns None if parsing fails.
    """
    if not value_str:
        return None
        
    value_str = str(value_str).replace('İ', 'i').replace('I', 'ı').lower()
    
    # Determine multiplier based on unit
    multiplier = 1.0
    if 'ml' in value_str or 'cc' in value_str:
        multiplier = 0.001 # Convert ml/cc to Liters
    elif 'lt' in value_str or 'litre' in value_str or 'l' in value_str:
        multiplier = 1.0
    
    # Extract numeric part
    # Remove everything except digits, comma, dot
    num_str = re.sub(r'[^\d,.]', '', value_str)
    if not num_str:
        return None
        
    try:
        # Handle 1.000,50 vs 1,5 formats
        # If comma is present and looks like decimal separator (e.g. 1,5 or 3,3)
        if ',' in num_str:
            if '.' in num_str:
                # Both present (e.g. 1.000,50) -> remove dot, replace comma
                num_str = num_str.replace('.', '').replace(',', '.')
            else:
                # Only comma -> replace with dot
                num_str = num_str.replace(',', '.')
        
        val = float(num_str)
        return val * multiplier
    except:
        return None

def test_logic():
    # 1. Fetch real allowed values
    service = TrendyolService(user=django.contrib.auth.models.User.objects.first())
    cat_id = 2412
    print(f"Fetching attributes for Category {cat_id}...")
    resp = service.get_category_attributes(cat_id)
    
    allowed_values = []
    for attr in resp.get('categoryAttributes', []):
        if attr['attribute']['id'] == 43: # Hacim
            allowed_values = attr.get('attributeValues', [])
            break
            
    print(f"Found {len(allowed_values)} allowed values for Hacim.")
    
    # 2. Test Cases
    test_cases = ['1,5 LT', '1,6 LT', '3,3 LT', '350 ML']
    
    for test_val in test_cases:
        print(f"\nTesting: '{test_val}'")
        
        attr_val = test_val
        
        # Logic from views.py
        if attr_val and not str(attr_val).isdigit() and allowed_values:
            attr_val_original = attr_val
            
            # ... (skipping exact match loop for brevity, focusing on proximity) ...
            
            # 3. Numeric Proximity Match
            if not str(attr_val).isdigit():
                xml_val_parsed = parse_measurement(str(attr_val_original))
                print(f"  Parsed XML Value: {xml_val_parsed}")
                
                if xml_val_parsed is not None:
                    best_match_id = None
                    best_match_name = None
                    min_diff = float('inf')
                    
                    for av in allowed_values:
                        av_parsed = parse_measurement(av['name'])
                        if av_parsed is not None:
                            diff = abs(xml_val_parsed - av_parsed)
                            if diff < min_diff:
                                min_diff = diff
                                best_match_id = av['id']
                                best_match_name = av['name']
                    
                    print(f"  Best Match: {best_match_name} (ID: {best_match_id}) - Diff: {min_diff}")
                    
                    if best_match_id and min_diff <= 0.1:
                        attr_val = best_match_id
                        print(f"  MATCHED! New attr_val: {attr_val}")
                    else:
                        print(f"  NO MATCH (Diff > 0.1)")
        
        print(f"Final Result: {attr_val}")

if __name__ == "__main__":
    test_logic()
