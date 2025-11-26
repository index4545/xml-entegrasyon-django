from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TrendyolBatchRequest, Product, BackgroundProcess
from integrations.services import TrendyolService
import json

@login_required
def batch_requests_list(request):
    batches = TrendyolBatchRequest.objects.all().order_by('-created_at')
    processes = BackgroundProcess.objects.all().order_by('-created_at')
    return render(request, 'products/batch_requests_list.html', {
        'batches': batches,
        'processes': processes
    })

@login_required
def check_batch_status(request, batch_id):
    try:
        batch = TrendyolBatchRequest.objects.get(batch_request_id=batch_id)
        service = TrendyolService(user=request.user)
        result = service.check_batch_request(batch_id)
        
        # Update local record
        if 'status' in result:
            batch.status = result['status']
        if 'failedItemCount' in result:
            batch.failed_item_count = result['failedItemCount']
        if 'itemCount' in result:
            batch.item_count = result['itemCount']
            
        batch.result_json = result
        batch.save()
        
        # Hatalı ürünleri bul ve yayından kaldır
        if batch.failed_item_count > 0 and 'items' in result:
            failed_barcodes = []
            for item in result['items']:
                if item.get('status') == 'FAILURE':
                    # Trendyol genellikle requestItemIdentifier veya barcode alanında barkodu döner
                    # Ancak createProducts v2'de requestItemIdentifier gönderilmediyse ne döner?
                    # Genellikle barcode döner.
                    # Kontrol edelim:
                    identifier = item.get('requestItemIdentifier') or item.get('barcode')
                    if identifier:
                        failed_barcodes.append(identifier)
            
            if failed_barcodes:
                updated_count = Product.objects.filter(barcode__in=failed_barcodes).update(is_published_to_trendyol=False)
                messages.warning(request, f"{updated_count} adet hatalı ürün 'Yayında Değil' olarak işaretlendi.")

        messages.success(request, f"Batch durumu güncellendi: {batch.status}")
        
    except TrendyolBatchRequest.DoesNotExist:
        messages.error(request, "Batch kaydı bulunamadı.")
    except Exception as e:
        messages.error(request, f"Hata: {str(e)}")
        
    return redirect('batch_requests_list')
