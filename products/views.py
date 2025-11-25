from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.management import call_command
from django.db.models import Q
from django.urls import reverse
from .models import Product, Supplier, CategoryMapping, BrandMapping, SupplierSettings, PriceRule, CategoryAttributeMapping, TrendyolBatchRequest, TrendyolCategory, BackgroundProcess
from .forms import SupplierSettingsForm, PriceRuleForm
from integrations.services import TrendyolService
import random
import difflib
from django.http import JsonResponse
import math
import re

def parse_measurement(value_str):
    """
    Parses a measurement string (e.g. '3,3 LT', '1500 ml') and returns the value in a standard unit (e.g. Liters).
    Returns None if parsing fails.
    """
    if not value_str:
        return None
        
    value_str = str(value_str).replace('İ', 'i').replace('I', 'ı').lower()
    
    # Determine multiplier based on unit
    multiplier = 1.0
    if 'ml' in value_str or 'cc' in value_str:
        multiplier = 0.001 # Convert ml/cc to Liters
    elif 'lt' in value_str or 'litre' in value_str or 'l' in value_str:
        multiplier = 1.0
    
    # Extract numeric part
    # Remove everything except digits, comma, dot
    num_str = re.sub(r'[^\d,.]', '', value_str)
    if not num_str:
        return None
        
    try:
        # Handle 1.000,50 vs 1,5 formats
        # If comma is present and looks like decimal separator (e.g. 1,5 or 3,3)
        if ',' in num_str:
            if '.' in num_str:
                # Both present (e.g. 1.000,50) -> remove dot, replace comma
                num_str = num_str.replace('.', '').replace(',', '.')
            else:
                # Only comma -> replace with dot
                num_str = num_str.replace(',', '.')
        
        val = float(num_str)
        return val * multiplier
    except:
        return None

@login_required
def dashboard(request):
    total_products = Product.objects.count()
    published_products = Product.objects.filter(is_published_to_trendyol=True).count()
    pending_products = total_products - published_products
    total_suppliers = Supplier.objects.count()
    suppliers = Supplier.objects.all() # Tedarikçileri listelemek için
    recent_products = Product.objects.order_by('-created_at')[:5]

    context = {
        'total_products': total_products,
        'published_products': published_products,
        'pending_products': pending_products,
        'total_suppliers': total_suppliers,
        'suppliers': suppliers,
        'recent_products': recent_products,
    }
    return render(request, 'products/dashboard.html', context)

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    supplier_filter = request.GET.get('supplier', '')
    
    products = Product.objects.all().order_by('-created_at')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) | 
            Q(barcode__icontains=query)
        )
    
    if status == 'published':
        products = products.filter(is_published_to_trendyol=True)
    elif status == 'pending':
        products = products.filter(is_published_to_trendyol=False)

    if category_filter:
        products = products.filter(category_path=category_filter)
    
    if brand_filter:
        products = products.filter(brand=brand_filter)

    if supplier_filter:
        products = products.filter(supplier_id=supplier_filter)

    # Filtreleme seçenekleri için verileri çek
    categories = Product.objects.exclude(category_path__isnull=True).exclude(category_path='').values_list('category_path', flat=True).distinct().order_by('category_path')
    brands = Product.objects.exclude(brand__isnull=True).exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand')
    suppliers = Supplier.objects.all()

    paginator = Paginator(products, 20) # Sayfada 20 ürün
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'categories': categories,
        'brands': brands,
        'suppliers': suppliers,
        'selected_category': category_filter,
        'selected_brand': brand_filter,
        'selected_supplier': int(supplier_filter) if supplier_filter else None,
        'selected_status': status,
        'search_query': query
    }

    return render(request, 'products/product_list.html', context)

import subprocess
import sys

@login_required
def sync_xml(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id')
        
        if supplier_id:
            supplier = Supplier.objects.filter(id=supplier_id).first()
        else:
            # Eğer ID gelmezse (eski butonlar için) ilkini al
            supplier = Supplier.objects.first()
            
        if supplier:
            try:
                # Arka planda çalıştır
                subprocess.Popen([sys.executable, 'manage.py', 'auto_sync_stocks', '--supplier_id', str(supplier.id)])
                messages.success(request, f"{supplier.name} için XML çekme ve güncelleme işlemi arka planda başlatıldı. Ürün sayısına göre işlem sürebilir.")
            except Exception as e:
                messages.error(request, f"İşlem başlatılamadı: {str(e)}")
        else:
            messages.warning(request, "Kayıtlı tedarikçi bulunamadı.")
    
    # Geldiği sayfaya geri dön
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def send_bulk_trendyol(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_products')
        if not selected_ids:
            messages.warning(request, "Lütfen en az bir ürün seçin.")
            return redirect('product_list')

        products = Product.objects.filter(id__in=selected_ids)
        
        try:
            service = TrendyolService(user=request.user)
            result = service.create_products(products)
            
            if "batchRequestId" in result:
                messages.success(request, f"{len(products)} ürün Trendyol'a gönderildi. Batch ID: {result['batchRequestId']}")
                products.update(is_published_to_trendyol=True)
            elif result.get("status") == "error":
                messages.error(request, f"Hata: {result.get('message')}")
            else:
                messages.warning(request, f"Bilinmeyen yanıt: {result}")

        except Exception as e:
            messages.error(request, f"İşlem başlatılamadı: {str(e)}")

    return redirect('product_list')

@login_required
def search_trendyol_brands(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        service = TrendyolService(user=request.user)
        brands = service.search_brands(query)
        # API yanıtı: [{"id": 1, "name": "Marka"}, ...]
        return JsonResponse({'results': brands})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def search_trendyol_categories(request):
    query = request.GET.get('q', '').lower()
    
    try:
        service = TrendyolService(user=request.user)
        # Tüm ağacı çek (Cache mekanizması eklenebilir)
        tree = service.get_category_tree()
        
        # Ağacı düzleştir ve ara
        results = []
        
        def traverse(categories):
            for cat in categories:
                if query in cat['name'].lower():
                    results.append({'id': cat['id'], 'name': cat['name']})
                if cat.get('subCategories'):
                    traverse(cat['subCategories'])
        
        if 'categories' in tree:
             traverse(tree['categories'])
        elif isinstance(tree, list): # Bazen direkt liste dönebilir
             traverse(tree)
             
        return JsonResponse({'results': results[:50]}) # Max 50 sonuç
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def match_categories(request):
    suppliers = Supplier.objects.all()
    selected_supplier_id = request.GET.get('supplier_id')
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all') # all, matched, unmatched
    
    products = Product.objects.exclude(category_path__isnull=True).exclude(category_path='')
    
    if selected_supplier_id:
        products = products.filter(supplier_id=selected_supplier_id)
        
    # 1. Get distinct categories
    xml_categories = products.values_list('category_path', flat=True).distinct().order_by('category_path')
    
    # 2. Apply Search
    if search_query:
        xml_categories = xml_categories.filter(category_path__icontains=search_query)

    # 3. Get Mappings
    # We fetch all mappings to determine status efficiently
    all_mappings = {m.xml_category_name: m for m in CategoryMapping.objects.all()}
    mapped_names = set(all_mappings.keys())
    
    # 4. Apply Status Filter
    if status_filter == 'matched':
        # Filter in Python because we have the list of mapped names
        # But xml_categories is a QuerySet. We can use __in
        xml_categories = xml_categories.filter(category_path__in=mapped_names)
    elif status_filter == 'unmatched':
        xml_categories = xml_categories.exclude(category_path__in=mapped_names)

    # 5. Pagination
    paginator = Paginator(xml_categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 6. Prepare Data for Current Page
    page_items = []
    
    # Pre-fetch Trendyol Categories for commission calculation (Optimization)
    # We only need this for mapped items on the current page
    current_page_mappings = [all_mappings[cat] for cat in page_obj if cat in all_mappings]
    
    # Collect IDs and Names to fetch
    ty_ids = [m.trendyol_category_id for m in current_page_mappings if m.trendyol_category_id]
    ty_names = [m.trendyol_category_name for m in current_page_mappings if m.trendyol_category_name]
    
    ty_cats_by_id = {c.trendyol_id: c for c in TrendyolCategory.objects.filter(trendyol_id__in=ty_ids)}
    # For names, it's harder to exact match in bulk due to " > " logic, but we can try
    # We'll fetch all potentially relevant ones or just rely on the loop logic which is fine for 20 items.
    
    # Varsayılan komisyon
    default_commission = 0
    if selected_supplier_id:
        try:
            settings = SupplierSettings.objects.get(supplier_id=selected_supplier_id)
            default_commission = settings.default_commission_rate
        except SupplierSettings.DoesNotExist:
            pass

    # Helper for commission (simplified version of previous logic)
    def get_commission(mapping):
        if not mapping: return None
        
        # 1. ID Match
        if mapping.trendyol_category_id in ty_cats_by_id:
            return ty_cats_by_id[mapping.trendyol_category_id].commission_rate
            
        # 2. Name Match (DB query per item - acceptable for 20 items)
        if mapping.trendyol_category_name:
            t_cat = TrendyolCategory.objects.filter(name__iexact=mapping.trendyol_category_name).first()
            if not t_cat:
                t_cat = TrendyolCategory.objects.filter(name__iendswith=f" > {mapping.trendyol_category_name}").first()
            if t_cat:
                return t_cat.commission_rate
        
        return None

    for cat_path in page_obj:
        mapping = all_mappings.get(cat_path)
        commission = None
        is_default_commission = False
        
        if mapping:
            commission = get_commission(mapping)
            if commission is None and default_commission > 0:
                commission = default_commission
                is_default_commission = True
                
        page_items.append({
            'xml_path': cat_path,
            'mapping': mapping,
            'commission_rate': commission,
            'is_default_commission': is_default_commission
        })

    if request.method == 'POST':
        if 'delete_mapping' in request.POST:
            mapping_id = request.POST.get('delete_mapping')
            CategoryMapping.objects.filter(id=mapping_id).delete()
            messages.success(request, "Eşleştirme silindi.")
            # Redirect keeping filters
            base_url = request.path
            query_string = request.GET.urlencode()
            return redirect(f"{base_url}?{query_string}")
        
        if 'delete_all_mappings' in request.POST:
            CategoryMapping.objects.all().delete()
            messages.success(request, "Tüm kategori eşleştirmeleri silindi.")
            return redirect(request.path)
            
        # Save Mappings
        saved_count = 0
        for item in page_items:
            cat = item['xml_path']
            # Check if this row has data submitted
            trendyol_id = request.POST.get(f'cat_{cat}') # Note: cat string might have special chars, handle in template?
            # Actually, using loop counter in template is safer for IDs
            # But here we need to know which one.
            # Let's use a hidden input with the xml path in the form row.
            
            # Alternative: The form submits `cat_ID` where ID is the loop counter? No, stateless.
            # The template uses `cat_{{ cat }}`. If `cat` has spaces, it's fine in POST data keys usually.
            # But `.` or special chars might be tricky.
            # Let's rely on the fact that we are iterating the same `page_items`.
            
            # Wait, the POST request might not have the same pagination context if not passed carefully?
            # No, the form is submitted to the same URL with GET params, so `page_obj` is same.
            
            trendyol_id = request.POST.get(f'cat_id_{cat}') # I will change template to use this key
            trendyol_name = request.POST.get(f'cat_name_{cat}')
            
            if trendyol_id and not item['mapping']: # Only create if not exists (or update?)
                CategoryMapping.objects.create(
                    xml_category_name=cat, 
                    trendyol_category_id=trendyol_id,
                    trendyol_category_name=trendyol_name
                )
                saved_count += 1
        
        if saved_count > 0:
            messages.success(request, f"{saved_count} kategori eşleştirmesi kaydedildi.")
            
        base_url = request.path
        query_string = request.GET.urlencode()
        return redirect(f"{base_url}?{query_string}")

    return render(request, 'products/match_categories.html', {
        'page_items': page_items,
        'page_obj': page_obj,
        'suppliers': suppliers,
        'selected_supplier_id': int(selected_supplier_id) if selected_supplier_id else None,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': paginator.count
    })

@login_required
def match_brands(request):
    suppliers = Supplier.objects.all()
    selected_supplier_id = request.GET.get('supplier_id')

    products = Product.objects.exclude(brand__isnull=True).exclude(brand='')
    
    if selected_supplier_id:
        products = products.filter(supplier_id=selected_supplier_id)

    xml_brands = products.values_list('brand', flat=True).distinct()
    
    existing_mappings = BrandMapping.objects.all()
    mapped_names = [m.xml_brand_name for m in existing_mappings]
    
    missing_brands = [b for b in xml_brands if b not in mapped_names]

    if request.method == 'POST':
        if 'delete_mapping' in request.POST:
            mapping_id = request.POST.get('delete_mapping')
            BrandMapping.objects.filter(id=mapping_id).delete()
            messages.success(request, "Eşleştirme silindi.")
            return redirect(f"{request.path}?supplier_id={selected_supplier_id}" if selected_supplier_id else request.path)

        if 'delete_all_mappings' in request.POST:
            BrandMapping.objects.all().delete()
            messages.success(request, "Tüm marka eşleştirmeleri silindi.")
            return redirect(f"{request.path}?supplier_id={selected_supplier_id}" if selected_supplier_id else request.path)

        for brand in missing_brands:
            trendyol_id = request.POST.get(f'brand_{brand}')
            if trendyol_id:
                BrandMapping.objects.create(xml_brand_name=brand, trendyol_brand_id=trendyol_id)
        messages.success(request, "Marka eşleştirmeleri kaydedildi.")
        return redirect(f"{request.path}?supplier_id={selected_supplier_id}" if selected_supplier_id else request.path)

    return render(request, 'products/match_brands.html', {
        'missing_brands': missing_brands,
        'existing_mappings': existing_mappings,
        'suppliers': suppliers,
        'selected_supplier_id': int(selected_supplier_id) if selected_supplier_id else None
    })

@login_required
def supplier_settings(request):
    suppliers = Supplier.objects.all()
    selected_supplier_id = request.GET.get('supplier_id')
    
    if not selected_supplier_id and suppliers.exists():
        selected_supplier_id = suppliers.first().id
        
    selected_supplier = None
    form = None
    price_rules = None
    preview_products = []
    
    if selected_supplier_id:
        selected_supplier = Supplier.objects.get(id=selected_supplier_id)
        settings, created = SupplierSettings.objects.get_or_create(supplier=selected_supplier)
        price_rules = PriceRule.objects.filter(supplier=selected_supplier).order_by('min_price')
        
        if request.method == 'POST':
            if 'save_settings' in request.POST:
                form = SupplierSettingsForm(request.POST, instance=settings)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Ayarlar başarıyla kaydedildi.")
                    return redirect(f"{reverse('supplier_settings')}?supplier_id={selected_supplier_id}")
            
            elif 'save_rule' in request.POST:
                rule_id = request.POST.get('edit_rule_id')
                if rule_id:
                    try:
                        rule_instance = PriceRule.objects.get(id=rule_id, supplier=selected_supplier)
                        rule_form = PriceRuleForm(request.POST, instance=rule_instance)
                        msg = "Fiyat kuralı güncellendi."
                    except PriceRule.DoesNotExist:
                        messages.error(request, "Düzenlenecek kural bulunamadı.")
                        return redirect(f"{reverse('supplier_settings')}?supplier_id={selected_supplier_id}")
                else:
                    rule_form = PriceRuleForm(request.POST)
                    msg = "Fiyat kuralı eklendi."

                if rule_form.is_valid():
                    rule = rule_form.save(commit=False)
                    rule.supplier = selected_supplier
                    rule.save()
                    messages.success(request, msg)
                    return redirect(f"{reverse('supplier_settings')}?supplier_id={selected_supplier_id}")
                else:
                    messages.error(request, "Kural kaydedilirken hata oluştu.")
            
            elif 'delete_rule' in request.POST:
                rule_id = request.POST.get('rule_id')
                PriceRule.objects.filter(id=rule_id, supplier=selected_supplier).delete()
                messages.success(request, "Fiyat kuralı silindi.")
                return redirect(f"{reverse('supplier_settings')}?supplier_id={selected_supplier_id}")

        else:
            form = SupplierSettingsForm(instance=settings)
        
        # Preview Logic
        sample_products = Product.objects.filter(supplier=selected_supplier)[:5]
        
        # Cache mappings for preview
        cat_paths = [p.category_path for p in sample_products if p.category_path]
        cat_mappings = {m.xml_category_name: m for m in CategoryMapping.objects.filter(xml_category_name__in=cat_paths)}
        
        # Load all commissions
        all_commissions = list(TrendyolCategory.objects.all())

        for p in sample_products:
            cost = p.buying_price if p.buying_price > 0 else p.selling_price
            
            commission_rate = 0
            if p.category_path in cat_mappings:
                mapping = cat_mappings[p.category_path]
                # Try ID match
                for c in all_commissions:
                    if c.trendyol_id == mapping.trendyol_category_id:
                        commission_rate = c.commission_rate
                        break
                else:
                    # Name match fallback
                    if mapping.trendyol_category_name:
                        for c in all_commissions:
                             if c.name.endswith(f" > {mapping.trendyol_category_name}") or c.name == mapping.trendyol_category_name:
                                commission_rate = c.commission_rate
                                break

            new_price = calculate_selling_price(cost, settings, price_rules, commission_rate)
            preview_products.append({
                'name': p.name,
                'sku': p.sku,
                'cost': cost,
                'new_price': new_price
            })
            
    return render(request, 'products/supplier_settings.html', {
        'suppliers': suppliers,
        'selected_supplier': selected_supplier,
        'form': form,
        'price_rules': price_rules,
        'rule_form': PriceRuleForm(),
        'preview_products': preview_products
    })

@login_required
def publish_wizard(request):
    suppliers = Supplier.objects.all()
    
    # Filtreleme Parametreleri
    supplier_id = request.GET.get('supplier_id')
    category_filter = request.GET.get('category')
    brand_filter = request.GET.get('brand')
    search_query = request.GET.get('q')
    
    # Varsayılan olarak ilk tedarikçiyi seç
    if not supplier_id and suppliers.exists():
        supplier_id = suppliers.first().id
    
    products = Product.objects.filter(stock_quantity__gt=0, is_published_to_trendyol=False)
    
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)
        
    if category_filter:
        products = products.filter(category_path__icontains=category_filter)
        
    if brand_filter:
        products = products.filter(brand__icontains=brand_filter)
        
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(sku__icontains=search_query) |
            Q(barcode__icontains=search_query)
        )

    # Filtreleme seçenekleri için listeler (Sadece mevcut tedarikçinin ürünlerinden)
    filter_base_products = Product.objects.filter(supplier_id=supplier_id) if supplier_id else Product.objects.all()
    categories = filter_base_products.values_list('category_path', flat=True).distinct().order_by('category_path')
    brands = filter_base_products.values_list('brand', flat=True).distinct().order_by('brand')

    if request.method == 'POST':
        # Gönderim İşlemi
        send_all = request.POST.get('send_all') == 'true'
        selected_ids = request.POST.getlist('selected_products')
        
        products_to_send = []
        
        if send_all:
            # Filtrelenmiş tüm ürünleri al (POST'ta filtreleri tekrar uygulamak gerekebilir veya hidden input ile taşımak)
            # Basitlik için: Eğer 'send_all' ise, o anki filtre kriterlerine uyanları tekrar sorgula
            # Ancak güvenli olan, filtreleri form içinde hidden olarak taşımaktır.
            # Burada tekrar filtreleme yapalım:
            products_to_send = Product.objects.filter(stock_quantity__gt=0, is_published_to_trendyol=False)
            if supplier_id: products_to_send = products_to_send.filter(supplier_id=supplier_id)
            if category_filter: products_to_send = products_to_send.filter(category_path__icontains=category_filter)
            if brand_filter: products_to_send = products_to_send.filter(brand__icontains=brand_filter)
            if search_query: products_to_send = products_to_send.filter(Q(name__icontains=search_query) | Q(sku__icontains=search_query))
        else:
            if not selected_ids:
                messages.warning(request, "Lütfen en az bir ürün seçin.")
                return redirect(f"{request.path}?supplier_id={supplier_id}")
            products_to_send = Product.objects.filter(id__in=selected_ids)
        
        # Tedarikçi Ayarlarını Al
        supplier_settings = None
        price_rules = []
        if supplier_id:
            try:
                supplier_settings = SupplierSettings.objects.get(supplier_id=supplier_id)
                price_rules = list(PriceRule.objects.filter(supplier_id=supplier_id).order_by('min_price'))
            except SupplierSettings.DoesNotExist:
                pass # Varsayılanları kullan veya hata ver
        
        use_unique_barcode = supplier_settings.use_unique_barcode if supplier_settings else False
        min_stock = supplier_settings.min_stock if supplier_settings else 0
        sku_prefix = supplier_settings.sku_prefix if supplier_settings else ""

        # Eşleştirme Kontrolü
        unmapped_cats = []
        unmapped_brands = []
        
        valid_products = []
        
        for p in products_to_send:
            # Stok kontrolü
            if p.stock_quantity < min_stock:
                continue

            # Eşleştirme Kontrolü (Sadece eşleşmişleri al)
            is_mapped = True
            if p.category_path and not CategoryMapping.objects.filter(xml_category_name=p.category_path).exists():
                unmapped_cats.append(p.category_path)
                is_mapped = False
            if p.brand and not BrandMapping.objects.filter(xml_brand_name=p.brand).exists():
                unmapped_brands.append(p.brand)
                is_mapped = False
            
            if is_mapped:
                valid_products.append(p)
        
        if unmapped_cats or unmapped_brands:
            messages.warning(request, f"{len(unmapped_cats)} kategori ve {len(unmapped_brands)} marka eşleşmediği için bu ürünler atlandı. Sadece eşleşmiş {len(valid_products)} ürün gönderiliyor.")
            # Redirect etmiyoruz, devam ediyoruz.

        if not valid_products:
             messages.warning(request, "Gönderilecek uygun ürün bulunamadı (Stok yetersiz veya eşleşme yok).")
             return redirect(f"{request.path}?supplier_id={supplier_id}")

        # Gönderim Hazırlığı
        service = TrendyolService(user=request.user)
        prepared_items = []
        
        # Attribute Mappings Cache
        cat_attr_mappings = {} # {xml_cat_name: [mappings]}
        # Cache for Trendyol Attribute Values (for smart matching)
        # Key: trendyol_category_id, Value: { attr_id: [ {id, name}, ... ] }
        ty_cat_attributes_cache = {}
        
        # Cache mappings for commission calculation
        cat_paths = [p.category_path for p in valid_products if p.category_path]
        cat_mappings_cache = {m.xml_category_name: m for m in CategoryMapping.objects.filter(xml_category_name__in=cat_paths)}
        
        # Load all commissions
        all_commissions = list(TrendyolCategory.objects.all())

        for p in valid_products:
            # Fiyat Hesapla
            cost = float(p.buying_price) if p.buying_price > 0 else float(p.selling_price)
            
            commission_rate = 0
            if p.category_path in cat_mappings_cache:
                mapping = cat_mappings_cache[p.category_path]
                # Try ID match
                for c in all_commissions:
                    if c.trendyol_id == mapping.trendyol_category_id:
                        commission_rate = c.commission_rate
                        break
                else:
                    # Name match fallback
                    if mapping.trendyol_category_name:
                        for c in all_commissions:
                             if c.name.endswith(f" > {mapping.trendyol_category_name}") or c.name == mapping.trendyol_category_name:
                                commission_rate = c.commission_rate
                                break

            if supplier_settings:
                p.selling_price = calculate_selling_price(cost, supplier_settings, price_rules, commission_rate)
            else:
                # Fallback if no settings
                p.selling_price = round(cost * 1.2, 2)
            
            # Barkod
            if use_unique_barcode or not p.barcode:
                p.barcode = f"TY-{p.sku}-{random.randint(1000,9999)}"
            
            # SKU Prefix
            if sku_prefix and not p.sku.startswith(sku_prefix):
                p.sku = f"{sku_prefix}{p.sku}"

            # Mappingleri al
            cat_map = CategoryMapping.objects.filter(xml_category_name=p.category_path).first()
            brand_map = BrandMapping.objects.filter(xml_brand_name=p.brand).first()
            
            if cat_map: p.trendyol_category_id = cat_map.trendyol_category_id
            if brand_map: p.trendyol_brand_id = brand_map.trendyol_brand_id
            
            p.save()

            # Attributes Hazırla
            attributes = []
            if p.category_path:
                if p.category_path not in cat_attr_mappings:
                    cat_attr_mappings[p.category_path] = list(CategoryAttributeMapping.objects.filter(category_mapping__xml_category_name=p.category_path))
                
                mappings = cat_attr_mappings[p.category_path]
                
                # Cache Trendyol Attributes for this category (Always fetch to support Text->ID lookup and Required check)
                if p.trendyol_category_id not in ty_cat_attributes_cache:
                    try:
                        ty_resp = service.get_category_attributes(p.trendyol_category_id)
                        attr_values_map = {}
                        required_set = set()
                        for attr in ty_resp.get('categoryAttributes', []):
                            attr_id = attr['attribute']['id']
                            values = attr.get('attributeValues', [])
                            attr_values_map[attr_id] = values
                            if attr.get('required'):
                                required_set.add(attr_id)
                        
                        ty_cat_attributes_cache[p.trendyol_category_id] = {
                            'values': attr_values_map,
                            'required': required_set
                        }
                    except:
                        ty_cat_attributes_cache[p.trendyol_category_id] = {'values': {}, 'required': set()}

                cache_entry = ty_cat_attributes_cache.get(p.trendyol_category_id, {})
                all_values_map = cache_entry.get('values', {})
                required_ids = cache_entry.get('required', set())

                def tr_lower(s):
                    return s.replace('İ', 'i').replace('I', 'ı').lower()

                for m in mappings:
                    attr_val = None
                    # Get allowed values for this attribute
                    allowed_values = all_values_map.get(m.trendyol_attribute_id, [])

                    if m.mapping_type == 'fixed':
                        attr_val = m.static_value
                    elif m.mapping_type == 'xml' and m.xml_attribute_name:
                        attr_val = p.attributes.get(m.xml_attribute_name)
                    elif m.mapping_type == 'smart':
                        # Akıllı Eşleştirme Mantığı
                        search_text = tr_lower(f"{p.name} {p.description}")
                        for val in allowed_values:
                            val_name = val['name']
                            if tr_lower(val_name) in search_text:
                                attr_val = val['id']
                                break 
                    
                    # Text -> ID Lookup (Fix for "Invalid Value" errors)
                    if attr_val and not str(attr_val).isdigit() and allowed_values:
                        attr_val_original = attr_val # Keep original for parsing

                        text_val = tr_lower(str(attr_val))
                        # Remove units
                        for unit in ['lt', 'litre', 'ml', 'parça', 'adet', 'cm', 'mm']:
                            text_val = text_val.replace(unit, '')
                        text_val = text_val.strip()
                        
                        for av in allowed_values:
                            av_name = tr_lower(av['name'])
                            av_name_clean = av_name
                            for unit in ['lt', 'litre', 'ml', 'parça', 'adet', 'cm', 'mm']:
                                av_name_clean = av_name_clean.replace(unit, '')
                            av_name_clean = av_name_clean.strip()
                            
                            if av_name == text_val or av_name_clean == text_val:
                                attr_val = av['id']
                                break
                            # Try replacing comma with dot for decimal numbers (1,5 -> 1.5)
                            if text_val.replace(',', '.') == av_name_clean.replace(',', '.'):
                                attr_val = av['id']
                                break
                        
                        # 3. Numeric Proximity Match (for Volume/Hacim etc.)
                        if not str(attr_val).isdigit():
                            xml_val_parsed = parse_measurement(str(attr_val_original)) # Use original value with units
                            if xml_val_parsed is not None:
                                best_match_id = None
                                min_diff = float('inf')
                                
                                for av in allowed_values:
                                    av_parsed = parse_measurement(av['name'])
                                    if av_parsed is not None:
                                        diff = abs(xml_val_parsed - av_parsed)
                                        if diff < min_diff:
                                            min_diff = diff
                                            best_match_id = av['id']
                                
                                # Tolerance: 0.1 Liters (100ml)
                                if best_match_id and min_diff <= 0.1:
                                    attr_val = best_match_id

                    if attr_val:
                        attr_item = {"attributeId": m.trendyol_attribute_id}
                        if str(attr_val).isdigit():
                             attr_item["attributeValueId"] = int(attr_val)
                        else:
                             attr_item["customAttributeValue"] = str(attr_val)
                        attributes.append(attr_item)

                # Auto-Fill Missing Required Attributes (Fallback)
                mapped_ids = set(a['attributeId'] for a in attributes)
                missing_required = required_ids - mapped_ids
                
                for req_id in missing_required:
                    # Try Smart Match for missing required attribute
                    allowed_values = all_values_map.get(req_id, [])
                    found_val = None
                    
                    search_text = tr_lower(f"{p.name} {p.description}")
                    for val in allowed_values:
                        if tr_lower(val['name']) in search_text:
                            found_val = val['id']
                            break
                    
                    # Fallback: If Color (Renk) is missing, try to use 'Çok Renkli' or 'Diğer'
                    if not found_val:
                        # Öncelikli güvenli değerler
                        safe_defaults = ['çok renkli', 'karışık', 'diğer', 'belirtilmemiş', 'gümüş', 'metalik', 'tek renk', 'standart']
                        
                        for val in allowed_values:
                            v_name = tr_lower(val['name'])
                            if v_name in safe_defaults:
                                found_val = val['id']
                                break
                    
                    # Last Resort: Eğer hala bulunamadıysa ve zorunluysa, listenin ilk elemanını seç
                    # Bu, ürünün hata alıp reddedilmesindense, yanlış özellikle de olsa oluşturulmasını sağlar.
                    # Kullanıcı daha sonra düzeltebilir.
                    if not found_val and allowed_values:
                         found_val = allowed_values[0]['id']

                    if found_val:
                        attributes.append({"attributeId": req_id, "attributeValueId": found_val})

            # Resimler
            image_urls = [img.image_url for img in p.images.all()]
            if not image_urls:
                continue

            item = {
                "barcode": p.barcode,
                "title": p.name[:100],
                "productMainId": p.model_code if p.model_code else p.sku, # Varyant Grubu
                "brandId": p.trendyol_brand_id,
                "categoryId": p.trendyol_category_id,
                "quantity": p.stock_quantity,
                "stockCode": p.sku,
                "dimensionalWeight": 1,
                "description": p.description,
                "currencyType": "TRY",
                "listPrice": float(p.selling_price),
                "salePrice": float(p.selling_price),
                "vatRate": 20, # Varsayılan
                "cargoCompanyId": 10,
                "images": [{"url": url} for url in image_urls],
                "attributes": attributes
            }
            prepared_items.append(item)
            
        try:
            result = service.create_products(prepared_items)
            
            if "batchRequestId" in result:
                batch_id = result['batchRequestId']
                messages.success(request, f"{len(prepared_items)} ürün Trendyol'a gönderildi. Batch ID: {batch_id}")
                
                # Save Batch Request
                TrendyolBatchRequest.objects.create(
                    batch_request_id=batch_id,
                    batch_type='ProductV2OnBoarding',
                    item_count=len(prepared_items)
                )

                # Sadece gönderilenleri güncelle
                sent_barcodes = [item['barcode'] for item in prepared_items]
                Product.objects.filter(barcode__in=sent_barcodes).update(is_published_to_trendyol=True)
            elif result.get("status") == "error":
                messages.error(request, f"Hata: {result.get('message')} - {result.get('details')}")
            else:
                messages.warning(request, f"Bilinmeyen yanıt: {result}")
        except Exception as e:
             messages.error(request, f"API Hatası: {str(e)}")
            
        return redirect('product_list')

    # Pagination
    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/publish_wizard.html', {
        'products': page_obj,
        'suppliers': suppliers,
        'selected_supplier_id': int(supplier_id) if supplier_id else None,
        'categories': categories,
        'brands': brands,
        'selected_category': category_filter,
        'selected_brand': brand_filter,
        'search_query': search_query
    })

@login_required
def auto_match_categories(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id')
        
        # 1. Eşleşmemiş kategorileri bul
        products = Product.objects.exclude(category_path__isnull=True).exclude(category_path='')
        if supplier_id:
            products = products.filter(supplier_id=supplier_id)
            
        xml_categories = products.values_list('category_path', flat=True).distinct()
        existing_mappings = CategoryMapping.objects.values_list('xml_category_name', flat=True)
        missing_categories = [c for c in xml_categories if c not in existing_mappings]
        
        if not missing_categories:
            messages.info(request, "Eşleştirilecek yeni kategori bulunamadı.")
            return redirect('match_categories')

        # 2. Trendyol Kategori Ağacını Çek ve Düzleştir
        try:
            service = TrendyolService(user=request.user)
            tree = service.get_category_tree()
            
            trendyol_cats_flat = []
            def flatten_cats(cats):
                for c in cats:
                    trendyol_cats_flat.append({'id': c['id'], 'name': c['name']})
                    if c.get('subCategories'):
                        flatten_cats(c['subCategories'])
            
            if 'categories' in tree:
                flatten_cats(tree['categories'])
            elif isinstance(tree, list):
                flatten_cats(tree)
                
            # İsim -> ID haritası (Hızlı erişim için)
            ty_cat_map = {c['name'].lower(): {'id': c['id'], 'name': c['name']} for c in trendyol_cats_flat}
            ty_cat_names = list(ty_cat_map.keys())
            
        except Exception as e:
            messages.error(request, f"Trendyol kategorileri alınamadı: {str(e)}")
            return redirect('match_categories')

        # 3. Eşleştirme Algoritması
        matched_count = 0
        
        for xml_cat in missing_categories:
            # XML kategorisinin son parçasını al (Örn: "Giyim > Kadın > Elbise" -> "Elbise")
            # Genelde en anlamlı kısım sondadır.
            search_term = xml_cat.split('>')[-1].strip().lower()
            
            # 1. Tam Eşleşme Kontrolü
            if search_term in ty_cat_map:
                match_data = ty_cat_map[search_term]
                CategoryMapping.objects.create(
                    xml_category_name=xml_cat, 
                    trendyol_category_id=match_data['id'],
                    trendyol_category_name=match_data['name']
                )
                matched_count += 1
                continue
                
            # 2. Benzerlik Araması (Fuzzy Match)
            # cutoff=0.7 -> %70 benzerlik
            matches = difflib.get_close_matches(search_term, ty_cat_names, n=1, cutoff=0.7)
            
            if matches:
                best_match_key = matches[0]
                match_data = ty_cat_map[best_match_key]
                CategoryMapping.objects.create(
                    xml_category_name=xml_cat, 
                    trendyol_category_id=match_data['id'],
                    trendyol_category_name=match_data['name']
                )
                matched_count += 1
        
        if matched_count > 0:
            messages.success(request, f"{matched_count} kategori otomatik olarak eşleştirildi.")
        else:
            messages.warning(request, "Otomatik eşleştirme ile uygun kategori bulunamadı.")
            
        return redirect(f"{reverse('match_categories')}?supplier_id={supplier_id}" if supplier_id else 'match_categories')
    
    return redirect('match_categories')

@login_required
def map_attributes(request, mapping_id):
    mapping = CategoryMapping.objects.get(id=mapping_id)
    
    # 1. Trendyol Özelliklerini Çek
    try:
        service = TrendyolService(user=request.user)
        # Trendyol API'den özellikleri al
        ty_attributes_response = service.get_category_attributes(mapping.trendyol_category_id)
        all_attributes = ty_attributes_response.get('categoryAttributes', [])
    except Exception as e:
        messages.error(request, f"Trendyol özellikleri alınamadı: {str(e)}")
        return redirect('match_categories')

    required_attributes = [attr for attr in all_attributes if attr.get('required')]
    optional_attributes = [attr for attr in all_attributes if not attr.get('required')]

    # 2. Mevcut Eşleşmeleri Çek
    existing_mappings = CategoryAttributeMapping.objects.filter(category_mapping=mapping)
    mapped_dict = {m.trendyol_attribute_id: m for m in existing_mappings}

    # 3. XML'den gelen örnek özellikleri bul (Kullanıcıya kolaylık olsun diye)
    # Bu kategorideki ürünlerden örnek attribute key'leri topla
    sample_products = Product.objects.filter(category_path=mapping.xml_category_name)[:10]
    xml_keys = set()
    for p in sample_products:
        if p.attributes:
            if isinstance(p.attributes, dict):
                xml_keys.update(p.attributes.keys())
            # Eğer string olarak gelirse (eski kayıtlar vs)
            elif isinstance(p.attributes, str):
                pass 
    
    xml_keys = sorted(list(xml_keys))

    if request.method == 'POST':
        # Form verilerini işle
        for attr in all_attributes:
            attr_id = attr['attribute']['id']
            attr_name = attr['attribute']['name']
            
            mapping_type = request.POST.get(f'type_{attr_id}')
            value = request.POST.get(f'value_{attr_id}')
            is_varianter = request.POST.get(f'varianter_{attr_id}') == 'on'
            is_slicer = request.POST.get(f'slicer_{attr_id}') == 'on'
            
            if mapping_type and value:
                CategoryAttributeMapping.objects.update_or_create(
                    category_mapping=mapping,
                    trendyol_attribute_id=attr_id,
                    defaults={
                        'trendyol_attribute_name': attr_name,
                        'mapping_type': mapping_type,
                        'static_value': value if mapping_type == 'fixed' else None,
                        'xml_attribute_name': value if mapping_type == 'xml' else None,
                        'is_varianter': is_varianter,
                        'is_slicer': is_slicer
                    }
                )
            else:
                # Eğer boş gönderildiyse ve veritabanında varsa sil (Opsiyonel)
                pass
                
        messages.success(request, "Özellik eşleştirmeleri kaydedildi.")
        return redirect('match_categories')

    return render(request, 'products/map_attributes.html', {
        'mapping': mapping,
        'required_attributes': required_attributes,
        'optional_attributes': optional_attributes,
        'mapped_dict': mapped_dict,
        'xml_keys': xml_keys
    })

@login_required
def delete_products_from_trendyol(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_products')
        action_type = request.POST.get('action_type', 'delete_api') # 'delete_api' or 'reset_local'

        if not selected_ids:
            messages.warning(request, "Lütfen en az bir ürün seçin.")
            return redirect('product_list')

        products = Product.objects.filter(id__in=selected_ids)
        barcodes = [p.barcode for p in products if p.barcode]

        if action_type == 'delete_api':
            try:
                service = TrendyolService(user=request.user)
                result = service.delete_products(barcodes)
                
                if "batchRequestId" in result:
                    batch_id = result['batchRequestId']
                    messages.success(request, f"{len(barcodes)} ürün için silme talebi gönderildi. Batch ID: {batch_id}")
                    
                    # Save Batch Request
                    TrendyolBatchRequest.objects.create(
                        batch_request_id=batch_id,
                        batch_type='ProductDeletion',
                        item_count=len(barcodes)
                    )
                    
                    # Update local status immediately
                    products.update(is_published_to_trendyol=False)
                    
                elif result.get("status") == "error":
                    messages.error(request, f"Hata: {result.get('message')} - {result.get('details')}")
                else:
                    messages.warning(request, f"Bilinmeyen yanıt: {result}")

            except Exception as e:
                messages.error(request, f"İşlem başlatılamadı: {str(e)}")
        
        elif action_type == 'reset_local':
            products.update(is_published_to_trendyol=False)
            messages.success(request, f"{len(products)} ürünün durumu 'Yayında Değil' olarak güncellendi.")

    return redirect('product_list')

def calculate_selling_price(cost, settings, rules, commission_rate=0):
    cost = float(cost)
    
    # 1. Price Rules (Fiyat Kuralları) - Öncelikli
    # Eğer kural varsa, direkt kuralı uygula ve çık (Basit mantık)
    # VEYA kuralı maliyet üzerine uygula, sonra diğer maliyetleri ekle?
    # Mevcut yapıda kural direkt fiyatı belirliyordu. Ancak yeni maliyet yapısıyla
    # kuralın "hedef kar marjı" gibi davranması daha doğru olabilir ama
    # şimdilik eski mantığı koruyup, kural yoksa detaylı hesaplamaya geçelim.
    
    matched_rule = None
    for rule in rules:
        if float(rule.min_price) <= cost < float(rule.max_price):
            matched_rule = rule
            break
            
    if matched_rule:
        val = float(matched_rule.value)
        extra = float(matched_rule.extra_cost)
        
        final_price = cost
        if matched_rule.operation_type == 'percentage':
            if matched_rule.rule_type == 'increase':
                final_price = cost * (1 + val / 100)
            else:
                final_price = cost * (1 - val / 100)
        else: # Fixed
            if matched_rule.rule_type == 'increase':
                final_price = cost + val
            else:
                final_price = cost - val
        
        final_price += extra
        
        # Kural uygulansa bile KDV/Komisyon eklenebilir mi?
        # Kullanıcı "kural" ile genellikle son fiyatı manipüle etmek ister.
        # Ancak "Trendyol Komisyonunu Dahil Et" seçeneği varsa, kuraldan çıkan fiyata eklenmeli.
        
        if getattr(settings, 'include_trendyol_commission', False):
            effective_rate = float(commission_rate) if commission_rate > 0 else float(getattr(settings, 'default_commission_rate', 0))
            if effective_rate > 0:
                rate = effective_rate / 100
                if rate < 1:
                    final_price = final_price / (1 - rate)
                    
        if settings.price_rounding:
            final_price = math.floor(final_price) + 0.99
            
        return round(final_price, 2)

    # 2. Detaylı Maliyet Hesabı (Kural Yoksa)
    
    # Parametreler
    margin = float(settings.profit_margin) / 100
    shipping_cost_gross = float(settings.shipping_cost)
    service_fee_gross = float(getattr(settings, 'service_fee', 10.19))
    withholding_rate = float(getattr(settings, 'withholding_tax_rate', 1.0)) / 100
    
    buying_includes_vat = getattr(settings, 'buying_price_includes_vat', True)
    buying_vat_rate = float(getattr(settings, 'buying_vat_rate', 20.0)) / 100
    selling_vat_rate = float(getattr(settings, 'selling_vat_rate', 20.0)) / 100
    
    # Komisyon Oranı
    comm_rate = 0
    if getattr(settings, 'include_trendyol_commission', False):
        comm_rate = float(commission_rate) if commission_rate > 0 else float(getattr(settings, 'default_commission_rate', 0))
        comm_rate = comm_rate / 100

    # A. Net Maliyetler (KDV Hariç)
    if buying_includes_vat:
        net_product_cost = cost / (1 + buying_vat_rate)
    else:
        net_product_cost = cost
        
    # Gider KDV Oranı (Genelde %20 varsayıyoruz)
    expense_vat_rate = 0.20 
    
    net_shipping = shipping_cost_gross / (1 + expense_vat_rate)
    net_service = service_fee_gross / (1 + expense_vat_rate)
    
    # Stopaj (Net ürün maliyeti üzerinden mi? Genelde brüt üzerinden hesaplanır ama XML fiyatı esastır)
    # XML fiyatı (cost) üzerinden stopaj
    withholding_tax = cost * withholding_rate
    
    # Sabit Maliyetler Toplamı (Net)
    fixed_costs_net = net_product_cost + net_shipping + net_service + withholding_tax
    
    # İndirilebilir KDV (Sabit Kısımlar)
    # Ürün KDV + Kargo KDV + Hizmet KDV
    deductible_vat_fixed = (net_product_cost * buying_vat_rate) + \
                           (net_shipping * expense_vat_rate) + \
                           (net_service * expense_vat_rate)

    # B. Satış Fiyatı Hesabı (Döngüsel Bağlılık Çözümü)
    # Formül: P = (FixedCosts + P*Comm/1.2 + PayableVAT) * (1 + Margin)
    # PayableVAT = OutputVAT - InputVAT
    # OutputVAT = P * (SellVAT / (1+SellVAT))
    # InputVAT = DeductibleFixed + (P*Comm/1.2 * 0.2)
    
    # Basitleştirme:
    # P = (1+Margin) * [ FixedCosts + P*CommNet + max(0, P*OutputVatFactor - DeductibleFixed - P*CommInputVatFactor) ]
    
    # Katsayılar
    K = 1 + margin
    R_comm_net = comm_rate / (1 + expense_vat_rate) # Komisyonun net maliyet katsayısı
    R_comm_vat = comm_rate - R_comm_net # Komisyonun KDV katsayısı (Brüt - Net)
    
    R_out_vat = selling_vat_rate / (1 + selling_vat_rate) # İç yüzde ile KDV
    
    # Durum 1: Ödenecek KDV Çıkıyor (Pozitif)
    # P = K * (FixedCosts + P*R_comm_net + P*R_out_vat - DeductibleFixed - P*R_comm_vat)
    # P = K * (FixedCosts - DeductibleFixed) + P * K * (R_comm_net + R_out_vat - R_comm_vat)
    # P * [1 - K * (R_comm_net + R_out_vat - R_comm_vat)] = K * (FixedCosts - DeductibleFixed)
    
    factor_vat_pos = K * (R_comm_net + R_out_vat - R_comm_vat)
    base_vat_pos = K * (fixed_costs_net - deductible_vat_fixed)
    
    if (1 - factor_vat_pos) > 0:
        price_with_vat = base_vat_pos / (1 - factor_vat_pos)
    else:
        price_with_vat = float('inf') # Hata durumu, marj çok yüksek veya formül patladı

    # Kontrol: Bu fiyatta gerçekten KDV çıkıyor mu?
    output_vat = price_with_vat * R_out_vat
    input_vat_comm = price_with_vat * R_comm_vat
    payable_vat = output_vat - (deductible_vat_fixed + input_vat_comm)
    
    final_price = price_with_vat
    
    if payable_vat < 0:
        # Durum 2: Ödenecek KDV Yok (Alacaklıyız) -> KDV Maliyeti 0
        # P = K * (FixedCosts + P*R_comm_net)
        # P * (1 - K*R_comm_net) = K * FixedCosts
        
        factor_vat_zero = K * R_comm_net
        base_vat_zero = K * fixed_costs_net
        
        if (1 - factor_vat_zero) > 0:
            final_price = base_vat_zero / (1 - factor_vat_zero)
        else:
            final_price = cost * 2 # Fallback

    if settings.price_rounding:
        final_price = math.floor(final_price) + 0.99
        
    return round(final_price, 2)

@login_required
def get_background_processes(request):
    processes = BackgroundProcess.objects.all().order_by('-created_at')[:10]
    data = []
    for p in processes:
        data.append({
            'id': p.id,
            'type': p.get_process_type_display(),
            'supplier': p.supplier.name if p.supplier else '-',
            'status': p.get_status_display(),
            'status_code': p.status,
            'message': p.message,
            'progress': f"{p.processed_items} / {p.total_items}" if p.total_items > 0 else "-",
            'created_at': p.created_at.strftime('%H:%M:%S'),
            'completed_at': p.completed_at.strftime('%H:%M:%S') if p.completed_at else '-'
        })
    return JsonResponse({'processes': data})

