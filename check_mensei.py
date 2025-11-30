import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

u = User.objects.first()
s = TrendyolService(u)
attrs = s.get_category_attributes(2139)

for a in attrs.get('categoryAttributes', []):
    if a['attribute']['id'] == 1192:  # Menşei
        print(f'Attribute: {a["attribute"]["name"]}')
        print('Values:')
        for v in a.get('attributeValues', []):
            print(f'  - {v["name"]} (ID: {v["id"]})')
        break