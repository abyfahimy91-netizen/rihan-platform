from django.urls import path
from .views import ProductListView, ProductDetailView

app_name = 'catalog'

urlpatterns = [
    # Homepage - Product List
    path('', ProductListView.as_view(), name='product_list'),
    
    # Product Detail (SEO-friendly slug URL)
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
]
