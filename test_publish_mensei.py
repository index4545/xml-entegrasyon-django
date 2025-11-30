import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product, CategoryMapping, CategoryAttributeMapping
from integrations.services import TrendyolService
from django.contrib.auth.models import User

# Test ürünü al
product = Product.objects.filter(category_path__icontains='Çay ve Kahve').first()
if not product:
    print('Test ürünü bulunamadı')
    exit()

print(f'Test ürünü: {product.name}')

# Trendyol servisi
user = User.objects.first()
service = TrendyolService(user=user)

# Kategori mapping
cat_mapping = CategoryMapping.objects.filter(xml_category_name=product.category_path).first()
if not cat_mapping:
    print('Kategori mapping bulunamadı')
    exit()

print(f'Kategori: {cat_mapping.trendyol_category_id}')

# Attribute mappings
mappings = list(CategoryAttributeMapping.objects.filter(category_mapping=cat_mapping))
print(f'Attribute mappings sayısı: {len(mappings)}')

# Trendyol attribute'ları al
try:
    ty_resp = service.get_category_attributes(cat_mapping.trendyol_category_id)
    attr_values_map = {}
    required_set = set()
    for attr in ty_resp.get('categoryAttributes', []):
        attr_id = attr['attribute']['id']
        values = attr.get('attributeValues', [])
        attr_values_map[attr_id] = values
        if attr.get('required'):
            required_set.add(attr_id)

    print(f'Required attributes: {required_set}')
    print(f'Menşei required: {1192 in required_set}')

    # Attributes oluştur (publish_wizard mantığı)
    attributes = []

    def tr_lower(s):
        return s.replace('İ', 'i').replace('I', 'ı').lower()

    for m in mappings:
        attr_val = None
        allowed_values = attr_values_map.get(m.trendyol_attribute_id, [])

        if m.mapping_type == 'fixed':
            attr_val = m.static_value
        elif m.mapping_type == 'xml' and m.xml_attribute_name:
            attr_val = product.attributes.get(m.xml_attribute_name) if product.attributes else None

        # Text -> ID Lookup
        if attr_val and not str(attr_val).isdigit() and allowed_values:
            text_val = tr_lower(str(attr_val))
            for av in allowed_values:
                av_name = tr_lower(av['name'])
                if av_name == text_val:
                    attr_val = av['id']
                    break

        if attr_val:
            attr_item = {"attributeId": m.trendyol_attribute_id}
            if str(attr_val).isdigit():
                 attr_item["attributeValueId"] = int(attr_val)
            else:
                 attr_item["customAttributeValue"] = str(attr_val)
            attributes.append(attr_item)

    print(f'Mapping sonrası attributes: {attributes}')

    # Auto-Fill Missing Required
    mapped_ids = set(a['attributeId'] for a in attributes)
    missing_required = required_set - mapped_ids

    for req_id in missing_required:
        allowed_values = attr_values_map.get(req_id, [])
        found_val = None

        search_text = tr_lower(f"{product.name} {product.description or ''}")
        for val in allowed_values:
            if tr_lower(val['name']) in search_text:
                found_val = val['id']
                break

        if not found_val:
            safe_defaults = ['çok renkli', 'karışık', 'diğer', 'belirtilmemiş', 'gümüş', 'metalik', 'tek renk', 'standart']
            for val in allowed_values:
                v_name = tr_lower(val['name'])
                if v_name in safe_defaults:
                    found_val = val['id']
                    break

        if not found_val and allowed_values:
             found_val = allowed_values[0]['id']

        if found_val:
            attributes.append({"attributeId": req_id, "attributeValueId": found_val})

    print(f'Auto-fill sonrası attributes: {attributes}')

    # Özel Kural: Menşei her zaman TR
    mensei_attr_id = 1192
    mensei_tr_value_id = 10617344

    mensei_exists = False
    for attr in attributes:
        if attr['attributeId'] == mensei_attr_id:
            mensei_exists = True
            if attr.get('attributeValueId') != mensei_tr_value_id:
                attr['attributeValueId'] = mensei_tr_value_id
            break

    if not mensei_exists:
        attributes.append({"attributeId": mensei_attr_id, "attributeValueId": mensei_tr_value_id})

    print(f'Final attributes: {attributes}')

    # Menşei kontrolü
    mensei_attr = None
    for attr in attributes:
        if attr['attributeId'] == 1192:
            mensei_attr = attr
            break

    if mensei_attr:
        print(f'Menşei attribute: {mensei_attr}')
        if mensei_attr.get('attributeValueId') == 10617344:
            print('✅ Menşei doğru olarak TR (10617344) ayarlandı!')
        else:
            print(f'❌ Menşei yanlış değer: {mensei_attr.get("attributeValueId")}')
    else:
        print('❌ Menşei attribute bulunamadı!')

except Exception as e:
    print(f'Hata: {e}')
    import traceback
    traceback.print_exc()