import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product, CategoryMapping

def check_attributes():
    mappings = CategoryMapping.objects.all()
    print(f"Total mappings: {mappings.count()}")
    
    for mapping in mappings:
        print(f"Checking mapping: {mapping.xml_category_name}")
        products = Product.objects.filter(category_path=mapping.xml_category_name)
        print(f"Found {products.count()} products for this category.")
        
        if products.exists():
            p = products.first()
            print(f"Sample product attributes: {p.attributes}")
            print(f"Sample product attributes type: {type(p.attributes)}")
            
            xml_keys = set()
            for p in products[:10]:
                if p.attributes:
                    if isinstance(p.attributes, str):
                        import json
                        try:
                            attrs = json.loads(p.attributes)
                            xml_keys.update(attrs.keys())
                        except:
                            print("Attributes is a string but not valid JSON")
                    elif isinstance(p.attributes, dict):
                        xml_keys.update(p.attributes.keys())
            
            print(f"Collected keys: {xml_keys}")
        print("-" * 20)

if __name__ == "__main__":
    check_attributes()
