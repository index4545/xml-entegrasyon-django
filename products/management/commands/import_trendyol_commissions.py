import json
import os
import zlib
from django.core.management.base import BaseCommand
from products.models import TrendyolCategory

class Command(BaseCommand):
    help = 'Imports Trendyol category commissions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the JSON file containing commissions')

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading JSON: {e}'))
            return

        self.stdout.write(f"Found {len(data)} categories. Importing...")
        
        count_created = 0
        count_updated = 0
        
        for item in data:
            ty_id = item.get('id') or item.get('trendyol_id')
            name = item.get('name') or item.get('category_name')
            rate = item.get('commission') or item.get('commission_rate')
            
            if not name:
                continue

            if not ty_id:
                # Generate a pseudo ID from name
                # Use CRC32 to get a consistent integer
                ty_id = zlib.crc32(name.encode('utf-8'))
            
            try:
                obj, created = TrendyolCategory.objects.update_or_create(
                    trendyol_id=ty_id,
                    defaults={
                        'name': name,
                        'commission_rate': rate or 0
                    }
                )
                if created:
                    count_created += 1
                else:
                    count_updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving {name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created: {count_created}, Updated: {count_updated}"))
