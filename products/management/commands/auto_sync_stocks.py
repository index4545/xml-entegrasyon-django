from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import Supplier, Product, SupplierSettings, PriceRule, TrendyolBatchRequest, CategoryMapping, TrendyolCategory, ProductImage, BackgroundProcess
from integrations.services import TrendyolService
from products.views import calculate_selling_price
from products.utils import apply_frame_to_image
import requests
import xmltodict
from decimal import Decimal
import datetime
import traceback

class Command(BaseCommand):
    help = 'Syncs stock and price changes from XML to Trendyol automatically. Also fetches new products.'

    def add_arguments(self, parser):
        parser.add_argument('--supplier_id', type=int, help='Specific supplier ID to sync', required=False)
        parser.add_argument('--product_ids', type=str, help='Comma separated list of product IDs to sync', required=False)
        parser.add_argument('--force', action='store_true', help='Force sync ignoring time interval', required=False)
        parser.add_argument('--process_type', type=str, help='Process type for logging', default='xml_sync', required=False)
        parser.add_argument('--published_only', action='store_true', help='Only sync products published to Trendyol', required=False)
        parser.add_argument('--verify_trendyol', action='store_true', help='Verify prices with Trendyol after sync', required=False)

    def handle(self, *args, **options):
        self.stdout.write("Starting auto sync...")
        
        supplier_id = options.get('supplier_id')
        product_ids_str = options.get('product_ids')
        force = options.get('force')
        process_type = options.get('process_type')
        published_only = options.get('published_only')
        verify_trendyol = options.get('verify_trendyol')
        
        target_skus = []
        if product_ids_str:
            try:
                p_ids = [int(x) for x in product_ids_str.split(',') if x.strip()]
                # Get SKUs for these products
                target_skus = list(Product.objects.filter(id__in=p_ids).values_list('sku', flat=True))
                
                # If product_ids are provided, we should filter suppliers based on these products
                relevant_supplier_ids = Product.objects.filter(id__in=p_ids).values_list('supplier_id', flat=True).distinct()
                suppliers = Supplier.objects.filter(id__in=relevant_supplier_ids)
                
                self.stdout.write(f"Syncing specific products: {len(target_skus)} SKUs from {suppliers.count()} suppliers.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Invalid product_ids: {e}"))
                return
        elif supplier_id:
            suppliers = Supplier.objects.filter(id=supplier_id)
        else:
            suppliers = Supplier.objects.filter(is_active=True)
        
        for supplier in suppliers:
            try:
                settings = supplier.settings
            except SupplierSettings.DoesNotExist:
                if supplier_id or product_ids_str or force: # If manually triggered, create settings if missing or proceed
                     settings, _ = SupplierSettings.objects.get_or_create(supplier=supplier)
                else:
                    continue
            
            # Check if it's time to update (only if not manually triggered)
            if not supplier_id and not product_ids_str and not force:
                if settings.auto_update_interval <= 0:
                    continue
                
                last_update = settings.last_auto_update
                if last_update:
                    next_update = last_update + datetime.timedelta(minutes=settings.auto_update_interval)
                    if timezone.now() < next_update:
                        continue
            
            # Determine target SKUs for this supplier
            current_target_skus = list(target_skus) if target_skus else []
            
            if published_only:
                published_skus = list(Product.objects.filter(supplier=supplier, is_published_to_trendyol=True).values_list('sku', flat=True))
                if not published_skus:
                    self.stdout.write(f"No published products for {supplier.name}, skipping.")
                    continue
                
                if current_target_skus:
                    # Intersect if both filters are present
                    current_target_skus = list(set(current_target_skus) & set(published_skus))
                    if not current_target_skus:
                        self.stdout.write(f"No matching published products for {supplier.name} in selected list.")
                        continue
                else:
                    current_target_skus = published_skus

            self.stdout.write(f"Processing supplier: {supplier.name}")
            
            # Create Background Process Record
            process = BackgroundProcess.objects.create(
                process_type=process_type,
                supplier=supplier,
                status='processing',
                message='XML indiriliyor...'
            )
            
            try:
                self.sync_supplier(supplier, settings, process, current_target_skus)
                
                if verify_trendyol:
                    self.verify_trendyol_prices(supplier, process, current_target_skus)
                
                process.status = 'completed'
                process.completed_at = timezone.now()
                if not verify_trendyol: # If verified, message is updated in verify function
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

    def verify_trendyol_prices(self, supplier, process, target_skus=None):
        """
        Fetches live data from Trendyol and compares with local DB.
        If discrepancies found, sends update.
        """
        self.stdout.write("Verifying Trendyol prices...")
        process.message += " | Trendyol fiyatları doğrulanıyor..."
        process.save()
        
        from integrations.models import TrendyolSettings
        ty_settings = TrendyolSettings.objects.filter(is_active=True).first()
        if not ty_settings:
            return

        service = TrendyolService(user=ty_settings.user)
        
        # Get published products for this supplier
        products = Product.objects.filter(supplier=supplier, is_published_to_trendyol=True)
        if target_skus:
            products = products.filter(sku__in=target_skus)
            
        # We need barcodes to query Trendyol
        # Since we can't query by barcode list efficiently for thousands of items (URL length limit),
        # we will fetch all products page by page and filter in memory OR query in small batches.
        # Querying in small batches is safer.
        
        barcodes = list(products.values_list('barcode', flat=True))
        barcodes = [b for b in barcodes if b]
        
        if not barcodes:
            return

        batch_size = 50 # Trendyol allows filtering by barcode, let's try 50 at a time
        mismatched_items = []
        
        total_checked = 0
        
        for i in range(0, len(barcodes), batch_size):
            batch_barcodes = barcodes[i:i+batch_size]
            
            try:
                ty_response = service.get_products(barcodes=batch_barcodes)
                ty_products = ty_response.get('content', [])
                
                # Map by barcode
                ty_map = {p['barcode']: p for p in ty_products}
                
                # Compare
                for barcode in batch_barcodes:
                    if barcode not in ty_map:
                        continue
                        
                    ty_p = ty_map[barcode]
                    local_p = Product.objects.filter(barcode=barcode).first()
                    
                    if not local_p: continue
                    
                    # Compare Price (Sale Price)
                    ty_price = Decimal(str(ty_p.get('salePrice', 0)))
                    local_price = local_p.selling_price
                    
                    # Compare Stock
                    ty_stock = int(ty_p.get('quantity', 0))
                    local_stock = local_p.stock_quantity
                    
                    price_diff = abs(ty_price - local_price) > Decimal('0.1')
                    stock_diff = ty_stock != local_stock
                    
                    if price_diff or stock_diff:
                        self.stdout.write(f"Mismatch for {barcode}: TY Price={ty_price}, Local={local_price} | TY Stock={ty_stock}, Local={local_stock}")
                        mismatched_items.append({
                            "barcode": barcode,
                            "quantity": local_stock,
                            "salePrice": float(local_price),
                            "listPrice": float(local_price)
                        })
                        
                total_checked += len(batch_barcodes)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error verifying batch: {e}"))
        
        if mismatched_items:
            self.stdout.write(self.style.WARNING(f"Found {len(mismatched_items)} mismatches. Sending correction..."))
            process.message += f" | {len(mismatched_items)} uyumsuzluk bulundu, düzeltiliyor..."
            process.save()
            
            results = service.update_price_and_inventory(mismatched_items)
            
            for res in results:
                if "batchRequestId" in res:
                    TrendyolBatchRequest.objects.create(
                        batch_request_id=res['batchRequestId'],
                        batch_type='ProductInventoryUpdate',
                        item_count=len(mismatched_items),
                        process=process
                    )
                    process.message += f" | Düzeltme Batch: {res['batchRequestId']}"
        else:
            self.stdout.write(self.style.SUCCESS("Verification complete. No mismatches found."))
            process.message += " | Doğrulama tamamlandı, fark yok."
        
        process.save()

    def sync_supplier(self, supplier, settings, process, target_skus=None):
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
        ty_commissions = {c.trendyol_id: c.commission_rate for c in TrendyolCategory.objects.all()}
        
        count_created = 0
        count_updated = 0
        processed_count = 0
        
        # İstatistikler
        stats = {
            'new_products': 0,
            'updated_products': 0,
            'price_changed': 0,
            'stock_increased': 0,
            'stock_decreased': 0,
            'total_stock_diff': 0,
            'stock_zeroed': 0,
            'trendyol_sent_items': 0,
            'trendyol_batch_id': None
        }

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
            
            # Filter by target SKUs if provided
            if target_skus and sku not in target_skus:
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
                if mapping.trendyol_category_id in ty_commissions:
                    commission_rate = ty_commissions[mapping.trendyol_category_id]
            
            # Calculate Selling Price
            try:
                new_selling_price = calculate_selling_price(
                    new_buying_price, 
                    settings, 
                    price_rules, 
                    commission_rate
                )
            except Exception as e:
                # If price calculation fails, and we need to zero stock
                if settings.zero_stock_on_error and sku in existing_products:
                    new_stock = 0
                    # Use existing price to avoid validation errors
                    new_selling_price = existing_products[sku].selling_price
                    self.stdout.write(self.style.WARNING(f"Price calc error for {sku}, zeroing stock: {e}"))
                else:
                    # Skip this item if we can't calculate price and it's not an existing item we can zero
                    continue

            if sku in existing_products:
                # UPDATE EXISTING PRODUCT
                product = existing_products[sku]
                
                # Check for changes
                stock_diff = new_stock - product.stock_quantity
                stock_changed = stock_diff != 0
                price_changed = abs(product.buying_price - new_buying_price) > Decimal('0.01')
                
                # Force update if we are zeroing due to error (implicit in new_stock=0)
                
                if stock_changed or price_changed:
                    if stock_changed:
                        if stock_diff > 0:
                            stats['stock_increased'] += 1
                        else:
                            stats['stock_decreased'] += 1
                        
                        if new_stock == 0:
                            stats['stock_zeroed'] += 1
                        
                        stats['total_stock_diff'] += stock_diff

                    if price_changed:
                        stats['price_changed'] += 1

                    product.stock_quantity = new_stock
                    product.buying_price = new_buying_price
                    product.selling_price = new_selling_price
                    product.save()
                    count_updated += 1
                    stats['updated_products'] += 1
                    
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

                # Handle Images
                # Image1, Image2... Image5
                for i in range(1, 6):
                    img_key = f'Image{i}'
                    img_url = item.get(img_key)
                    if img_url:
                        create_product_image(img_url, is_primary=(i==1))
                
                # RSS / Google Merchant Image Links
                img_link = item.get('image_link') or item.get('g:image_link')
                if img_link:
                     create_product_image(img_link, is_primary=True)
                
                # Additional Images
                for k, v in item.items():
                    if k.startswith('additional_image_link') or k.startswith('g:additional_image_link'):
                        if v:
                            create_product_image(v)

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
                            create_product_image(img_url)
                        elif isinstance(img_url, dict):
                             url = img_url.get('#text') or img_url.get('url')
                             if url:
                                 create_product_image(url)
                
                count_created += 1
                stats['new_products'] += 1

        self.stdout.write(self.style.SUCCESS(f"Sync complete. Created: {count_created}, Updated: {count_updated}"))
        process.message = f"Tamamlandı. Eklenen: {count_created}, Güncellenen: {count_updated}"
        process.processed_items = total_items
        process.details = stats
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
                        item_count=len(updated_items_payload), # This is approximate per batch
                        process=process
                    )
                    stats['trendyol_batch_id'] = res['batchRequestId']
                    stats['trendyol_sent_items'] = len(updated_items_payload)
                    process.details = stats
                    process.message = f"XML Tamamlandı. Trendyol'a {len(updated_items_payload)} ürün gönderildi (Batch: {res['batchRequestId']}). Sonuç bekleniyor..."
                    process.save()
                else:
                    self.stdout.write(self.style.ERROR(f"Error sending batch: {res}"))
                    process.message += f" | Trendyol Gönderim Hatası: {res}"
                    process.save()
        else:
            self.stdout.write("No changes detected for Trendyol.")
            process.message += " | Trendyol için değişiklik yok."
            process.save()

