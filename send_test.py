import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product
from integrations.services import TrendyolService
from django.contrib.auth.models import User
import random

# Admin kullanıcısını al
user = User.objects.filter(is_superuser=True).first()
service = TrendyolService(user=user)

# 4462 olan ürünleri al
products = Product.objects.filter(trendyol_category_id=4462, is_published_to_trendyol=False)[:3]  # İlk 3'ü test edelim
print(f'{len(products)} ürün gönderilecek')

prepared_items = []

for p in products:
    # SKU prefix ve barcode işlemleri
    sku_prefix = ''
    use_unique_barcode = False
    
    if not p.barcode:
        p.barcode = f'TY-{p.sku}-{random.randint(1000,9999)}'
    
    if sku_prefix and not p.sku.startswith(sku_prefix):
        p.sku = f'{sku_prefix}{p.sku}'
    
    # Fiyat hesaplama (basit)
    cost = float(p.buying_price) if p.buying_price > 0 else float(p.selling_price)
    p.selling_price = round(cost * 1.2, 2)
    
    # Resimler
    image_urls = []
    if p.images.exists():
        for img in p.images.all():
            if img.cloudinary_url:
                image_urls.append(img.cloudinary_url)
            else:
                image_urls.append(img.image_url)
    
    item = {
        'barcode': p.barcode,
        'title': p.name[:100],
        'productMainId': p.model_code if p.model_code else p.sku,
        'brandId': p.trendyol_brand_id,
        'categoryId': p.trendyol_category_id,
        'quantity': p.stock_quantity,
        'stockCode': p.sku,
        'dimensionalWeight': 1,
        'description': p.description,
        'currencyType': 'TRY',
        'listPrice': float(p.selling_price),
        'salePrice': float(p.selling_price),
        'vatRate': 20,
        'cargoCompanyId': 10,
        'images': [{'url': url} for url in image_urls],
        'attributes': p.trendyol_attributes or []
    }
    prepared_items.append(item)

print(f'{len(prepared_items)} ürün hazırlandı')

# Gönder
try:
    result = service.create_products(prepared_items)
    print('Gönderim sonucu:', result)
    
    if 'batchRequestId' in result:
        print(f'Batch ID: {result["batchRequestId"]}')
        # Başarılıysa ürünleri güncelle
        barcodes = [item['barcode'] for item in prepared_items]
        Product.objects.filter(barcode__in=barcodes).update(is_published_to_trendyol=True)
        print(f'{len(barcodes)} ürün yayınlandı olarak işaretlendi')
    
except Exception as e:
    print(f'Hata: {e}')