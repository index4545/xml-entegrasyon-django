from django.db import models
from django.contrib.auth.models import User

class TrendyolSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trendyol_settings')
    api_key = models.CharField(max_length=255, verbose_name="Trendyol API Key")
    api_secret = models.CharField(max_length=255, verbose_name="Trendyol API Secret")
    supplier_id = models.CharField(max_length=255, verbose_name="Trendyol Satıcı ID (Supplier ID)")
    
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    def __str__(self):
        return f"Trendyol Settings for {self.user.username}"

    class Meta:
        verbose_name = "Trendyol Ayarları"
        verbose_name_plural = "Trendyol Ayarları"

class GeminiSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gemini_settings')
    api_key = models.CharField(max_length=255, verbose_name="Gemini API Key")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    def __str__(self):
        return f"Gemini Settings for {self.user.username}"

    class Meta:
        verbose_name = "Gemini AI Ayarları"
        verbose_name_plural = "Gemini AI Ayarları"

class GeminiAPIKey(models.Model):
    settings = models.ForeignKey(GeminiSettings, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=255, verbose_name="API Key")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    last_used_at = models.DateTimeField(null=True, blank=True)
    error_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.key[:10]}..."

