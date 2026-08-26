"""
SEO views for Rihan Platform
"""
from django.http import HttpResponse


def robots_txt(request):
    """
    Generate robots.txt dynamically
    Allows all crawlers, points to sitemap
    """
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def llms_txt(request):
    """llms.txt — راهنمای کشف سایت برای هوش‌های مصنوعی (GPTBot, Claude, Perplexity و ...)."""
    from django.http import HttpResponse
    from .models import Product

    lines = [
        "# Rihan (ریهان)",
        "",
        "> فروشگاه آنلاین ایرانیِ اعتمادمحور؛ انتخاب دقیق و آزمون‌شدهٔ محصولات اصیل (ادویه و خوراکی).",
        "> هر محصول با داستان گزینش، فیلتر شفاف مخاطب (مناسب/نامناسب برای چه کسی) و مشخصات کامل ارائه می‌شود.",
        "",
        "## Pages",
        "- [خانه](https://rihan360.ir/): فهرست محصولات منتخب",
    ]
    for p in Product.objects.filter(status='active', deleted_at__isnull=True).order_by('-created_at'):
        desc = (p.short_description or '').strip()[:120]
        lines.append("- [محصول: %s](https://rihan360.ir/products/%s/): %s" % (p.name, p.slug, desc))
    lines += [
        "- [درباره ما](https://rihan360.ir/about/)",
        "- [سوالات متداول](https://rihan360.ir/faq/)",
        "- [سیاست مرجوعی](https://rihan360.ir/return-policy/)",
        "- [تماس با ما](https://rihan360.ir/contact/)",
        "",
        "## Contact",
        "تلفن: 09143183790",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
