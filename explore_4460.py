import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from integrations.services import TrendyolService
from django.contrib.auth.models import User

# Admin kullanıcısını al
user = User.objects.filter(is_superuser=True).first()
if not user:
    print('Admin kullanıcı bulunamadı')
    exit()

service = TrendyolService(user=user)

def explore_tree(cats, level=0):
    for cat in cats:
        cat_id = cat['id']
        name = cat['name']
        indent = '  ' * level
        print(f"{indent}{cat_id}: {name}")

        if 'subCategories' in cat and cat['subCategories']:
            explore_tree(cat['subCategories'], level + 1)
        else:
            # Yaprak kategori - özellikleri kontrol et
            try:
                attrs = service.get_category_attributes(cat_id)
                if 'categoryAttributes' in attrs:
                    print(f"{indent}  -> Özellikler var ({len(attrs['categoryAttributes'])} özellik)")
                else:
                    print(f"{indent}  -> Özellikler yok")
            except Exception as e:
                print(f"{indent}  -> API hatası: {e}")

try:
    tree = service.get_category_tree()
    if 'categories' in tree:
        # 4460'i bul
        def find_cat_4460(cats):
            for cat in cats:
                if cat['id'] == 4460:
                    return cat
                if 'subCategories' in cat:
                    result = find_cat_4460(cat['subCategories'])
                    if result:
                        return result
            return None

        cat_4460 = find_cat_4460(tree['categories'])
        if cat_4460:
            print('4460 Mutfak Gereçleri alt kategorileri:')
            if 'subCategories' in cat_4460:
                explore_tree(cat_4460['subCategories'], 1)
            else:
                print('Alt kategori yok')
        else:
            print('4460 kategorisi bulunamadı')
    else:
        print('Kategori ağacı alınamadı')
except Exception as e:
    print(f'Hata: {e}')