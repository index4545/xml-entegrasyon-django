from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import Supplier, Product, SupplierSettings, PriceRule, TrendyolBatchRequest, CategoryMapping, TrendyolCategory, ProductImage, BackgroundProcess
from integrations.services import TrendyolService
from products.views import calculate_selling_price
import requests
import xmltodict
from decimal import Decimal
import datetime
import traceback

class Command(BaseCommand):
    help = 'Syncs stock and price changes from XML to Trendyol automatically. Also fetches new products.'

    def add_arguments(self, parser):
        parser.add_argument('--supplier_id', type=int, help='Specific supplier ID to sync', required=False)

    def handle(self, *args, **options):
        self.stdout.write("Starting auto sync...")
        
        supplier_id = options.get('supplier_id')
        
        if supplier_id:
            suppliers = Supplier.objects.filter(id=supplier_id)
        else:
            suppliers = Supplier.objects.filter(is_active=True)
        
        for supplier in suppliers:
            try:
                settings = supplier.settings
            except SupplierSettings.DoesNotExist:
                if supplier_id: # If manually triggered, create settings if missing or proceed
                     settings, _ = SupplierSettings.objects.get_or_create(supplier=supplier)
                else:
                    continue
            
            # Check if it's time to update (only if not manually triggered)
            if not supplier_id:
                if settings.auto_update_interval <= 0:
                    continue
                
                last_update = settings.last_auto_update
                if last_update:
                    next_update = last_update + datetime.timedelta(minutes=settings.auto_update_interval)
                    if timezone.now() < next_update:
                        continue
            
            self.stdout.write(f"Processing supplier: {supplier.name}")
            
            # Create Background Process Record
            process = BackgroundProcess.objects.create(
                process_type='xml_sync',
                supplier=supplier,
                status='processing',
                message='XML indiriliyor...'
            )
            
            try:
                self.sync_supplier(supplier, settings, process)
                process.status = 'completed'
                process.completed_at = timezone.now()
                process.message = 'İşlem başarıyla tamamlandı.'
                process.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {supplier.name}: {e}"))
                process.status = 'failed'
                process.message = f"Hata oluştu: {str(e)}"
                process.error_details = traceback.format_exc()
                process.completed_at = timezone.now()
                process.save()
            
            # Update last run time
            settings.last_auto_update = timezone.now()
            settings.save()

    def sync_supplier(self, supplier, settings, process):
        # 1. Fetch XML
        try:
            response = requests.get(supplier.xml_url, timeout=120) # Increased timeout
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"XML indirilemedi: {e}")

        process.message = "XML analiz ediliyor..."
        process.save()

        # 2. Parse XML
        try:
            data = xmltodict.parse(response.content)
        except Exception as e:
            raise Exception(f"XML okunamadı: {e}")

        # Find product list (Improved logic)
        products_list = []
        
        # Strategy 1: Check for RSS/Channel/Item (New format)
        if 'rss' in data and 'channel' in data['rss'] and 'item' in data['rss']['channel']:
            products_list = data['rss']['channel']['item']
        else:
            # Strategy 2: Generic Search
            root_keys = list(data.keys())
            root = data[root_keys[0]]
            
            if isinstance(root, list):
                 products_list = root
            elif isinstance(root, dict):
                for key, value in root.items():
                    if isinstance(value, list):
                        products_list = value
                        break
                    elif isinstance(value, dict) and isinstance(value, list):
                         products_list = value
                         break
                if not products_list:
                     for key in root:
                         if isinstance(root[key], list):
                             products_list = root[key]
                             break
        
        if not products_list:
            raise Exception("XML içinde ürün listesi bulunamadı.")

        # Ensure products_list is a list (xmltodict returns dict for single item)
        if isinstance(products_list, dict):
            products_list = [products_list]

        total_items = len(products_list)
        process.total_items = total_items
        process.message = f"{total_items} ürün bulundu. İşleniyor..."
        process.save()

        self.stdout.write(f"Found {total_items} products in XML. Checking for updates...")
        
        updated_items_payload = []
        
        # Cache existing products for this supplier
        existing_products = {p.sku: p for p in Product.objects.filter(supplier=supplier)}
        
        # Cache price rules and commissions
        price_rules = list(PriceRule.objects.filter(supplier=supplier))
        cat_mappings = {m.xml_category_name: m for m in CategoryMapping.objects.all()}
        
        count_created = 0
        count_updated = 0
        processed_count = 0

        for item in products_list:
            processed_count += 1
            if processed_count % 100 == 0:
                process.processed_items = processed_count
                process.save()

            # Field Mapping Logic
            # 1. SKU
            sku = item.get('Product_code') or item.get('StokKodu') or item.get('UrunKodu') or item.get('sku') or item.get('code') or item.get('id') or item.get('g:id')
            if not sku:
                continue
            
            # 2. Name
            name = item.get('Name') or item.get('UrunAdi') or item.get('Baslik') or item.get('name') or item.get('title') or item.get('g:title') or "No Name"
            
            # 3. Description
            desc = item.get('Description') or item.get('Aciklama') or item.get('Detay') or item.get('description') or item.get('g:description') or ""
            
            # 4. Brand
            brand = item.get('Marka') or item.get('brand') or item.get('g:brand')
            
            # 5. Barcode
            barcode = item.get('Barcode') or item.get('Barkod') or item.get('barcode') or item.get('g:gtin')
            
            # 6. Category
            category_path = item.get('Category') or item.get('Kategori') or item.get('category') or item.get('KategoriYolu') or item.get('g:product_type')
            # Handle list of categories (RSS feed case)
            if isinstance(category_path, list):
                category_path = " > ".join([str(c) for c in category_path if c])

            # 7. Stock
            stock_raw = item.get('Stock') or item.get('StokAdedi') or item.get('Miktar') or item.get('stock') or item.get('quantity') or item.get('g:quantity')
            # RSS availability check
            if not stock_raw and item.get('g:availability') == 'in stock':
                 stock_raw = 10 # Default if just "in stock"
            
            try:
                new_stock = int(stock_raw) if stock_raw else 0
            except:
                new_stock = 0
                
            # 8. Price (Buying Price)
            # Priority: xml_bayii_alis_fiyati > AlisFiyati > price (if listprice exists) > g:price
            buying_price_raw = item.get('xml_bayii_alis_fiyati') or item.get('AlisFiyati') or item.get('BayiFiyati') or item.get('buying_price')
            
            # If no explicit buying price, check generic 'price'
            if not buying_price_raw:
                # In RSS feeds, 'price' is often the selling price. 'listprice' is MSRP.
                # We assume 'price' is our cost if no other cost field exists, OR we map it to selling price.
                # For dropshipping, usually the feed gives you the price you pay.
                buying_price_raw = item.get('price') or item.get('g:price')

            # Fallback to selling price fields if still empty
            if not buying_price_raw:
                buying_price_raw = item.get('SatisFiyati') or item.get('Fiyat') or item.get('selling_price') or item.get('g:sale_price')

            def clean_price(p):
                if not p: return Decimal('0.00')
                if isinstance(p, str):
                    # Remove currency symbols
                    p = p.replace('TRY', '').replace('TL', '').strip()
                    p = p.replace(',', '.')
                try:
                    return Decimal(p)
                except:
                    return Decimal('0.00')
            
            new_buying_price = clean_price(buying_price_raw)
            
            # Determine Commission Rate
            commission_rate = 0
            if category_path in cat_mappings:
                mapping = cat_mappings[category_path]
                commission_rate = mapping.commission_rate or 0
            
            # Calculate Selling Price
            new_selling_price = calculate_selling_price(
                new_buying_price, 
                settings, 
                price_rules, 
                commission_rate
            )

            if sku in existing_products:
                # UPDATE EXISTING PRODUCT
                product = existing_products[sku]
                
                # Check for changes
                stock_changed = product.stock_quantity != new_stock
                price_changed = abs(product.buying_price - new_buying_price) > Decimal('0.01')
                
                if stock_changed or price_changed:
                    product.stock_quantity = new_stock
                    product.buying_price = new_buying_price
                    product.selling_price = new_selling_price
                    product.save()
                    count_updated += 1
                    
                    # If published to Trendyol, add to update payload
                    if product.is_published_to_trendyol and product.barcode:
                        updated_items_payload.append({
                            "barcode": product.barcode,
                            "quantity": new_stock,
                            "salePrice": float(new_selling_price),
                            "listPrice": float(new_selling_price)
                        })
            else:
                # CREATE NEW PRODUCT
                product = Product.objects.create(
                    supplier=supplier,
                    sku=sku,
                    name=name,
                    description=desc,
                    buying_price=new_buying_price,
                    selling_price=new_selling_price,
                    stock_quantity=new_stock,
                    brand=brand,
                    category_path=category_path,
                    original_barcode=barcode,
                    supplier_product_id=sku,
                    attributes=item
                )
                if not product.barcode and barcode:
                    product.barcode = barcode
                    product.save()
                
                # Handle Images
                # Image1, Image2... Image5
                for i in range(1, 6):
                    img_key = f'Image{i}'
                    img_url = item.get(img_key)
                    if img_url:
                        ProductImage.objects.create(product=product, image_url=img_url, is_primary=(i==1))
                
                # RSS / Google Merchant Image Links
                img_link = item.get('image_link') or item.get('g:image_link')
                if img_link:
                     ProductImage.objects.create(product=product, image_url=img_link, is_primary=True)
                
                # Additional Images
                for k, v in item.items():
                    if k.startswith('additional_image_link') or k.startswith('g:additional_image_link'):
                        if v:
                            ProductImage.objects.create(product=product, image_url=v)

                # Other image formats
                images = item.get('Resimler') or item.get('Images') or item.get('images')
                if images:
                    img_list = []
                    if isinstance(images, list):
                        img_list = images
                    elif isinstance(images, dict):
                        for k, v in images.items():
                            if isinstance(v, list): img_list = v
                            elif isinstance(v, str): img_list.append(v)
                    elif isinstance(images, str):
                        img_list.append(images)
                    
                    for img_url in img_list:
                        if isinstance(img_url, str):
                            ProductImage.objects.create(product=product, image_url=img_url)
                        elif isinstance(img_url, dict):
                             url = img_url.get('#text') or img_url.get('url')
                             if url:
                                 ProductImage.objects.create(product=product, image_url=url)
                
                count_created += 1

        self.stdout.write(self.style.SUCCESS(f"Sync complete. Created: {count_created}, Updated: {count_updated}"))
        process.message = f"Tamamlandı. Eklenen: {count_created}, Güncellenen: {count_updated}"
        process.processed_items = total_items
        process.save()

        if updated_items_payload:
            self.stdout.write(f"Sending updates for {len(updated_items_payload)} items to Trendyol...")
            process.message += f" | Trendyol'a {len(updated_items_payload)} güncelleme gönderiliyor..."
            process.save()
            
            from integrations.models import TrendyolSettings
            ty_settings = TrendyolSettings.objects.filter(is_active=True).first()
            
            if not ty_settings:
                self.stdout.write(self.style.ERROR("No active Trendyol settings found. Cannot sync."))
                return

            service = TrendyolService(user=ty_settings.user)
            
            results = service.update_price_and_inventory(updated_items_payload)
            
            for res in results:
                if "batchRequestId" in res:
                    self.stdout.write(self.style.SUCCESS(f"Batch sent: {res['batchRequestId']}"))
                    # Log batch request
                    TrendyolBatchRequest.objects.create(
                        batch_request_id=res['batchRequestId'],
                        batch_type='ProductInventoryUpdate',
                        item_count=len(updated_items_payload) # This is approximate per batch
                    )
                else:
                    self.stdout.write(self.style.ERROR(f"Error sending batch: {res}"))
        else:
            self.stdout.write("No changes detected for Trendyol.")

