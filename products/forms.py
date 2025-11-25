from django import forms
from .models import SupplierSettings, PriceRule

class SupplierSettingsForm(forms.ModelForm):
    class Meta:
        model = SupplierSettings
        fields = [
            'profit_margin', 'shipping_cost', 'price_rounding',
            'sku_prefix', 'use_unique_barcode', 'min_stock',
            'include_trendyol_commission', 'default_commission_rate',
            'service_fee', 'withholding_tax_rate',
            'buying_price_includes_vat', 'buying_vat_rate', 'selling_vat_rate',
            'auto_update_interval',
            'stop_stock_update', 'stop_price_update'
        ]
        widgets = {
            'profit_margin': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sku_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_rounding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_unique_barcode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_trendyol_commission': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'service_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'withholding_tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'buying_price_includes_vat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'buying_vat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_vat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_update_interval': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'stop_stock_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'stop_price_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'profit_margin': 'Varsayılan Kar Marjı (%)',
            'shipping_cost': 'Sabit Kargo/Maliyet (TL)'
        }

class PriceRuleForm(forms.ModelForm):
    class Meta:
        model = PriceRule
        fields = ['min_price', 'max_price', 'rule_type', 'operation_type', 'value', 'extra_cost']
        widgets = {
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Min Fiyat'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Max Fiyat'}),
            'rule_type': forms.Select(attrs={'class': 'form-select'}),
            'operation_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'İşlem Miktarı'}),
            'extra_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ek Fiyat'}),
        }
