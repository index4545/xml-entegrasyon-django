import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

user = User.objects.filter(is_superuser=True).first()
service = TrendyolService(user=user)

try:
    attrs = service.get_category_attributes(4462)
    if 'categoryAttributes' in attrs:
        print('4462 Demlik kategorisi özellikleri:')
        for attr in attrs['categoryAttributes']:
            required = attr.get('required', False)
            name = attr['attribute']['name']
            status = "Zorunlu" if required else "İsteğe bağlı"
            print(f'  {name} ({status})')
    else:
        print('Özellik bulunamadı')
except Exception as e:
    print(f'Hata: {e}')