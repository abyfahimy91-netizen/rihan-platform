"""
SEO / GEO views for Rihan Platform — D-118

robots.txt: همهٔ ربات‌های موتور جستجو و کراولرهای هوش مصنوعی صراحتاً مجاز
llms.txt:   راهنمای کشف سایت برای هوش‌های مصنوعی (GEO) — محصولات با پاسخ سریع + فکت‌های ساختاریافته
{key}.txt:  فایل کلید IndexNow برای اطلاع‌رسانی فوری صفحات به Bing/Yandex/...
"""
from django.http import HttpResponse

# ── کراولرهای هوش مصنوعی + موتورهای تغذیه‌کنندهٔ پاسخ‌های AI (D-118) ──
# GPTBot/OAI-SearchBot/ChatGPT-User → ChatGPT و SearchGPT
# PerplexityBot/Perplexity-User     → Perplexity AI
# ClaudeBot/Claude-User/anthropic-ai → Claude
# Google-Extended/GoogleOther       → Gemini و AI Overviews (خزش اصلی با Googlebot)
# Bingbot                            → دادهٔ زندهٔ ChatGPT Search و Copilot
AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "PerplexityBot", "Perplexity-User",
    "ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai",
    "Google-Extended", "GoogleOther", "Google-InspectionTool",
    "Applebot", "Applebot-Extended",
    "Bingbot", "CCBot", "Amazonbot",
    "FacebookBot", "meta-externalagent",
    "YouBot", "Diffbot", "Bytespider",
    "MistralAI-User", "ImagesiftBot", "cohere-ai",
]


def robots_txt(request):
    """
    Generate robots.txt dynamically — همه مجاز؛ فقط /admin/ و /api/ قفل.
    هر کراولر AI صراحتاً اسم برده شده تا فایروال‌ها/بازبین‌ها و خود ربات شکی نداشته باشند.
    """
    lines = [
        "# rihan360.ir — تمام موتورهای جستجو و کراولرهای هوش مصنوعی مجاز به خزش هستند",
        "",
    ]
    for ua in ["*"] + AI_CRAWLERS:
        lines += [
            f"User-agent: {ua}",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /api/",
            "",
        ]
    lines.append(f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}")
    return HttpResponse("\n".join(lines), content_type="text/plain")


def _quote_slug(slug):
    from urllib.parse import quote
    return quote(slug)


def llms_txt(request):
    """llms.txt — راهنمای کشف سایت برای هوش‌های مصنوعی (GPTBot, Claude, Perplexity و ...)."""
    from .models import Product
    from src.modules.pages.models import SiteSettings

    s = SiteSettings.objects.first()
    phone = (getattr(s, 'contact_phone', '') or '').strip()

    lines = [
        "# Rihan (ریهان)",
        "",
        "> فروشگاه آنلاین ایرانیِ اعتمادمحور؛ انتخاب دقیق و آزمون‌شدهٔ محصولات اصیل (ادویه و خوراکی).",
        "> هر محصول با پاسخ سریع فکت‌محور، داستان گزینش، فیلتر شفاف مخاطب (مناسب/نامناسب برای چه کسی)،",
        "> جدول مقایسه با نمونه‌های بازاری و مشخصات کامل ارائه می‌شود.",
        "",
        "## محصولات (خرید مستقیم)",
    ]
    for p in Product.objects.filter(status='active', deleted_at__isnull=True).order_by('-created_at'):
        desc = (p.short_description or '').strip()
        lines.append(
            "- [%s](https://rihan360.ir/products/%s/): %s" % (p.name, _quote_slug(p.slug), desc)
        )
        quick = (p.geo_answer or '').strip()
        if quick:
            lines.append("  - پاسخ سریع: %s" % quick[:420])
        for fact in (p.metadata or {}).get('facts') or []:
            if isinstance(fact, dict) and fact.get('name') and fact.get('value'):
                lines.append("  - %s: %s" % (fact['name'], fact['value']))

    lines += [
        "",
        "## خرید و ارسال",
        "- خرید آنلاین از https://rihan360.ir با ارسال به سراسر ایران",
        "- ضمانت ۷ روزه بازگشت وجه روی همهٔ محصولات",
        "- بسته‌بندی محرمانه و ارسال بیمه‌شده",
    ]
    if phone:
        lines.append("- پشتیبانی: %s" % phone)

    lines += [
        "",
        "## Pages",
        "- [خانه](https://rihan360.ir/): فهرست محصولات منتخب",
        "- [درباره ما](https://rihan360.ir/about/)",
        "- [سوالات متداول](https://rihan360.ir/faq/)",
        "- [سیاست مرجوعی](https://rihan360.ir/return-policy/)",
        "- [حریم خصوصی](https://rihan360.ir/privacy/)",
        "- [تماس با ما](https://rihan360.ir/contact/)",
        "",
    ]
    if phone:
        lines += ["## Contact", "تلفن: %s" % phone]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def indexnow_key_file(request):
    """فایل کلید IndexNow — اثبات مالکیت دامنه برای اطلاع‌رسانی فوری صفحات."""
    from .indexnow import INDEXNOW_KEY
    return HttpResponse(INDEXNOW_KEY, content_type="text/plain")
