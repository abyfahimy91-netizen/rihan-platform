"""
Catalog Views - Block-based Product Storytelling (D-079)
"""
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Product


class ProductListView(ListView):
    """List of active products (Homepage)"""
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(
            status='active',
            deleted_at__isnull=True
        ).select_related('category', 'supplier').order_by('-is_featured', '-created_at')
        
        # Filter by category slug
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Search
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(short_description__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class ProductDetailView(DetailView):
    """Product detail page with block-based storytelling"""
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Product.objects.filter(
            status='active',
            deleted_at__isnull=True
        ).select_related('category', 'supplier')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Get blocks ordered by sort_order (both direct and linked)
        direct_blocks = product.direct_blocks.filter(
            is_active=True
        ).order_by('sort_order')
        
        linked_blocks = product.product_blocks.filter(
            block__is_active=True
        ).order_by('sort_order').select_related('block')
        
        # Merge blocks: direct blocks first, then linked blocks
        context['blocks'] = list(direct_blocks)
        context['blocks'] += [pb.block for pb in linked_blocks]
        
        # SEO
        context['seo_title'] = product.seo_title or product.name
        context['seo_description'] = product.seo_description or product.short_description
        context['seo_keywords'] = product.seo_keywords or []
        
        # Related products (same category)
        context['related_products'] = Product.objects.filter(
            category=product.category,
            status='active',
            deleted_at__isnull=True
        ).exclude(id=product.id)[:4]
        
        return context
