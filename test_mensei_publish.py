import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product, CategoryMapping
from integrations.services import TrendyolService
from django.contrib.auth.models import User

# Test için bir ürün al
product = Product.objects.filter(category_path__icontains='Çay ve Kahve').first()
if not product:
    print('Test ürünü bulunamadı')
    exit()

print(f'Test ürünü: {product.name}')
print(f'Kategori: {product.category_path}')

# Trendyol servisi ile attribute'ları al
user = User.objects.first()
service = TrendyolService(user=user)

# Kategori ID'sini al
cat_mapping = CategoryMapping.objects.filter(xml_category_name=product.category_path).first()
if not cat_mapping:
    print('Kategori mapping bulunamadı')
    exit()

print(f'Trendyol Kategori ID: {cat_mapping.trendyol_category_id}')

# Attribute'ları al
try:
    attrs_resp = service.get_category_attributes(cat_mapping.trendyol_category_id)
    mensei_attr = None
    for attr in attrs_resp.get('categoryAttributes', []):
        if attr['attribute']['id'] == 1192:
            mensei_attr = attr
            break

    if mensei_attr:
        print('Menşei attribute bulundu:')
        print(f'ID: {mensei_attr["attribute"]["id"]}')
        print(f'Name: {mensei_attr["attribute"]["name"]}')
        print(f'Required: {mensei_attr.get("required")}')

        # TR değerini bul
        tr_value = None
        for val in mensei_attr.get('attributeValues', []):
            if 'türkiye' in val['name'].lower() or 'tr' in val['name'].lower():
                tr_value = val
                break

        if tr_value:
            print(f'TR Value ID: {tr_value["id"]}')
        else:
            print('TR değeri bulunamadı')
    else:
        print('Menşei attribute bulunamadı')

except Exception as e:
    print(f'Hata: {e}')