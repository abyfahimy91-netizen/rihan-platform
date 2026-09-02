"""
تگ تمپلیت سایدبار اختصاصی پنل ادمین ریحان.
مدل‌ها را گروه‌بندی کرده و لینک هرکدام را فقط برای کاربران دارای دسترسی می‌سازد.
هر مدلی که در آینده ثبت شود، خودکار زیر گروه «سایر» ظاهر می‌شود.
D-125: گروه «📈 ردیابی بازدید» با لینک اختصاصی پنل سرنخ‌ها + بج سرنخ داغ.
SALES-14050610: بازآرایی کامل گروه‌ها بر اساس جریان کار روزانهٔ اپراتور + مخفی‌سازی ماژول‌های قدیمی/فنی.
"""
from django import template
from django.urls import NoReverseMatch, reverse
from django.contrib.admin import site as admin_site

register = template.Library()

# ماژول‌های قدیمی/تکراری/فنی که نباید در سایدبار دیده شوند
HIDDEN_LABELS = {
    # family_panel قدیمی است و هیچ داده‌ای ندارد — تنظیمات اصلی: pages.sitesettings
    'family_panel.productdraft',
    'family_panel.sensitiveoperation',
    'family_panel.productcontent',
    'family_panel.activitylog',
    'family_panel.sitesettings',
    # دو لاگ ممیزی موازی — core.auditlog ملاک است (audit.AuditLog خالی)
    'audit.auditlog',
    # پنل سرنخ قدیمی (۰ رکورد) — VisitorLead و پنل /leads/panel/ ملاک‌اند
    'leads.lead',
    # فنی — برای اپراتور روزمره وسیلهٔ کار نیست
    'order.cart',
    'rihan_auth.adminloginattempt',
}

# (عنوان گروه، [(app_label.model_name, عنوان فارسی), ...])
# ترتیب گروه‌ها = ترتیب جریان کار روزانه: محصول → سفارش → کمپین → مشتری → محتوا → مالی → دسترسی → فنی
GROUPS = [
    ("🛍 محصولات و انبار", [
        ("catalog.product", "محصولات"),
        ("catalog.category", "دسته‌بندی‌ها"),
        ("catalog.productimage", "تصاویر محصولات"),
        ("catalog.inventory", "موجودی انبار"),
        ("catalog.inventorytransaction", "تاریخچه موجودی"),
        ("catalog.supplier", "تامین‌کنندگان"),
    ]),
    ("🧾 سفارش‌ها و ارسال", [
        ("order.order", "سفارش‌ها"),
        ("order.payment", "پرداخت‌های در انتظار تایید"),
        ("order.shipment", "مرسوله‌ها"),
        ("order.address", "آدرس‌ها"),
    ]),
    ("🎟 کمپین و تخفیف", [
        ("order.coupon", "کدهای تخفیف"),
    ]),
    ("📞 مشتریان و سرنخ‌ها", [
        ("__visitor_panel__", "داشبورد سرنخ‌های بازدید"),
        ("leads.visitorlead", "مدیریت سرنخ‌ها"),
        ("auth.user", "کاربران ثبت‌نامی"),
        ("reviews.review", "نظرات مشتریان"),
    ]),
    ("🧩 محتوای سایت", [
        ("pages.sitesettings", "⚙️ تنظیمات صفحه اصلی و سایت"),
        ("pages.faqitem", "❓ سوالات متداول"),
        ("catalog.contentblock", "بلوک‌های محتوا"),
    ]),
    ("💰 امور مالی", [
        ("__finance_dashboard__", "داشبورد مالی و تسویه"),
        ("order.shipment", None),  # تسویه مرسوله‌ای از داخل خود مرسوله‌ها
    ]),
    ("👥 دسترسی و نقش‌ها", [
        ("auth.group", "گروه‌های دسترسی"),
        ("rbac.role", "نقش‌ها"),
        ("rbac.userrole", "نقش اختصاص‌یافته"),
    ]),
    ("⚙️ فنی و امنیت (پیشرفته)", [
        ("order.bankaccount", "حساب‌های بانکی مقصد"),
        ("order.notificationlog", "لاگ اطلاع‌رسانی"),
        ("rihan_auth.authsettings", "تنظیمات ورود و پیامک"),
        ("rihan_auth.smsprovider", "سرویس‌دهنده‌های پیامک"),
        ("rihan_auth.loginattempt", "تلاش‌های ورود"),
        ("rihan_auth.phoneotp", "کدهای یکبارمصرف"),
        ("rihan_auth.devicetoken", "توکن‌های دستگاه"),
        ("core.featureflag", "پرچم‌های قابلیت"),
        ("core.auditlog", "لاگ‌های ممیزی"),
    ]),
]


def _badge_counts():
    """D-119/D-120/D-125: تعداد کارهای در انتظار برای بج قرمز کنار منو — سبک و فقط-خواندنی"""
    badges = {}
    try:
        from src.modules.order.models import Payment, Shipment
        pp = Payment.objects.filter(status=Payment.PaymentStatus.PENDING_REVIEW).count()
        if pp:
            badges['order.payment'] = pp
        ns = Shipment.objects.filter(status=Shipment.Status.NEW).count()
        if ns:
            badges['order.shipment'] = ns
        # طلب معوق تامین‌کننده‌ها (تحویل‌شده ولی تسویه‌نشده) → بج روی داشبورد مالی
        due = Shipment.objects.filter(
            fulfiller=Shipment.FulfillerType.SUPPLIER,
            supplier__isnull=False,
            settlement_status=Shipment.SettlementStatus.UNSETTLED,
            status=Shipment.Status.DELIVERED).count()
        if due:
            badges['__finance_dashboard__'] = due
        try:
            from src.modules.reviews.models import Review
            pr = Review.objects.filter(is_approved=False).count()
            if pr:
                badges['reviews.review'] = pr
        except Exception:
            pass
        # D-125: سرنخ‌های داغِ هنوز پیگیری‌نشده → بج روی داشبورد سرنخ‌ها
        try:
            from src.modules.leads.models import VisitorLead
            hot = VisitorLead.objects.filter(is_hot=True).exclude(
                status__in=[VisitorLead.LeadStatus.BUYER, VisitorLead.LeadStatus.JUNK]).count()
            if hot:
                badges['__visitor_panel__'] = hot
        except Exception:
            pass
    except Exception:
        pass
    return badges


@register.simple_tag(takes_context=True)
def rihan_sidebar(context):
    request = context.get("request")
    registry = {}
    for model, model_admin in admin_site._registry.items():
        label = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        if label in HIDDEN_LABELS:
            continue
        try:
            if request is None or not model_admin.has_view_or_change_permission(request, None):
                continue
            url = reverse(
                "admin:{}_{}_changelist".format(model._meta.app_label, model._meta.model_name)
            )
        except Exception:
            continue
        registry[label] = url

    groups, used = [], set()
    badges = _badge_counts()
    SPECIAL_URLS = {'__finance_dashboard__': '/finance/admin/',
                    '__visitor_panel__': '/leads/panel/'}
    for title, entries in GROUPS:
        items = []
        for k, t in entries:
            if t is None:      # آیتم بدون برچسب = لینک تکراری، نمایش نده
                continue
            if k in registry or k in SPECIAL_URLS:
                item = {"title": t, "url": registry.get(k, SPECIAL_URLS.get(k, '')), "badge": badges.get(k, 0)}
                items.append(item)
            if k in registry:
                used.add(k)
        if items:
            groups.append({"title": title, "items": items})

    leftovers = []
    for label, url in registry.items():
        if label not in used:
            meta = None
            for m in admin_site._registry:
                if "{}.{}".format(m._meta.app_label, m._meta.model_name) == label:
                    meta = m._meta
                    break
            name = str(meta.verbose_name_plural) if meta else label
            leftovers.append({"title": name, "url": url})
    if leftovers:
        groups.append({"title": "🗂 سایر بخش‌ها", "items": leftovers})

    return {"groups": groups}
