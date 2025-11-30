import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.ai_views import process_attribute_match_task
from products.models import Product
from django.contrib.auth.models import User
import concurrent.futures

# Admin kullanıcısını al
user = User.objects.filter(is_superuser=True).first()
if not user:
    print('Admin kullanıcı bulunamadı')
    exit()

# API key al
from integrations.models import GeminiSettings
try:
    settings = GeminiSettings.objects.get(user=user)
    api_keys = list(settings.api_keys.values_list('key', flat=True))
    if not api_keys and settings.api_key:
        api_keys = [settings.api_key]
except GeminiSettings.DoesNotExist:
    print('AI ayarları bulunamadı')
    exit()

if not api_keys:
    print('API anahtarı bulunamadı')
    exit()

# 4462 olan ürünleri al
products = Product.objects.filter(trendyol_category_id=4462)
print(f'{len(products)} ürün için özellik eşleştirmesi yapılacak')

# Paralel işleme
key_cycle = iter(api_keys * (len(products) // len(api_keys) + 1))  # Keys'i döngüye al

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(api_keys), 5)) as executor:
    future_to_product = {}
    for product in products:
        key = next(key_cycle)
        future = executor.submit(process_attribute_match_task, product.id, key, user.id)
        future_to_product[future] = product

    for future in concurrent.futures.as_completed(future_to_product):
        product = future_to_product[future]
        try:
            result = future.result()
            results.append(result)
            status = "Başarılı" if result.get('success') else "Başarısız"
            print(f"{product.sku}: {status}")
            if not result.get('success'):
                print(f"  Hata: {result.get('error')}")
        except Exception as exc:
            print(f"{product.sku}: İstisna - {exc}")

success_count = sum(1 for r in results if r.get('success'))
print(f"\nToplam: {len(results)} ürün işlendi, {success_count} başarılı")