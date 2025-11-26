from django.db import migrations, models

def set_original_content(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.all():
        fields_to_update = []
        if not product.original_name:
            product.original_name = product.name
            fields_to_update.append('original_name')
        if not product.original_description:
            product.original_description = product.description
            fields_to_update.append('original_description')
        if fields_to_update:
            product.save(update_fields=fields_to_update)

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_trendyolbatchrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='ai_generated_description',
            field=models.TextField(blank=True, null=True, verbose_name='AI Açıklaması'),
        ),
        migrations.AddField(
            model_name='product',
            name='ai_generated_name',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='AI Ürün Adı'),
        ),
        migrations.AddField(
            model_name='product',
            name='ai_last_error',
            field=models.TextField(blank=True, null=True, verbose_name='Son AI Hatası'),
        ),
        migrations.AddField(
            model_name='product',
            name='ai_last_run_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Son AI İşlemi'),
        ),
        migrations.AddField(
            model_name='product',
            name='ai_status',
            field=models.CharField(choices=[('original', 'Orijinal'), ('processing', 'İşleniyor'), ('generated', 'AI Güncellendi'), ('error', 'Hata')], default='original', max_length=20, verbose_name='AI İçerik Durumu'),
        ),
        migrations.AddField(
            model_name='product',
            name='original_description',
            field=models.TextField(blank=True, null=True, verbose_name='Orijinal Açıklama'),
        ),
        migrations.AddField(
            model_name='product',
            name='original_name',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Orijinal Ürün Adı'),
        ),
        migrations.RunPython(set_original_content, noop),
    ]
