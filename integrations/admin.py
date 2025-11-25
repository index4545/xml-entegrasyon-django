from django.contrib import admin
from .models import TrendyolSettings

@admin.register(TrendyolSettings)
class TrendyolSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'supplier_id', 'is_active')

