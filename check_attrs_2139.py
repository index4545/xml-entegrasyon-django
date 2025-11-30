import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

u = User.objects.first()
s = TrendyolService(u)
attrs = s.get_category_attributes(2139)

print('Trendyol Attributes:')
for a in attrs.get('categoryAttributes', [])[:15]:
    attr_name = a['attribute']['name']
    attr_id = a['attribute']['id']
    required = a.get('required', False)
    has_values = bool(a.get('attributeValues'))
    print(f'- {attr_name} (ID: {attr_id}) - Required: {required} - Has Values: {has_values}')