from django.contrib import admin
from django.contrib import messages
from .models import Supplier, Product, ProductImage
from integrations.services import TrendyolService

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'xml_url', 'is_active', 'updated_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'selling_price', 'stock_quantity', 'supplier', 'is_published_to_trendyol')
    list_filter = ('supplier', 'is_published_to_trendyol', 'brand')
    search_fields = ('sku', 'name', 'barcode')
    inlines = [ProductImageInline]
    actions = ['send_to_trendyol']

    def send_to_trendyol(self, request, queryset):
        try:
            service = TrendyolService(user=request.user)
            result = service.create_products(queryset)
            
            if "batchRequestId" in result:
                self.message_user(request, f"Ürünler Trendyol'a gönderildi. Batch ID: {result['batchRequestId']}", messages.SUCCESS)
                # İsteğe bağlı: Ürünlerin durumunu güncelle
                queryset.update(is_published_to_trendyol=True) # Bu sadece gönderildiğini işaretler, başarılı olduğunu garanti etmez.
            elif result.get("status") == "error":
                self.message_user(request, f"Hata oluştu: {result.get('message')} Detay: {result.get('details')}", messages.ERROR)
            else:
                self.message_user(request, f"Bilinmeyen yanıt: {result}", messages.WARNING)

        except Exception as e:
            self.message_user(request, f"İşlem başlatılamadı: {str(e)}", messages.ERROR)

    send_to_trendyol.short_description = "Seçili ürünleri Trendyol'a gönder"

