import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Supplier
from django.core.management import call_command

def setup():
    # Create Superuser
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Superuser 'admin' created.")
    else:
        print("Superuser 'admin' already exists.")

    # Create Supplier
    xml_url = "https://cdn1.xmlbankasi.com/p1/pjsymndiclkn/image/data/xml/urunler1.xml"
    supplier, created = Supplier.objects.get_or_create(
        name="Test Tedarikçi",
        defaults={'xml_url': xml_url}
    )
    if created:
        print(f"Supplier '{supplier.name}' created.")
    else:
        print(f"Supplier '{supplier.name}' already exists.")

    # Run Fetch Command
    print("Running fetch_xml command...")
    call_command('fetch_xml', supplier.id)

if __name__ == '__main__':
    setup()
