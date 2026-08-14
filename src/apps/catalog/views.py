from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from .models import Category, Product, ContentBlock
from .serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer, ContentBlockSerializer

def product_list_view(request):
    categories = Category.objects.filter(is_active=True)
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    products = Product.objects.filter(is_available=True)
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search_query:
        products = products.filter(title__icontains=search_query)

    context = {'categories': categories, 'products': products, 'selected_category': category_slug, 'search_query': search_query}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'catalog/partials/product_grid.html', context)
    return render(request, 'catalog/list.html', context)

def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related('images', 'content_blocks'), slug=slug, is_available=True)
    context = {'product': product, 'content_blocks': product.content_blocks.filter(is_active=True)}
    return render(request, 'catalog/detail.html', context)

class CategoryListAPI(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer

class ProductListAPI(generics.ListAPIView):
    serializer_class = ProductListSerializer
    def get_queryset(self):
        qs = Product.objects.filter(is_available=True)
        cat = self.request.query_params.get('category')
        if cat:
            qs = qs.filter(category__slug=cat)
        return qs

class ProductDetailAPI(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'

class ContentBlockListAPI(generics.ListAPIView):
    serializer_class = ContentBlockSerializer
    def get_queryset(self):
        return ContentBlock.objects.filter(product__slug=self.kwargs.get('product_slug'), is_active=True)

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.orders.models import OrderItem

@login_required
def supplier_dashboard_view(request):
    """داشبورد اختصاصی تأمین‌کننده با تفکیک کامل دسترسی (M4 - D-051)"""
    if not hasattr(request.user, 'supplier_profile') and not request.user.is_superuser:
        raise PermissionDenied("دسترسی فقط برای تأمین‌کنندگان مجاز ریهان امکان‌پذیر است.")

    supplier = getattr(request.user, 'supplier_profile', None)
    if not supplier and request.user.is_superuser:
        # اگر ادمین اصلی خواست پنل را ببیند
        from .models import Supplier
        supplier = Supplier.objects.first()

    if supplier:
        items = OrderItem.objects.filter(product__supplier=supplier).select_related('order', 'product').order_by('-order__created_at')
        products = supplier.products.all()
    else:
        items = []
        products = []

    context = {
        'supplier': supplier,
        'order_items': items,
        'products': products
    }
    return render(request, 'catalog/supplier_dashboard.html', context)

@require_POST
@login_required
def supplier_update_tracking_view(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    supplier = getattr(request.user, 'supplier_profile', None)
    
    if not request.user.is_superuser and item.product.supplier != supplier:
        raise PermissionDenied()

    tracking_code = request.POST.get('tracking_code', '').strip()
    if tracking_code:
        order = item.order
        order.tracking_code = tracking_code
        order.status = 'shipped'
        order.save()
        messages.success(request, f"کد رهگیری برای سفارش {order.order_number} با موفقیت ثبت شد.")

    return redirect('supplier_dashboard')
