from django.urls import path
from . import views
from . import batch_views
from . import ai_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('sync-xml/', views.sync_xml, name='sync_xml'),
    path('send-trendyol/', views.send_bulk_trendyol, name='send_bulk_trendyol'),
    path('match-categories/', views.match_categories, name='match_categories'),
    path('match-categories/<int:mapping_id>/attributes/', views.map_attributes, name='map_attributes'),
    path('match-brands/', views.match_brands, name='match_brands'),
    path('auto-match-categories/', views.auto_match_categories, name='auto_match_categories'),
    path('publish-wizard/', views.publish_wizard, name='publish_wizard'),
    path('supplier-settings/', views.supplier_settings, name='supplier_settings'),
    path('batch-requests/', batch_views.batch_requests_list, name='batch_requests_list'),
    path('batch-requests/<str:batch_id>/check/', batch_views.check_batch_status, name='check_batch_status'),
    path('api/search-brands/', views.search_trendyol_brands, name='search_trendyol_brands'),
    path('api/search-categories/', views.search_trendyol_categories, name='search_trendyol_categories'),
    path('api/background-processes/', views.get_background_processes, name='get_background_processes'),
    path('manage-trendyol/', views.manage_trendyol_products, name='manage_trendyol_products'),
    path('sync-selected/', views.sync_selected_products, name='sync_selected_products'),
    path('sync-all/', views.sync_all_products, name='sync_all_products'),
    path('ai-tools/', ai_views.ai_tools, name='ai_tools'),
    path('ai-generate/', ai_views.ai_generate, name='ai_generate'),
    path('ai-match-categories/', ai_views.ai_match_categories, name='ai_match_categories'),
    path('ai-generate/<int:pk>/', ai_views.ai_generate_single, name='ai_generate_single'),
    path('ai-revert/<int:pk>/', ai_views.ai_revert_original, name='ai_revert_original'),
    path('api/test-frame/', views.test_frame_creation, name='test_frame_creation'),
]
