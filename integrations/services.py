import requests
import json
from django.conf import settings
from .models import TrendyolSettings
import base64

class TrendyolService:
    def __init__(self, user):
        try:
            self.settings = TrendyolSettings.objects.get(user=user, is_active=True)
        except TrendyolSettings.DoesNotExist:
            raise Exception("Trendyol ayarları bulunamadı veya aktif değil.")

        self.base_url = "https://apigw.trendyol.com/integration/product/sellers"
        self.supplier_id = self.settings.supplier_id
        self.api_key = self.settings.api_key
        self.api_secret = self.settings.api_secret

    def get_headers(self):
        auth_string = f"{self.api_key}:{self.api_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "User-Agent": f"{self.supplier_id} - SelfIntegration"
        }

    def create_products(self, items):
        """
        Trendyol'a ürünleri gönderir.
        items: Hazırlanmış ürün sözlükleri listesi (payload['items'])
        """
        url = f"{self.base_url}/{self.supplier_id}/products"
        
        if not items:
            return {"status": "error", "message": "Gönderilecek ürün listesi boş."}

        payload = {"items": items}
        
        try:
            response = requests.post(url, headers=self.get_headers(), json=payload)
            response.raise_for_status()
            
            # Başarılı ise batchRequestId döner
            return response.json()
        except requests.RequestException as e:
            error_content = ""
            if e.response is not None:
                error_content = e.response.text
            return {"status": "error", "message": str(e), "details": error_content}

    def check_batch_request(self, batch_request_id):
        url = f"{self.base_url}/{self.supplier_id}/products/batch-requests/{batch_request_id}"
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
             return {"status": "error", "message": str(e)}

    def search_brands(self, name):
        """
        Trendyol'da marka arar.
        """
        url = f"https://apigw.trendyol.com/integration/product/brands/by-name?name={name}"
        try:
            # Bu endpoint public olabilir veya auth gerektirebilir. Dökümanda auth belirtilmemiş ama header ekleyelim.
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return []

    def get_category_tree(self):
        """
        Trendyol kategori ağacını çeker.
        """
        url = "https://apigw.trendyol.com/integration/product/product-categories"
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"categories": []}

    def get_category_attributes(self, category_id):
        """
        Kategori özelliklerini çeker.
        """
        url = f"https://apigw.trendyol.com/integration/product/product-categories/{category_id}/attributes"
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"API Hatası: {str(e)}")

    def delete_products(self, barcodes):
        """
        Trendyol'dan ürünleri siler.
        barcodes: Silinecek ürünlerin barkod listesi ['barkod1', 'barkod2']
        """
        url = f"{self.base_url}/{self.supplier_id}/products"
        
        if not barcodes:
            return {"status": "error", "message": "Silinecek ürün listesi boş."}

        items = [{"barcode": b} for b in barcodes]
        payload = {"items": items}
        
        try:
            # DELETE methodu ile body gönderimi
            response = requests.delete(url, headers=self.get_headers(), json=payload)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            error_content = ""
            if e.response is not None:
                error_content = e.response.text
            return {"status": "error", "message": str(e), "details": error_content}

    def update_price_and_inventory(self, items):
        """
        Trendyol'da stok ve fiyat günceller.
        items: [{"barcode": "...", "quantity": 10, "salePrice": 100.0, "listPrice": 120.0}, ...]
        """
        url = f"https://apigw.trendyol.com/integration/inventory/sellers/{self.supplier_id}/products/price-and-inventory"
        
        if not items:
            return {"status": "error", "message": "Güncellenecek ürün listesi boş."}

        # Max 1000 items per request
        batch_size = 1000
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            payload = {"items": batch}
            
            try:
                response = requests.post(url, headers=self.get_headers(), json=payload)
                response.raise_for_status()
                results.append(response.json())
            except requests.RequestException as e:
                error_content = ""
                if e.response is not None:
                    error_content = e.response.text
                results.append({"status": "error", "message": str(e), "details": error_content})
                
        return results

    def archive_products(self, items):
        """
        Trendyol'da ürünleri arşivler veya arşivden çıkarır.
        items: [{"barcode": "...", "archived": True/False}, ...]
        """
        url = f"{self.base_url}/{self.supplier_id}/products/archive-state"
        
        if not items:
            return {"status": "error", "message": "İşlem yapılacak ürün listesi boş."}

        # Max 1000 items per request
        batch_size = 1000
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            payload = {"items": batch}
            
            try:
                response = requests.put(url, headers=self.get_headers(), json=payload)
                response.raise_for_status()
                results.append(response.json())
            except requests.RequestException as e:
                error_content = ""
                if e.response is not None:
                    error_content = e.response.text
                results.append({"status": "error", "message": str(e), "details": error_content})
                
        return results

    def get_products(self, barcodes=None, page=0, size=50, approved=None):
        """
        Trendyol'dan ürünleri çeker.
        barcodes: List of strings (optional)
        """
        url = f"{self.base_url}/{self.supplier_id}/products"
        
        params = {
            "page": page,
            "size": size
        }
        
        if barcodes:
            params["barcode"] = ",".join(barcodes)
            
        if approved is not None:
            params["approved"] = approved

        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # 404 dönerse ürün bulunamadı demektir, boş liste dönelim
            if e.response is not None and e.response.status_code == 404:
                return {"content": []}
            raise Exception(f"API Hatası (get_products): {str(e)}")

