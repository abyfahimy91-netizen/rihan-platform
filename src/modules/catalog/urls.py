from django.urls import path
from .views import ProductListView, ProductDetailView
from .views import product_share_view

app_name = 'catalog'

urlpatterns = [
    # Homepage - Product List
    path('', ProductListView.as_view(), name='product_list'),
    
    # Product Detail (SEO-friendly slug URL)
    path('products/<str:slug>/', ProductDetailView.as_view(), name='product_detail'),

    # شمارنده اشتراک‌گذاری (D-104)
    path('products/<str:slug>/share/', product_share_view, name='product_share'),
]
