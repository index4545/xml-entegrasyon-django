import google.generativeai as genai
import requests
import json
import time
from .models import GeminiSettings

class GeminiService:
    def __init__(self, user):
        try:
            self.settings = GeminiSettings.objects.get(user=user, is_active=True)
        except GeminiSettings.DoesNotExist:
            raise Exception("Gemini AI ayarları bulunamadı veya aktif değil.")

        # Default config for single use
        if self.settings.api_key:
            genai.configure(api_key=self.settings.api_key)
        
        # Kullanıcı isteği üzerine Gemini 2.5 Pro kullanılıyor
        # Dökümantasyon taraması sonucu Gemini 2.5 serisinin (Flash/Pro) mevcut olduğu doğrulandı.
        # REST API ve SDK için model adı güncellendi.
        self.model_name = 'gemini-2.5-pro' 
        self.model = genai.GenerativeModel(self.model_name)

    def _get_prompt(self, product_name, description, attributes):
        return f"""
          Sen uzman bir SEO ve E-Ticaret içerik editörüsün. Aşağıdaki ürün bilgilerini kullanarak Trendyol ve Google SEO uyumlu, satış odaklı yeni bir ürün başlığı ve ürün açıklaması oluştur.

        MEVCUT ÜRÜN BİLGİLERİ:
        Ürün Adı: {product_name}
        Mevcut Açıklama: {description}
        Özellikler: {attributes}

        KURALLAR:
        1. Ürün Başlığı:
              - 70 ile 80 karakter arasında olmalı.
           - Anahtar kelimeleri içermeli (Model, Renk, Önemli Özellik).
           - Marka ismini ASLA başlıkta kullanma.
           - Dikkat çekici ve net olmalı.
           - Gereksiz kelimelerden kaçınılmalı.
           - Ürünle ilgisi olmayan özellikler ASLA yazılmamalı.

        2. Ürün Açıklaması:
           - HTML formatında olmalı (<p>, <ul>, <li> vb. kullan).
              - Okunaklı, ikna edici ve bilgilendirici olmalı.
           - Ürünün faydalarına odaklanmalı.
           - Özellikleri maddeler halinde listele.
           - SEO uyumlu anahtar kelimeler doğal bir şekilde geçirilmeli.
              - Minimum 350 kelime, maksimum 550 kelime olmalı (Lütfen uzun ve detaylı yaz).
           - Ürünle ilgisi olmayan özellikler ASLA yazılmamalı.

        ÇIKTI FORMATI (JSON):
        {{
            "title": "Yeni Ürün Başlığı",
            "description": "Yeni HTML Ürün Açıklaması"
        }}
          Sadece JSON çıktısı ver, kod bloğu veya açıklama ekleme.
        """

    def generate_product_content(self, product_name, description, attributes):
        """
        Generates SEO optimized title and description for a product using the default SDK method.
        """
        prompt = self._get_prompt(product_name, description, attributes)

        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return self._clean_response(response.text)
        except Exception as e:
            raise Exception(f"AI Hatası: {str(e)}")

    def generate_with_key(self, product_name, description, attributes, api_key):
        """
        Generates content using a specific API key via REST API (Thread-safe).
        """
        prompt = self._get_prompt(product_name, description, attributes)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 429:
                    # Rate limit hit
                    if attempt < max_retries - 1:
                        # Wait 60 seconds for quota reset (Free tier usually resets every minute)
                        time.sleep(62) 
                        continue
                    else:
                        error_json = response.json()
                        error_msg = error_json.get('error', {}).get('message', response.text)
                        raise Exception(f"API Hatası (429 - Kota Aşıldı): {error_msg}")

                if not response.ok:
                    raise Exception(f"API Hatası ({response.status_code}): {response.text}")
                
                result = response.json()
                
                if 'candidates' in result and result['candidates']:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return self._clean_response(text)
                else:
                    raise Exception("API geçerli bir yanıt döndürmedi.")
                    
            except Exception as e:
                last_error = e
                if "429" not in str(e) and attempt < max_retries - 1:
                    time.sleep(2) # Short wait for other errors
                    continue
                if "429" in str(e):
                    raise e # Re-raise 429 immediately if we ran out of retries
        
        raise Exception(f"REST API Hatası: {str(last_error)}")

    def _get_category_match_prompt(self, product_name, description, candidates):
        candidates_str = "\n".join([f"ID: {c['id']}, Path: {c.get('path', c['name'])}" for c in candidates])
        return f"""
        Sen bir e-ticaret kategori uzmanısın. Aşağıdaki ürün için verilen aday kategoriler arasından EN UYGUN olanı seçmelisin.

        ÜRÜN BİLGİLERİ:
        Ürün Adı: {product_name}
        Açıklama: {description[:500]}...

        ADAY KATEGORİLER:
        {candidates_str}

        GÖREV:
        1. Ürün adını ve açıklamasını dikkatlice analiz et. Ürünün tam işlevini belirle.
        2. Aday kategorilerin tam yollarını (Path) incele. Sadece isme değil, kategori yoluna da bak.
        3. Yanıltıcı kelimelere dikkat et. (Örn: "Çelik Süzgeç" için "Çay Süzgeci" seçme, eğer ürün çay için değilse).
        4. En spesifik ve doğru "leaf" (uç) kategoriyi seç.
        5. ASLA "None" döndürme.

        ÇIKTI FORMATI (JSON):
        {{
            "selected_category_id": 12345, // Seçilen ID (Integer)
            "reason": "Seçim nedeni"
        }}
        Sadece JSON çıktısı ver.
        """

    def match_category_with_key(self, product_name, description, candidates, api_key):
        """
        Matches a product to a category using AI.
        """
        prompt = self._get_category_match_prompt(product_name, description, candidates)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                
                if response.status_code == 429:
                    # Rate limit hit
                    if attempt < max_retries - 1:
                        # Wait 60 seconds for quota reset (Free tier usually resets every minute)
                        time.sleep(62) 
                        continue
                    else:
                        error_json = response.json()
                        error_msg = error_json.get('error', {}).get('message', response.text)
                        raise Exception(f"API Hatası (429 - Kota Aşıldı): {error_msg}")

                if not response.ok:
                    raise Exception(f"API Hatası ({response.status_code}): {response.text}")
                
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    cleaned_text = self._clean_response(text)
                    try:
                        data = json.loads(cleaned_text)
                        return data.get('selected_category_id')
                    except json.JSONDecodeError:
                        raise Exception(f"JSON Ayrıştırma Hatası: {cleaned_text}")
                else:
                    raise Exception(f"API Yanıtı Boş veya Aday Yok: {result}")

            except Exception as e:
                last_error = e
                if "429" not in str(e) and attempt < max_retries - 1:
                    time.sleep(2) # Short wait for other errors
                    continue
                if "429" in str(e):
                    raise e # Re-raise 429 immediately if we ran out of retries
        
        raise Exception(f"AI Servis Hatası: {str(last_error)}")

    def _clean_response(self, text):
        if text.strip().startswith("```json"):
            text = text.strip()[7:]
        elif text.strip().startswith("```"):
            text = text.strip()[3:]
        
        if text.strip().endswith("```"):
            text = text.strip()[:-3]
            
        return text.strip()
