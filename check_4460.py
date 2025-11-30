from products.models import Product, CategoryMapping

print('Ürünler trendyol_category_id=4460:')
products = Product.objects.filter(trendyol_category_id=4460)
print(products.count())
for p in products[:5]:
    print(f'{p.sku}: {p.name}')

print('\nCategoryMapping trendyol_category_id=4460:')
mappings = CategoryMapping.objects.filter(trendyol_category_id=4460)
print(mappings.count())
for m in mappings:
    print(f'{m.xml_category_name} -> {m.trendyol_category_id}')