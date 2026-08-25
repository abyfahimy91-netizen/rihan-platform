from django.urls import path
from .views import ProductListView, ProductDetailView
from .views import product_share_view, short_link_redirect

app_name = 'catalog'

urlpatterns = [
    # Homepage - Product List
    path('', ProductListView.as_view(), name='product_list'),

    # D-107: لینک کوتاه تمیز برای اشتراک‌گذاری — rihan360.ir/p/<code>/
    path('p/<str:code>/', short_link_redirect, name='short_link'),

    # Product Detail (SEO-friendly slug URL)
    path('products/<str:slug>/', ProductDetailView.as_view(), name='product_detail'),

    # شمارنده اشتراک‌گذاری + لینک کوتاه و متن قابل ویرایش (D-104 / D-107)
    path('products/<str:slug>/share/', product_share_view, name='product_share'),
]
