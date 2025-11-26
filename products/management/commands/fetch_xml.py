import requests
import xmltodict
from django.core.management.base import BaseCommand
from products.models import Supplier, Product, ProductImage
from products.utils import apply_frame_to_image
from decimal import Decimal

class Command(BaseCommand):
    help = 'Fetches and parses XML from a supplier'

    def add_arguments(self, parser):
        parser.add_argument('supplier_id', type=int, help='ID of the supplier to fetch XML for')

    def handle(self, *args, **options):
        supplier_id = options['supplier_id']
        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Supplier with ID {supplier_id} not found'))
            return

        url = supplier.xml_url
        self.stdout.write(f"Fetching XML from {url}...")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch XML: {e}"))
            return

        self.stdout.write("Parsing XML...")
        try:
            data = xmltodict.parse(response.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse XML: {e}"))
            return

        # XML yapısını tahmin etmeye çalışalım. Genelde root -> products -> product şeklindedir.
        # Ancak bazen root -> product da olabilir.
        
        root_keys = list(data.keys())
        root = data[root_keys[0]]
        
        # Ürün listesini bulmaya çalış
        products_list = []
        if isinstance(root, list):
             products_list = root
        elif isinstance(root, dict):
            # Dict ise, içinde liste olan bir key arayalım
            for key, value in root.items():
                if isinstance(value, list):
                    products_list = value
                    break
                elif isinstance(value, dict): # Tek bir ürün varsa veya iç içe yapı
                     # Bazen <Urunler><Urun>...</Urun></Urunler> yapısı olur
                     if isinstance(value, list): # Bu durumda value liste olabilir
                         products_list = value
                         break
                     # Daha derin kontrol gerekebilir ama şimdilik basit tutalım.
            
            # Eğer hala bulamadıysak ve root'un kendisi bir ürün listesi değilse,
            # belki root'un altındaki tek key bir listedir.
            if not products_list:
                 # Örnek: data['Urunler']['Urun'] -> list
                 for key in root:
                     if isinstance(root[key], list):
                         products_list = root[key]
                         break

        if not products_list:
             self.stdout.write(self.style.WARNING("Could not find a list of products in the XML. Dumping keys for debugging:"))
             self.stdout.write(str(root_keys))
             if isinstance(root, dict):
                 self.stdout.write(str(root.keys()))
             return

        self.stdout.write(f"Found {len(products_list)} products. Processing...")

        count_created = 0
        count_updated = 0

        for item in products_list:
            # Mapping Logic (Burası XML yapısına göre özelleştirilmeli)
            # Standart bir yapı varsayıyoruz, ancak key'leri kontrol edeceğiz.
            
            # Olası key isimleri
            sku = item.get('Product_code') or item.get('StokKodu') or item.get('UrunKodu') or item.get('sku') or item.get('code')
            name = item.get('Name') or item.get('UrunAdi') or item.get('Baslik') or item.get('name') or item.get('title')
            
            # Fiyat Alanları
            # Alış Fiyatı (Bayi Fiyatı)
            buying_price_raw = item.get('xml_bayii_alis_fiyati') or item.get('AlisFiyati') or item.get('BayiFiyati') or item.get('buying_price')
            # Satış Fiyatı (Liste Fiyatı)
            selling_price_raw = item.get('SatisFiyati') or item.get('Fiyat') or item.get('price') or item.get('selling_price')
            
            # Eğer alış fiyatı yoksa satış fiyatını kullan, o da yoksa 0
            if not buying_price_raw and selling_price_raw:
                buying_price_raw = selling_price_raw
            
            stock = item.get('Stock') or item.get('StokAdedi') or item.get('Miktar') or item.get('stock') or item.get('quantity')
            desc = item.get('Description') or item.get('Aciklama') or item.get('Detay') or item.get('description')
            brand = item.get('Marka') or item.get('brand')
            barcode = item.get('Barcode') or item.get('Barkod') or item.get('barcode')
            category_path = item.get('Category') or item.get('Kategori') or item.get('category') or item.get('KategoriYolu')
            
            if not sku:
                self.stdout.write(self.style.WARNING(f"Skipping product without SKU: {item}"))
                continue

            # Fiyat temizleme fonksiyonu
            def clean_price(p):
                if not p: return Decimal('0.00')
                if isinstance(p, str):
                    p = p.replace(',', '.')
                try:
                    return Decimal(p)
                except:
                    return Decimal('0.00')

            buying_price = clean_price(buying_price_raw)
            selling_price = clean_price(selling_price_raw)
            
            # Eğer satış fiyatı 0 ise ve alış fiyatı varsa, satış fiyatını alış fiyatı yap (geçici)
            if selling_price == 0 and buying_price > 0:
                selling_price = buying_price

            # Stok temizleme
            try:
                stock_int = int(stock) if stock else 0
            except:
                stock_int = 0

            product, created = Product.objects.update_or_create(
                supplier=supplier,
                sku=sku,
                defaults={
                    'name': name or "No Name",
                    'description': desc or "",
                    'buying_price': buying_price,
                    'selling_price': selling_price,
                    'stock_quantity': stock_int,
                    'brand': brand,
                    'category_path': category_path,
                    'original_barcode': barcode, # XML'den gelen barkodu sakla
                    'supplier_product_id': sku,
                    'attributes': item  # Tüm XML verisini attributes alanına kaydet
                }
            )
            
            # Eğer ürün yeni oluşturulduysa ve henüz bir Trendyol barkodu yoksa,
            # XML barkodunu geçici olarak barcode alanına da yazabiliriz veya boş bırakabiliriz.
            # Kullanıcı "Benzersiz Barkod Oluştur" dediğinde bu alan güncellenecek.
            if created and not product.barcode:
                 product.barcode = barcode

            # Resim İşleme
            # Önceki resimleri temizle (Basit senaryo)
            product.images.all().delete()
            
            # Frame Settings
            use_frame = False
            frame_path = None
            if hasattr(supplier, 'settings') and supplier.settings.use_frame and supplier.settings.frame_image:
                use_frame = True
                frame_path = supplier.settings.frame_image.path

            def create_product_image(url, is_primary=False):
                pi = ProductImage(product=product, image_url=url, is_primary=is_primary)
                if use_frame and frame_path:
                    try:
                        processed = apply_frame_to_image(url, frame_path)
                        if processed:
                            pi.processed_image.save(processed.name, processed, save=False)
                    except Exception as e:
                        print(f"Frame error: {e}")
                pi.save()
            
            # Image1, Image2... Image5 kontrolü
            for i in range(1, 6):
                img_key = f'Image{i}'
                img_url = item.get(img_key)
                if img_url:
                    create_product_image(img_url, is_primary=(i==1))

            # Diğer olası resim yapıları (Eski koddan kalan destek)
            images = item.get('Resimler') or item.get('Images') or item.get('images')
            if images:
                img_list = []
                if isinstance(images, list):
                    img_list = images
                elif isinstance(images, dict):
                    # <Resimler><Resim>url1</Resim><Resim>url2</Resim></Resimler> yapısı
                    for k, v in images.items():
                        if isinstance(v, list):
                            img_list = v
                        elif isinstance(v, str):
                            img_list.append(v)
                elif isinstance(images, str):
                    img_list.append(images)
                
                for img_url in img_list:
                    if isinstance(img_url, str):
                        create_product_image(img_url)
                    elif isinstance(img_url, dict):
                         # Bazen <Resim>url</Resim> dict olarak gelebilir xmltodict ile
                         # Genelde #text key'i olur
                         url = img_url.get('#text') or img_url.get('url')
                         if url:
                             create_product_image(url)


            if created:
                count_created += 1
            else:
                count_updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Created: {count_created}, Updated: {count_updated}"))
