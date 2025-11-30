import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

u = User.objects.first()
s = TrendyolService(u)
attrs = s.get_category_attributes(2139)

print('Materyal Attribute Values:')
for a in attrs.get('categoryAttributes', []):
    if a['attribute']['id'] == 14:  # Materyal
        print(f"Attribute: {a['attribute']['name']}")
        print(f"Required: {a.get('required', False)}")
        print("Values:")
        for v in a.get('attributeValues', []):
            print(f"  - {v['name']} (ID: {v['id']})")
        break