from django.urls import path
from . import views

urlpatterns = [
    path('supplier/dashboard/', views.supplier_dashboard_view, name='supplier_dashboard'),
    path('supplier/item/<int:item_id>/tracking/', views.supplier_update_tracking_view, name='supplier_update_tracking'),
    path('products/', views.product_list_view, name='product_list'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('api/catalog/categories/', views.CategoryListAPI.as_view(), name='api_categories'),
    path('api/catalog/products/', views.ProductListAPI.as_view(), name='api_products'),
    path('api/catalog/products/<slug:slug>/', views.ProductDetailAPI.as_view(), name='api_product_detail'),
    path('api/catalog/products/<slug:product_slug>/blocks/', views.ContentBlockListAPI.as_view(), name='api_product_blocks'),
]
