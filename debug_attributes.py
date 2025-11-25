import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

def check_attributes():
    user = User.objects.first()
    service = TrendyolService(user=user)
    cat_id = 2412
    print(f"Fetching attributes for Category {cat_id}...")
    
    resp = service.get_category_attributes(cat_id)
    
    for attr in resp.get('categoryAttributes', []):
        if attr['attribute']['id'] == 43: # Hacim
            print(f"\nAttribute: {attr['attribute']['name']} (ID: 43)")
            print(f"Required: {attr.get('required')}")
            print(f"Allow Custom: {attr.get('allowCustom')}") # Note: API might not return this explicitly in all versions, but good to check
            
            print("Allowed Values:")
            values = attr.get('attributeValues', [])
            for v in values:
                print(f" - {v['name']} (ID: {v['id']})")
                
            # Check for 3.3 matches specifically
            print("\nSearching for 3.3 matches:")
            for v in values:
                if '3.3' in v['name'] or '3,3' in v['name']:
                    print(f"FOUND: {v['name']} (ID: {v['id']})")

if __name__ == "__main__":
    check_attributes()
