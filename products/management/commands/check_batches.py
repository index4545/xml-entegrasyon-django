from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import TrendyolBatchRequest, BackgroundProcess, Product
from integrations.models import TrendyolSettings
from integrations.services import TrendyolService
import traceback

class Command(BaseCommand):
    help = 'Checks the status of pending Trendyol batch requests.'

    def handle(self, *args, **options):
        self.stdout.write("Checking pending batches...")
        
        # Find pending batches
        pending_batches = TrendyolBatchRequest.objects.exclude(status__in=['COMPLETED', 'FAILED', 'VERIFIED'])
        
        if not pending_batches.exists():
            self.stdout.write("No pending batches found.")
            return

        # Get Service
        ty_settings = TrendyolSettings.objects.filter(is_active=True).first()
        if not ty_settings:
            self.stdout.write(self.style.ERROR("No active Trendyol settings found."))
            return
            
        service = TrendyolService(user=ty_settings.user)
        
        # Create Background Process
        process = BackgroundProcess.objects.create(
            process_type='trendyol_update',
            status='processing',
            message=f"{pending_batches.count()} adet bekleyen işlem kontrol ediliyor...",
            total_items=pending_batches.count()
        )
        
        checked_count = 0
        completed_count = 0
        failed_count = 0
        
        try:
            for batch in pending_batches:
                try:
                    result = service.check_batch_request(batch.batch_request_id)
                    
                    old_status = batch.status
                    new_status = result.get('status', old_status)
                    
                    batch.status = new_status
                    batch.failed_item_count = result.get('failedItemCount', batch.failed_item_count)
                    batch.item_count = result.get('itemCount', batch.item_count)
                    batch.result_json = result
                    batch.last_checked_at = timezone.now()
                    batch.save()
                    
                    # Update the linked process if exists
                    if batch.process:
                        p = batch.process
                        # Append status to message if not already there
                        status_msg = f" | Trendyol Batch Sonuç: {new_status} (Hatalı: {batch.failed_item_count})"
                        if status_msg not in p.message:
                            p.message += status_msg
                        
                        # Update details
                        if 'trendyol_results' not in p.details:
                            p.details['trendyol_results'] = []
                        
                        # Avoid duplicates in details list
                        exists = False
                        for r in p.details['trendyol_results']:
                            if r.get('batch_id') == batch.batch_request_id and r.get('status') == new_status:
                                exists = True
                                break
                        
                        if not exists:
                            p.details['trendyol_results'].append({
                                'batch_id': batch.batch_request_id,
                                'status': new_status,
                                'failed_count': batch.failed_item_count,
                                'total_count': batch.item_count,
                                'checked_at': timezone.now().strftime('%H:%M:%S')
                            })
                        
                        p.save()

                    if new_status == 'COMPLETED':
                        completed_count += 1
                    elif new_status == 'FAILED':
                        failed_count += 1
                        
                        # Handle failed items if any
                        if 'items' in result:
                            failed_barcodes = []
                            items_to_archive = [] # Silme hatası alan ama arşivlenmesi gerekenler

                            for item in result['items']:
                                if item.get('status') == 'FAILURE':
                                    identifier = item.get('requestItemIdentifier') or item.get('barcode')
                                    reasons = item.get('failureReasons', [])
                                    reason_str = " ".join(reasons).lower()
                                    
                                    if identifier:
                                        failed_barcodes.append(identifier)
                                        
                                        # Hata: "arşivledikten sonra silme işlemini gerçekleştirin"
                                        if "arşivle" in reason_str and batch.batch_type == 'ProductDeletion':
                                            items_to_archive.append(identifier)
                            
                            # 1. Hatalı ürünler için stok sıfırlama (Varsa)
                            if failed_barcodes:
                                # Find products with these barcodes
                                failed_products = Product.objects.filter(barcode__in=failed_barcodes)
                                
                                for product in failed_products:
                                    # Check supplier settings for error handling
                                    try:
                                        if product.supplier.settings.zero_stock_on_error:
                                            # Set stock to 0 instead of unpublishing
                                            product.stock_quantity = 0
                                            product.save()
                                            self.stdout.write(self.style.WARNING(f"Zeroed stock for failed item: {product.barcode}"))
                                        else:
                                            pass
                                    except Exception as e:
                                        self.stdout.write(self.style.ERROR(f"Error handling failed item {product.barcode}: {e}"))

                            # 2. Otomatik Arşivleme (Silme işlemi başarısız olduysa)
                            if items_to_archive:
                                self.stdout.write(self.style.WARNING(f"Silme işlemi başarısız olan {len(items_to_archive)} ürün otomatik arşivleniyor..."))
                                archive_items = [{"barcode": b, "archived": True} for b in items_to_archive]
                                try:
                                    archive_results = service.archive_products(archive_items)
                                    for res in archive_results:
                                        if "batchRequestId" in res:
                                            TrendyolBatchRequest.objects.create(
                                                batch_request_id=res['batchRequestId'],
                                                batch_type='ProductArchiveUpdate',
                                                item_count=len(items_to_archive)
                                            )
                                            self.stdout.write(self.style.SUCCESS(f"Otomatik arşiv isteği gönderildi: {res['batchRequestId']}"))
                                            
                                            # Yerel durumu güncelle
                                            Product.objects.filter(barcode__in=items_to_archive).update(is_published_to_trendyol=False)
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f"Otomatik arşivleme hatası: {e}"))

                    checked_count += 1
                    process.processed_items = checked_count
                    process.save()
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error checking batch {batch.batch_request_id}: {e}"))
            
            process.status = 'completed'
            process.message = f"Kontrol tamamlandı. {completed_count} tamamlandı, {failed_count} hatalı."
            process.completed_at = timezone.now()
            process.details = {
                'checked_batches': checked_count,
                'completed': completed_count,
                'failed': failed_count
            }
            process.save()
            
        except Exception as e:
            process.status = 'failed'
            process.message = f"Genel hata: {str(e)}"
            process.error_details = traceback.format_exc()
            process.completed_at = timezone.now()
            process.save()
            
        self.stdout.write(self.style.SUCCESS("Batch check complete."))
