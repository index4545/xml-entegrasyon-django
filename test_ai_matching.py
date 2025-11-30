import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from products.ai_views import process_attribute_match_task
from integrations.models import GeminiSettings
from django.contrib.auth.models import User

# Get first user
u = User.objects.first()
print(f"User: {u.username}")

# Get API key
s = GeminiSettings.objects.get(user=u)
key = s.api_keys.first().key
print(f"Using API key: {key[:10]}...")

# Test with product ID 1
result = process_attribute_match_task(1, key, u.id)
print(f"Result: {result}")