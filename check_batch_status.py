import os
import django
import sys
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from integrations.services import TrendyolService

def check_batch(batch_id):
    # Get the first user (assuming single user system or main admin)
    user = User.objects.first()
    if not user:
        print("No user found in database.")
        return

    print(f"Checking batch status for Batch ID: {batch_id}")
    try:
        service = TrendyolService(user)
        result = service.check_batch_request(batch_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        batch_id = sys.argv[1]
    else:
        # Default to the one provided by the user if not specified
        batch_id = "9ea532f9-21ab-4f2a-8221-de04e90bd402-1764024230"
    
    check_batch(batch_id)
