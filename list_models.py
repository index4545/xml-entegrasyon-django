import google.generativeai as genai
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from integrations.models import GeminiSettings

try:
    settings = GeminiSettings.objects.first()
    if not settings:
        print("Ayarlar bulunamadı.")
    else:
        genai.configure(api_key=settings.api_key)
        print("Mevcut Modeller:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
except Exception as e:
    print(f"Hata: {e}")
