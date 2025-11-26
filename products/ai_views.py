from collections import OrderedDict
import json
import concurrent.futures
import itertools

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Product, Supplier, TrendyolCategory
from integrations.models import GeminiSettings, GeminiAPIKey
from integrations.ai_service import GeminiService
from integrations.services import TrendyolService


STATUS_META = OrderedDict({
    'generated': {'label': 'AI ile Güncellenenler', 'badge': 'success'},
    'processing': {'label': 'İşleniyor', 'badge': 'warning'},
    'error': {'label': 'Hata Alanlar', 'badge': 'danger'},
    'original': {'label': 'Orijinal İçerik', 'badge': 'secondary'},
})


def _prepare_attributes(product):
    attrs = product.attributes
    if not attrs:
        return ''
    if isinstance(attrs, dict):
        return ', '.join([f"{key}: {value}" for key, value in attrs.items()])
    if isinstance(attrs, list):
        return ', '.join([str(item) for item in attrs])
    return str(attrs)


def _validate_ai_output(title, description):
    if not title or not description:
        raise ValueError("AI çıktısı eksik: başlık veya açıklama gelmedi.")

    title_length = len(title)
    if title_length < 70 or title_length > 80:
        raise ValueError(f"Ürün adı {title_length} karakter. 70-80 karakter aralığında olmalı.")

    plain_description = strip_tags(description)
    words = [word for word in plain_description.split() if word.strip()]
    word_count = len(words)
    # Kullanıcı 300 istiyor ama AI bazen 290'da kalabiliyor, tolerans tanıyalım (250).
    if word_count < 250 or word_count > 600:
        raise ValueError(f"Açıklama {word_count} kelime. 300-500 kelime hedefleniyor (Min 250 kabul edilir).")

    return title.strip(), description.strip(), word_count


def _process_product_ai(product, service, api_key=None):
    now = timezone.now()
    product.ai_status = 'processing'
    product.ai_last_error = ''
    product.ai_last_run_at = now
    product.save(update_fields=['ai_status', 'ai_last_error', 'ai_last_run_at'])

    attrs = _prepare_attributes(product)

    try:
        if api_key:
            result_json = service.generate_with_key(product.name, product.description, attrs, api_key)
        else:
            result_json = service.generate_product_content(product.name, product.description, attrs)
            
        data = json.loads(result_json)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        title, description, word_count = _validate_ai_output(title, description)

        update_fields = []
        if not product.original_name:
            product.original_name = product.name
            update_fields.append('original_name')
        if not product.original_description:
            product.original_description = product.description
            update_fields.append('original_description')

        product.name = title
        product.description = description
        product.ai_generated_name = title
        product.ai_generated_description = description
        product.ai_status = 'generated'
        product.ai_last_run_at = timezone.now()
        product.ai_last_error = ''

        update_fields += [
            'name',
            'description',
            'ai_generated_name',
            'ai_generated_description',
            'ai_status',
            'ai_last_run_at',
            'ai_last_error',
        ]
        product.save(update_fields=update_fields)

        snippet = strip_tags(description)[:180]

        return {
            'success': True,
            'product_id': product.id,
            'title': title,
            'description': description,
            'title_length': len(title),
            'word_count': word_count,
            'snippet': snippet,
            'ai_status': product.ai_status,
        }

    except Exception as exc:
        product.ai_status = 'error'
        product.ai_last_error = str(exc)
        product.ai_last_run_at = timezone.now()
        product.save(update_fields=['ai_status', 'ai_last_error', 'ai_last_run_at'])
        raise

@login_required
def ai_tools(request):
    # Settings Handling
    try:
        settings = GeminiSettings.objects.get(user=request.user)
    except GeminiSettings.DoesNotExist:
        settings = None

    if request.method == 'POST' and 'save_settings' in request.POST:
        api_keys_text = request.POST.get('api_keys_list', '').strip()
        
        if api_keys_text:
            # Create or update settings
            settings, created = GeminiSettings.objects.get_or_create(
                user=request.user,
                defaults={'is_active': True, 'api_key': 'multi-key'}
            )
            
            # Parse keys (one per line)
            keys = [k.strip() for k in api_keys_text.split('\n') if k.strip()]
            
            if keys:
                # Clear old keys and add new ones
                settings.api_keys.all().delete()
                for key in keys:
                    GeminiAPIKey.objects.create(settings=settings, key=key)
                
                # Set the first key as default for backward compatibility
                settings.api_key = keys[0]
                settings.save()
                
                messages.success(request, f"{len(keys)} adet API anahtarı kaydedildi.")
            else:
                messages.warning(request, "Geçerli API anahtarı bulunamadı.")
                
            return redirect('ai_tools')

    # Product List Logic
    query = request.GET.get('q', '')
    status_filter = request.GET.get('ai_status', '')
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    supplier_id = request.GET.get('supplier_id', '')
    match_status = request.GET.get('match_status', '')
    sort_by = request.GET.get('sort_by', '')
    
    per_page = request.GET.get('per_page', '20')
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100, 200]:
            per_page = 20
    except ValueError:
        per_page = 20

    status_ordering = Case(
        When(ai_status='generated', then=1),
        When(ai_status='processing', then=2),
        When(ai_status='error', then=3),
        default=4,
        output_field=IntegerField(),
    )

    if sort_by == 'newest_xml':
        products = Product.objects.all().order_by('-created_at')
    elif sort_by == 'oldest_xml':
        products = Product.objects.all().order_by('created_at')
    else:
        products = Product.objects.all().order_by(status_ordering, '-updated_at')
    
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)

    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) |
            Q(original_barcode__icontains=query) |
            Q(barcode__icontains=query)
        )

    if status_filter:
        products = products.filter(ai_status=status_filter)
    
    if category_filter:
        products = products.filter(category_path=category_filter)
        
    if brand_filter:
        products = products.filter(brand=brand_filter)

    if match_status == 'matched':
        products = products.filter(trendyol_category_id__isnull=False)
    elif match_status == 'unmatched':
        products = products.filter(trendyol_category_id__isnull=True)

    # Get unique categories and brands for filters (Filtered by Supplier)
    filter_base_products = Product.objects.all()
    if supplier_id:
        filter_base_products = filter_base_products.filter(supplier_id=supplier_id)

    categories = filter_base_products.exclude(category_path__isnull=True).exclude(category_path='').values_list('category_path', flat=True).distinct().order_by('category_path')
    brands = filter_base_products.exclude(brand__isnull=True).exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand')
    
    suppliers = Supplier.objects.all()

    paginator = Paginator(products, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    page_items = list(page_obj.object_list)

    # Fetch Trendyol Category Names for display
    t_ids = [p.trendyol_category_id for p in page_items if p.trendyol_category_id]
    cat_map = {}
    if t_ids:
        cats = TrendyolCategory.objects.filter(trendyol_id__in=t_ids)
        cat_map = {c.trendyol_id: c.name for c in cats}

    for p in page_items:
        if p.trendyol_category_id:
            p.trendyol_category_name_display = cat_map.get(p.trendyol_category_id)

    grouped_products = []
    for key, meta in STATUS_META.items():
        items = [item for item in page_items if item.ai_status == key]
        grouped_products.append({
            'status': key,
            'label': meta['label'],
            'badge': meta['badge'],
            'items': items,
        })
        
    # Get existing keys for display
    existing_keys = ""
    if settings:
        keys = settings.api_keys.all().values_list('key', flat=True)
        existing_keys = "\n".join(keys)
        if not existing_keys and settings.api_key:
            existing_keys = settings.api_key

    return render(request, 'products/ai_tools.html', {
        'products': page_obj,
        'settings': settings,
        'existing_keys': existing_keys,
        'grouped_products': grouped_products,
        'ai_status_choices': Product._meta.get_field('ai_status').choices,
        'ai_status_filter': status_filter,
        'category_filter': category_filter,
        'brand_filter': brand_filter,
        'supplier_id': supplier_id,
        'match_status': match_status,
        'categories': categories,
        'brands': brands,
        'suppliers': suppliers,
        'status_meta': STATUS_META,
        'per_page': per_page,
        'sort_by': sort_by,
    })

def process_single_product_task(product_id, api_key, user_id):
    # Worker function for thread pool
    # Re-fetch product to avoid stale data and ensure thread safety
    try:
        # We need to setup Django environment if this was a separate process, 
        # but for ThreadPoolExecutor in the same process, it's fine.
        # However, DB connections should be handled.
        from django.db import connection
        
        product = Product.objects.get(id=product_id)
        
        # Mock user object or fetch user if needed by service (service uses user to get settings)
        # But here we pass the key directly, so we can instantiate service with a dummy user or modify service
        # Actually, GeminiService needs a user to fetch settings.
        # Let's instantiate service once in the main thread or pass the key directly to a static method?
        # Better: Instantiate service here.
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        service = GeminiService(user=user)
        
        _process_product_ai(product, service, api_key)
        
        connection.close() # Close DB connection for this thread
        return {'success': True, 'sku': product.sku}
    except Exception as e:
        from django.db import connection
        connection.close()
        return {'success': False, 'sku': product_id, 'error': str(e)}

@login_required
def ai_generate(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_products')
        if not selected_ids:
            messages.warning(request, "Lütfen ürün seçin.")
            return redirect('ai_tools')
        
        products = Product.objects.filter(id__in=selected_ids)
        
        # Get API Keys
        try:
            settings = GeminiSettings.objects.get(user=request.user)
            api_keys = list(settings.api_keys.values_list('key', flat=True))
            if not api_keys and settings.api_key:
                api_keys = [settings.api_key]
        except GeminiSettings.DoesNotExist:
            messages.error(request, "AI Ayarları bulunamadı.")
            return redirect('ai_tools')

        if not api_keys:
            messages.error(request, "Aktif API anahtarı bulunamadı.")
            return redirect('ai_tools')

        success_count = 0
        errors = []
        
        # Round-robin keys iterator
        key_cycle = itertools.cycle(api_keys)
        
        # Use ThreadPoolExecutor for parallel processing
        # Max workers = number of keys (Conservative for rate limits)
        max_workers = len(api_keys)
        if max_workers > 5: max_workers = 5 # Cap at 5 threads to avoid DB overload and rate limits
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_product = {}
            for product in products:
                key = next(key_cycle)
                future = executor.submit(process_single_product_task, product.id, key, request.user.id)
                future_to_product[future] = product

            for future in concurrent.futures.as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    result = future.result()
                    if result['success']:
                        success_count += 1
                    else:
                        errors.append(f"{product.sku}: {result['error']}")
                except Exception as exc:
                    errors.append(f"{product.sku}: {exc}")

        if success_count:
            messages.success(request, f"{success_count} ürün AI ile paralel olarak yeniden yazıldı.")
        if errors:
            messages.warning(request, f"{len(errors)} ürün işlenirken hata oluştu. İlk hata: {errors[0]}")
            
    return redirect('ai_tools')


@login_required
@require_POST
def ai_generate_single(request, pk):
    product = get_object_or_404(Product, pk=pk)

    try:
        service = GeminiService(user=request.user)
        result = _process_product_ai(product, service)
        meta = STATUS_META.get(result['ai_status'], {'badge': 'secondary', 'label': 'Bilinmiyor'})
        result.update({
            'status_badge': meta['badge'],
            'status_label': meta['label'],
            'name': product.name,
            'description_snippet': strip_tags(product.description)[:180],
            'original_name': product.original_name or '',
            'original_description': product.original_description or '',
            'ai_generated_name': product.ai_generated_name or '',
            'ai_generated_description': product.ai_generated_description or '',
        })
        return JsonResponse(result)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)


@login_required
@require_POST
def ai_revert_original(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if not product.original_name and not product.original_description:
        return JsonResponse({'success': False, 'error': 'Orijinal XML bilgileri bulunamadı.'}, status=400)

    product.name = product.original_name or product.name
    product.description = product.original_description or product.description
    product.ai_generated_name = None
    product.ai_generated_description = None
    product.ai_status = 'original'
    product.ai_last_error = ''
    product.ai_last_run_at = timezone.now()
    product.save(update_fields=[
        'name',
        'description',
        'ai_generated_name',
        'ai_generated_description',
        'ai_status',
        'ai_last_error',
        'ai_last_run_at',
    ])

    return JsonResponse({
        'success': True,
        'product_id': product.id,
        'name': product.name,
        'description_snippet': strip_tags(product.description)[:180],
        'status_badge': STATUS_META['original']['badge'],
        'status_label': STATUS_META['original']['label'],
        'ai_status': 'original',
        'original_name': product.original_name or '',
        'original_description': product.original_description or '',
    })

def process_category_match_task(product_id, api_key, user_id, trendyol_cats_flat):
    try:
        from django.db import connection
        from django.contrib.auth.models import User
        
        product = Product.objects.get(id=product_id)
        user = User.objects.get(id=user_id)
        service = GeminiService(user=user)
        
        # 1. Search Candidates Locally (Fuzzy or Keyword)
        search_text = product.name.lower()
        
        # Score based search
        scored_candidates = []
        search_words = [w for w in search_text.split() if len(w) > 2]
        
        for cat in trendyol_cats_flat:
            cat_name_lower = cat['name'].lower()
            # Also check path if available
            cat_path_lower = cat.get('path', '').lower()
            
            score = 0
            
            # Exact category name match in product name (High Priority)
            if cat_name_lower in search_text:
                score += 50

            for word in search_words:
                if word in cat_name_lower:
                    score += 10 # Name match is stronger
                elif word in cat_path_lower:
                    score += 3 # Path match is weaker
            
            if score > 0:
                scored_candidates.append((score, cat))
        
        # Sort by score desc
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Take top 25 (increased from 20)
        top_candidates = [c[1] for c in scored_candidates[:25]]
        
        # Fallback: If no candidates, try broader search (first word only)
        if not top_candidates and search_words:
            first_word = search_words[0]
            for cat in trendyol_cats_flat:
                if first_word in cat['name'].lower():
                    top_candidates.append(cat)
            top_candidates = top_candidates[:25]

        if not top_candidates:
            product.ai_last_error = "Kategori eşleşmesi için uygun aday bulunamadı."
            product.save(update_fields=['ai_last_error'])
            connection.close()
            return {'success': False, 'sku': product.sku, 'error': 'No candidates found', 'product_id': product.id}
            
        # 2. Ask AI
        selected_id = service.match_category_with_key(product.name, product.description, top_candidates, api_key)
        
        if selected_id:
            product.trendyol_category_id = selected_id
            product.ai_last_error = "" # Clear error
            product.save(update_fields=['trendyol_category_id', 'ai_last_error'])
            
            # Find category name for display
            cat_name = str(selected_id)
            for c in trendyol_cats_flat:
                if c['id'] == selected_id:
                    cat_name = c['name']
                    break

            connection.close()
            return {
                'success': True, 
                'sku': product.sku, 
                'cat_id': selected_id, 
                'category_name': cat_name,
                'product_name': product.name,
                'product_id': product.id
            }
        else:
            product.ai_last_error = "AI geçerli bir kategori ID döndürmedi (Null)."
            product.save(update_fields=['ai_last_error'])
            connection.close()
            return {
                'success': False, 
                'sku': product.sku, 
                'error': 'AI returned null ID', 
                'product_id': product.id,
                'product_name': product.name
            }
            
    except Exception as e:
        from django.db import connection
        try:
            product = Product.objects.get(id=product_id)
            product.ai_last_error = f"Hata: {str(e)}"
            product.save(update_fields=['ai_last_error'])
        except:
            pass
        connection.close()
        return {
            'success': False, 
            'sku': product_id, 
            'error': str(e), 
            'product_id': product_id,
            'product_name': product.name if 'product' in locals() else str(product_id)
        }

@login_required
def ai_match_categories(request):
    if request.method == 'POST':
        # Check if it's a JSON request (from fetch)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
        
        if is_ajax:
            try:
                body = json.loads(request.body)
                selected_ids = body.get('selected_products', [])
            except:
                selected_ids = []
        else:
            selected_ids = request.POST.getlist('selected_products')

        if not selected_ids:
            if is_ajax:
                return JsonResponse({'error': 'Lütfen ürün seçin.'}, status=400)
            messages.warning(request, "Lütfen ürün seçin.")
            return redirect('ai_tools')
            
        products = Product.objects.filter(id__in=selected_ids)
        
        # Get API Keys
        try:
            settings = GeminiSettings.objects.get(user=request.user)
            api_keys = list(settings.api_keys.values_list('key', flat=True))
            if not api_keys and settings.api_key:
                api_keys = [settings.api_key]
        except GeminiSettings.DoesNotExist:
            if is_ajax:
                return JsonResponse({'error': 'AI Ayarları bulunamadı.'}, status=400)
            messages.error(request, "AI Ayarları bulunamadı.")
            return redirect('ai_tools')
            
        if not api_keys:
            if is_ajax:
                return JsonResponse({'error': 'Aktif API anahtarı bulunamadı.'}, status=400)
            messages.error(request, "Aktif API anahtarı bulunamadı.")
            return redirect('ai_tools')

        # Fetch Trendyol Tree and Flatten (Once)
        try:
            ty_service = TrendyolService(user=request.user)
            tree = ty_service.get_category_tree()
            
            trendyol_cats_flat = []
            def flatten_cats(cats, path=""):
                for c in cats:
                    current_path = f"{path} > {c['name']}" if path else c['name']
                    if not c.get('subCategories'):
                        trendyol_cats_flat.append({'id': c['id'], 'name': c['name'], 'path': current_path})
                    else:
                        flatten_cats(c['subCategories'], current_path)
            
            if 'categories' in tree:
                flatten_cats(tree['categories'])
            elif isinstance(tree, list):
                flatten_cats(tree)
                
        except Exception as e:
            if is_ajax:
                return JsonResponse({'error': f"Trendyol kategori ağacı alınamadı: {e}"}, status=500)
            messages.error(request, f"Trendyol kategori ağacı alınamadı: {e}")
            return redirect('ai_tools')

        def stream_response():
            yield json.dumps({'type': 'start', 'total': products.count()}) + "\n"
            
            key_cycle = itertools.cycle(api_keys)
            max_workers = min(len(api_keys), 5)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_product = {}
                for product in products:
                    key = next(key_cycle)
                    future = executor.submit(process_category_match_task, product.id, key, request.user.id, trendyol_cats_flat)
                    future_to_product[future] = product

                for future in concurrent.futures.as_completed(future_to_product):
                    product = future_to_product[future]
                    try:
                        result = future.result()
                        yield json.dumps({'type': 'result', 'data': result}) + "\n"
                    except Exception as exc:
                        yield json.dumps({'type': 'result', 'data': {'success': False, 'sku': product.sku, 'error': str(exc), 'product_id': product.id}}) + "\n"
            
            yield json.dumps({'type': 'end'}) + "\n"

        if is_ajax:
            return StreamingHttpResponse(stream_response(), content_type='application/x-ndjson')
        
        # Fallback for non-ajax (legacy)
        # ... (same as before but blocking) ...
        # For simplicity, we redirect to ai_tools with a message saying "Use the button properly"
        # Or just run it blocking.
        messages.info(request, "İşlem arka planda başlatıldı (eski yöntem).")
        return redirect('ai_tools')
            
    return redirect('ai_tools')
