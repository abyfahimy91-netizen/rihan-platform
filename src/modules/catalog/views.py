"""
Catalog Views - Block-based Product Storytelling (D-079)
+ صفحه فروش اقناعی و اشتراک‌گذاری (D-104)
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from django.db.models import Q, F

from .models import Product, ShortLink

from src.core.fa import fa_digits


@require_POST
def product_share_view(request, slug):
    """شمارنده اشتراک‌گذاری + برگرداندن لینک کوتاه و متن قابل ویرایش (D-107)"""
    product = get_object_or_404(
        Product, slug=slug, status='active', deleted_at__isnull=True
    )
    Product.objects.filter(pk=product.pk).update(share_count=F('share_count') + 1)
    product.refresh_from_db(fields=['share_count'])
    channel = (request.POST.get('channel') or '')[:30]

    # D-107: متن و لینک از تنظیمات ادمین — یک منبع حقیقت برای همه کانال‌ها
    from src.modules.pages.models import SiteSettings
    s = SiteSettings.objects.first()
    brand = (getattr(s, 'brand_name_latin', '') or 'Rihan').strip()
    msg = (getattr(s, 'share_message_text', '') or '').strip() or (
        '✨ یه انتخاب خاص برات پیدا کردم؛ یه نگاه بنداز، ارزشش رو داره!')
    hashtags = (getattr(s, 'share_hashtags', '') or '').strip()

    try:
        code = ShortLink.get_for_product(product).code
        short_url = request.build_absolute_uri(f'/p/{code}/')
    except Exception:
        short_url = request.build_absolute_uri(
            product.get_absolute_url() if hasattr(product, 'get_absolute_url')
            else f'/products/{product.slug}/')

    caption = f'{msg}\n{product.name} | {brand}\n{short_url}'
    if hashtags:
        caption += f'\n\n{hashtags}'

    return JsonResponse({
        'ok': True,
        'count': product.share_count,
        'count_fa': fa_digits(f'{product.share_count:,}'),
        'channel': channel,
        'url': short_url,
        'text': caption,
    })


def short_link_redirect(request, code):
    """rihan360.ir/p/<code>/ → صفحه محصول (لینک تمیز برای پیام‌رسان‌ها)"""
    link = get_object_or_404(
        ShortLink.objects.select_related('product'), code=code.strip())
    return redirect('catalog:product_detail', slug=link.product.slug)


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
        # SEO: نام دسته برای تایتل متمایز صفحهٔ دسته‌بندی
        context['current_category_name'] = ''
        if context['current_category']:
            from .models import Category
            _cat = Category.objects.filter(slug=context['current_category']).first()
            if _cat:
                context['current_category_name'] = _cat.name
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

        # ── D-107: متادیتای اشتراک‌گذاری + لینک کوتاه + برند لاتین ──
        from src.modules.pages.models import SiteSettings
        s = SiteSettings.objects.first()
        brand = (getattr(s, 'brand_name_latin', '') or 'Rihan').strip()
        msg = (getattr(s, 'share_message_text', '') or '').strip() or (
            '✨ یه انتخاب خاص برات پیدا کردم؛ یه نگاه بنداز، ارزشش رو داره!')
        hashtags = (getattr(s, 'share_hashtags', '') or '').strip()
        try:
            code = ShortLink.get_for_product(product).code
            context['short_url'] = self.request.build_absolute_uri(f'/p/{code}/')
        except Exception:
            context['short_url'] = self.request.build_absolute_uri(
                f'/products/{product.slug}/')
        caption = f'{msg}\n{product.name} | {brand}\n{context["short_url"]}'
        if hashtags:
            caption += f'\n\n{hashtags}'
        context['share_caption'] = caption
        context['brand_latin'] = brand

        # OG image مطلق با cache-buster — نسخه اصلی JPEG برای سازگاری حداکثری پیام‌رسان‌ها
        img_url = ''
        try:
            original = ''
            try:
                first_img = product.gallery.first()
                if first_img and first_img.image:
                    original = first_img.image.url
            except Exception:
                original = ''
            raw = original or (str(product.main_image_url) if product.main_image_url else '')
            if raw:
                img_url = self.request.build_absolute_uri(raw)
                bust = getattr(product, 'updated_at', None)
                if bust:
                    img_url += f'?v={int(bust.timestamp())}'
        except Exception:
            img_url = ''
        context['og_image'] = img_url
        
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
        
        # ── D-118 GEO: آمار «همهٔ» نظرات تاییدشده برای aggregateRating اسکیما
        #    (برخلاف review_count که سقف نمایش ۱۲ دارد) + اعتبار قیمت اسکیما
        from datetime import timedelta
        from django.db.models import Avg, Count
        from django.utils import timezone
        from src.modules.reviews.models import Review

        rev_stats = Review.objects.filter(product=product, is_approved=True).aggregate(
            total=Count('id'), avg=Avg('rating'))
        context['review_total'] = rev_stats['total'] or 0
        context['review_avg'] = round(rev_stats['avg'], 1) if rev_stats['avg'] else 0
        context['price_valid_until'] = (timezone.localdate() + timedelta(days=180)).isoformat()
        
        
        # SEO
        context['seo_title'] = product.seo_title or product.name
        context['seo_description'] = product.seo_description or product.short_description
        context['seo_keywords'] = product.seo_keywords or []

        # ─── صفحه فروش اقناعی (D-104) ───
        from src.modules.reviews.models import Review
        from src.modules.pages.models import SiteSettings
        approved_reviews = (
            Review.objects.filter(product=product, is_approved=True)
            .select_related('user').order_by('-created_at')[:12]
        )
        review_count = approved_reviews.count()
        avg_rating = 0
        if review_count:
            avg_rating = round(sum(r.rating for r in approved_reviews) / review_count, 1)

        _ss = SiteSettings.load()
        context.update(
            faqs=product.faqs.filter(is_active=True).order_by('sort_order', 'id'),
            product_reviews=approved_reviews,
            review_count=review_count,
            avg_rating=avg_rating,
            discount_percent=product.discount_percent,
            # تعهدهای زیر دکمه خرید از تنظیمات سایت (D-104)
            buy_commitments=[
                ln.strip() for ln in (_ss.buy_commitments or '').splitlines()
                if ln.strip()
            ],
        )

        # Related products (same category)
        context['related_products'] = Product.objects.filter(
            category=product.category,
            status='active',
            deleted_at__isnull=True
        ).exclude(id=product.id)[:4]
        
        return context
