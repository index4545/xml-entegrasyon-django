from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tedarikçi Adı")
    xml_url = models.URLField(verbose_name="XML Linki")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tedarikçi"
        verbose_name_plural = "Tedarikçiler"

class Product(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products', verbose_name="Tedarikçi")
    supplier_product_id = models.CharField(max_length=255, verbose_name="Tedarikçi Ürün ID")
    sku = models.CharField(max_length=255, unique=True, verbose_name="Stok Kodu (SKU)")
    barcode = models.CharField(max_length=255, blank=True, null=True, verbose_name="Barkod")
    name = models.CharField(max_length=500, verbose_name="Ürün Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    original_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="Orijinal Ürün Adı")
    original_description = models.TextField(blank=True, null=True, verbose_name="Orijinal Açıklama")
    ai_generated_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="AI Ürün Adı")
    ai_generated_description = models.TextField(blank=True, null=True, verbose_name="AI Açıklaması")
    ai_status = models.CharField(
        max_length=20,
        choices=[
            ('original', 'Orijinal'),
            ('processing', 'İşleniyor'),
            ('generated', 'AI Güncellendi'),
            ('error', 'Hata')
        ],
        default='original',
        verbose_name="AI İçerik Durumu"
    )
    ai_last_run_at = models.DateTimeField(blank=True, null=True, verbose_name="Son AI İşlemi")
    ai_last_error = models.TextField(blank=True, null=True, verbose_name="Son AI Hatası")
    
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Alış Fiyatı", default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Satış Fiyatı", default=0)
    stock_quantity = models.IntegerField(default=0, verbose_name="Stok Adedi")
    
    brand = models.CharField(max_length=255, blank=True, null=True, verbose_name="Marka")
    category_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="Kategori Yolu")
    
    # Trendyol Integration Status
    is_published_to_trendyol = models.BooleanField(default=False, verbose_name="Trendyol'da Yayında")
    trendyol_product_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Trendyol Ürün ID")
    trendyol_category_id = models.IntegerField(blank=True, null=True, verbose_name="Trendyol Kategori ID")
    trendyol_brand_id = models.IntegerField(blank=True, null=True, verbose_name="Trendyol Marka ID")
    
    original_barcode = models.CharField(max_length=255, blank=True, null=True, verbose_name="Orjinal XML Barkodu")
    
    # Variant & Attributes
    model_code = models.CharField(max_length=255, blank=True, null=True, verbose_name="Model Kodu (Varyant Grubu)")
    attributes = models.JSONField(default=dict, blank=True, verbose_name="Ürün Özellikleri (XML)")
    trendyol_attributes = models.JSONField(default=dict, blank=True, verbose_name="Trendyol Özellikleri (AI)")

    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Eşitleme Tarihi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sku} - {self.name}"

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

class CategoryMapping(models.Model):
    xml_category_name = models.CharField(max_length=500, unique=True, verbose_name="XML Kategori Adı")
    trendyol_category_id = models.IntegerField(verbose_name="Trendyol Kategori ID")
    trendyol_category_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="Trendyol Kategori Adı")
    
    def __str__(self):
        return f"{self.xml_category_name} -> {self.trendyol_category_name or self.trendyol_category_id}"

    class Meta:
        verbose_name = "Kategori Eşleştirmesi"
        verbose_name_plural = "Kategori Eşleştirmeleri"

class BrandMapping(models.Model):
    xml_brand_name = models.CharField(max_length=255, unique=True, verbose_name="XML Marka Adı")
    trendyol_brand_id = models.IntegerField(verbose_name="Trendyol Marka ID")

    def __str__(self):
        return f"{self.xml_brand_name} -> {self.trendyol_brand_id}"

    class Meta:
        verbose_name = "Marka Eşleştirmesi"
        verbose_name_plural = "Marka Eşleştirmeleri"

class TrendyolCategory(models.Model):
    name = models.CharField(max_length=500, verbose_name="Kategori Adı")
    trendyol_id = models.IntegerField(unique=True, verbose_name="Trendyol Kategori ID")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Komisyon Oranı (%)")

    def __str__(self):
        return f"{self.name} ({self.trendyol_id}) - %{self.commission_rate}"

    class Meta:
        verbose_name = "Trendyol Kategori Komisyonu"
        verbose_name_plural = "Trendyol Kategori Komisyonları"

class SupplierSettings(models.Model):
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='settings', verbose_name="Tedarikçi")
    
    # Fiyatlandırma Ayarları
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=20, verbose_name="Varsayılan Kar Marjı (%)")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sabit Kargo/Maliyet (TL)")
    price_rounding = models.BooleanField(default=False, verbose_name="Fiyat Yuvarlama (.90)")
    
    # Ürün Ayarları
    sku_prefix = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ürün Kodu Ön Eki")
    use_unique_barcode = models.BooleanField(default=False, verbose_name="Benzersiz Barkod Oluştur")
    min_stock = models.IntegerField(default=0, verbose_name="Minimum Stok Limiti")
    
    # Komisyon Ayarı
    include_trendyol_commission = models.BooleanField(default=False, verbose_name="Trendyol Komisyonunu Fiyata Dahil Et")
    default_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21.00, verbose_name="Varsayılan Komisyon Oranı (%)")

    # Vergi ve Ek Maliyet Ayarları
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=10.19, verbose_name="Hizmet Bedeli (TL) - KDV Dahil")
    withholding_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, verbose_name="Stopaj Oranı (%)")
    
    buying_price_includes_vat = models.BooleanField(default=True, verbose_name="Alış Fiyatına KDV Dahil")
    buying_vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, verbose_name="Alış KDV Oranı (%)")
    selling_vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, verbose_name="Satış KDV Oranı (%)")

    # Güncelleme Ayarları
    stop_stock_update = models.BooleanField(default=False, verbose_name="Stok Güncellemesi Yapılmasın")
    stop_price_update = models.BooleanField(default=False, verbose_name="Fiyat Güncellemesi Yapılmasın")
    
    # Otomatik Güncelleme Ayarı
    auto_update_interval = models.IntegerField(default=0, verbose_name="Otomatik Güncelleme Aralığı (Dakika)")
    last_auto_update = models.DateTimeField(null=True, blank=True, verbose_name="Son Otomatik Güncelleme")
    
    # Batch Kontrol Ayarı
    batch_check_interval = models.IntegerField(default=15, verbose_name="Batch Kontrol Aralığı (Dakika)")
    last_batch_check = models.DateTimeField(null=True, blank=True, verbose_name="Son Batch Kontrolü")

    # Hata Yönetimi
    zero_stock_on_error = models.BooleanField(default=True, verbose_name="Hata Durumunda Stoğu Sıfırla")

    # Çerçeve Ayarları
    use_frame = models.BooleanField(default=False, verbose_name="Ürün Görsellerine Çerçeve Ekle")
    frame_image = models.ImageField(upload_to='frames/', null=True, blank=True, verbose_name="Çerçeve Görseli (PNG)")

    def __str__(self):
        return f"Ayarlar: {self.supplier.name}"
    
    class Meta:
        verbose_name = "Tedarikçi Ayarı"
        verbose_name_plural = "Tedarikçi Ayarları"

class PriceRule(models.Model):
    RULE_TYPES = [('increase', 'Fiyat Artışı'), ('decrease', 'Fiyat İndirimi')]
    OP_TYPES = [('percentage', 'Yüzdelik (%)'), ('fixed', 'Tutar (TL)')]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='price_rules', verbose_name="Tedarikçi")
    min_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Min Fiyat")
    max_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Max Fiyat")
    
    rule_type = models.CharField(max_length=10, choices=RULE_TYPES, default='increase', verbose_name="Kural Tipi")
    operation_type = models.CharField(max_length=10, choices=OP_TYPES, default='percentage', verbose_name="İşlem Tipi")
    
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="İşlem Miktarı")
    extra_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ek Fiyat (TL)")

    def __str__(self):
        return f"{self.min_price} - {self.max_price}"

    class Meta:
        verbose_name = "Fiyat Kuralı"
        verbose_name_plural = "Fiyat Kuralları"
        ordering = ['min_price']

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=1000)
    processed_image = models.ImageField(upload_to='processed_images/', null=True, blank=True, verbose_name="İşlenmiş Görsel")
    cloudinary_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="Cloudinary URL")
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.sku}"

class CategoryAttributeMapping(models.Model):
    category_mapping = models.ForeignKey(CategoryMapping, on_delete=models.CASCADE, related_name='attribute_mappings', verbose_name="Kategori Eşleşmesi")
    trendyol_attribute_id = models.IntegerField(verbose_name="Trendyol Özellik ID")
    trendyol_attribute_name = models.CharField(max_length=255, verbose_name="Trendyol Özellik Adı")
    
    MAPPING_TYPES = [
        ('fixed', 'Sabit Değer'), 
        ('xml', 'XML Verisinden'),
        ('smart', 'Akıllı Eşleştirme (Açıklamadan)')
    ]
    mapping_type = models.CharField(max_length=10, choices=MAPPING_TYPES, default='fixed', verbose_name="Eşleşme Tipi")
    
    static_value = models.CharField(max_length=255, blank=True, null=True, verbose_name="Sabit Değer")
    xml_attribute_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="XML Özellik Adı")
    
    is_required = models.BooleanField(default=False, verbose_name="Zorunlu mu?")
    is_varianter = models.BooleanField(default=False, verbose_name="Varyant Özelliği mi?")
    is_slicer = models.BooleanField(default=False, verbose_name="Görsel Varyantı mı (Slicer)?")

    def __str__(self):
        return f"{self.category_mapping} - {self.trendyol_attribute_name}"

    class Meta:
        verbose_name = "Kategori Özellik Eşleşmesi"
        verbose_name_plural = "Kategori Özellik Eşleştirmeleri"

class TrendyolBatchRequest(models.Model):
    BATCH_TYPES = [
        ('ProductV2OnBoarding', 'Ürün Aktarımı'),
        ('ProductInventoryUpdate', 'Stok/Fiyat Güncelleme'),
        ('ProductArchiveUpdate', 'Ürün Arşivleme'),
        ('ProductDeletion', 'Ürün Silme'),
        ('ProductV2Update', 'Ürün Güncelleme'),
    ]
    
    batch_request_id = models.CharField(max_length=255, unique=True, verbose_name="Batch Request ID")
    batch_type = models.CharField(max_length=50, choices=BATCH_TYPES, verbose_name="İşlem Tipi")
    status = models.CharField(max_length=50, default='PROCESSING', verbose_name="Durum")
    
    item_count = models.IntegerField(default=0, verbose_name="Toplam Ürün")
    failed_item_count = models.IntegerField(default=0, verbose_name="Hatalı Ürün")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Kontrol Tarihi")
    
    result_json = models.JSONField(null=True, blank=True, verbose_name="Sonuç JSON")
    
    # Link to the background process that initiated this batch
    process = models.ForeignKey('BackgroundProcess', on_delete=models.SET_NULL, null=True, blank=True, related_name='batch_requests', verbose_name="İlgili İşlem")

    def __str__(self):
        return f"{self.batch_type} - {self.batch_request_id}"

    class Meta:
        verbose_name = "Trendyol Batch İsteği"
        verbose_name_plural = "Trendyol Batch İstekleri"
        ordering = ['-created_at']

class BackgroundProcess(models.Model):
    PROCESS_TYPES = [
        ('xml_sync', 'XML Senkronizasyonu'),
        ('manual_xml_sync', 'Manuel XML Senkronizasyonu'),
        ('trendyol_update', 'Trendyol Güncellemesi'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('processing', 'İşleniyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Hata'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    process_type = models.CharField(max_length=50, choices=PROCESS_TYPES, verbose_name="İşlem Tipi")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Tedarikçi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    
    total_items = models.IntegerField(default=0, verbose_name="Toplam Öğe")
    processed_items = models.IntegerField(default=0, verbose_name="İşlenen Öğe")
    
    message = models.TextField(blank=True, verbose_name="Durum Mesajı")
    details = models.JSONField(default=dict, blank=True, verbose_name="İşlem Detayları")
    error_details = models.TextField(blank=True, null=True, verbose_name="Hata Detayları")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_process_type_display()} - {self.status}"

    class Meta:
        verbose_name = "Arka Plan İşlemi"
        verbose_name_plural = "Arka Plan İşlemleri"
        ordering = ['-created_at']
