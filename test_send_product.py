import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product, CategoryMapping, CategoryAttributeMapping, SupplierSettings, PriceRule, TrendyolBatchRequest
from integrations.services import TrendyolService
from django.contrib.auth.models import User
import random

# Test ürünü al
product = Product.objects.filter(category_path__icontains='Çay ve Kahve', is_published_to_trendyol=False).first()
if not product:
    print('Test ürünü bulunamadı')
    exit()

print(f'Test ürünü gönderiliyor: {product.name}')

# Tedarikçi ayarları
supplier_settings = SupplierSettings.objects.filter(supplier_id=product.supplier_id).first()
price_rules = list(PriceRule.objects.filter(supplier_id=product.supplier_id))

# Trendyol servisi
user = User.objects.first()
service = TrendyolService(user=user)

# Kategori mapping
cat_mapping = CategoryMapping.objects.filter(xml_category_name=product.category_path).first()
if not cat_mapping:
    print('Kategori mapping bulunamadı')
    exit()

# Fiyat hesapla
cost = float(product.buying_price) if product.buying_price > 0 else float(product.selling_price)
if supplier_settings:
    # Basit fiyat hesaplaması
    margin = float(supplier_settings.profit_margin) / 100
    product.selling_price = round(cost * (1 + margin), 2)
else:
    product.selling_price = round(cost * 1.2, 2)

# Barkod
if not product.barcode:
    product.barcode = f"TY-{product.sku}-{random.randint(1000,9999)}"

# SKU
if supplier_settings and supplier_settings.sku_prefix and not product.sku.startswith(supplier_settings.sku_prefix):
    product.sku = f"{supplier_settings.sku_prefix}{product.sku}"

# Mapping
product.trendyol_category_id = cat_mapping.trendyol_category_id
brand_mapping = None  # Basitleştirme için
product.trendyol_brand_id = 1  # Default
product.save()

# Attributes oluştur
attributes = []

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

    # CategoryAttributeMapping'leri al
    mappings = list(CategoryAttributeMapping.objects.filter(category_mapping=cat_mapping))

    def tr_lower(s):
        return s.replace('İ', 'i').replace('I', 'ı').lower()

    for m in mappings:
        attr_val = None
        allowed_values = attr_values_map.get(m.trendyol_attribute_id, [])

        if m.mapping_type == 'fixed':
            attr_val = m.static_value
        elif m.mapping_type == 'xml' and m.xml_attribute_name:
            attr_val = product.attributes.get(m.xml_attribute_name) if product.attributes else None

        # Text -> ID
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

    print(f'Final attributes count: {len(attributes)}')
    mensei_attr = next((a for a in attributes if a['attributeId'] == 1192), None)
    if mensei_attr:
        print(f'Menşei: {mensei_attr}')
    else:
        print('Menşei bulunamadı!')

    # Resimler
    image_urls = []
    for img in product.images.all()[:4]:  # Max 4 resim
        image_urls.append(img.image_url)

    if not image_urls:
        print('Resim bulunamadı')
        exit()

    # Item hazırla
    item = {
        "barcode": product.barcode,
        "title": product.name[:100],
        "productMainId": product.model_code if product.model_code else product.sku,
        "brandId": product.trendyol_brand_id,
        "categoryId": product.trendyol_category_id,
        "quantity": product.stock_quantity,
        "stockCode": product.sku,
        "dimensionalWeight": 1,
        "description": product.description,
        "currencyType": "TRY",
        "listPrice": float(product.selling_price),
        "salePrice": float(product.selling_price),
        "vatRate": 20,
        "cargoCompanyId": 10,
        "images": [{"url": url} for url in image_urls],
        "attributes": attributes
    }

    print(f'Ürün gönderiliyor: {item["title"]}')

    # Gönder
    result = service.create_products([item])

    if "batchRequestId" in result:
        batch_id = result['batchRequestId']
        print(f'✅ Başarılı! Batch ID: {batch_id}')

        # Batch Request kaydet
        TrendyolBatchRequest.objects.create(
            batch_request_id=batch_id,
            batch_type='ProductV2OnBoarding',
            item_count=1
        )

        # Ürünü yayınlandı olarak işaretle
        product.is_published_to_trendyol = True
        product.save()

        print('Ürün yayınlandı olarak işaretlendi.')
    else:
        print(f'❌ Hata: {result}')

except Exception as e:
    print(f'Hata: {e}')
    import traceback
    traceback.print_exc()