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
