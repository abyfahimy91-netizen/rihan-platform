"""
تگ تمپلیت سایدبار اختصاصی پنل ادمین ریحان.
مدل‌ها را گروه‌بندی کرده و لینک هرکدام را فقط برای کاربران دارای دسترسی می‌سازد.
هر مدلی که در آینده ثبت شود، خودکار زیر گروه «سایر» ظاهر می‌شود.
"""
from django import template
from django.urls import NoReverseMatch, reverse
from django.contrib.admin import site as admin_site

register = template.Library()

# (عنوان گروه، [(app_label.model_name, عنوان فارسی), ...])
GROUPS = [
    ("🛍 فروشگاه", [
        ("catalog.product", "محصولات"),
        ("catalog.category", "دسته‌بندی‌ها"),
        ("catalog.supplier", "تامین‌کنندگان"),
        ("catalog.productimage", "تصاویر محصولات"),
    ]),
    ("📦 موجودی انبار", [
        ("catalog.inventory", "موجودی کالاها"),
        ("catalog.inventorytransaction", "تراکنش‌های موجودی"),
    ]),
    ("🧾 سفارش‌ها", [
        ("order.order", "سفارش‌ها"),
        ("order.payment", "پرداخت‌ها"),
        ("order.shipment", "مرسوله‌ها"),
        ("order.notificationlog", "لاگ اطلاع‌رسانی"),
        ("order.address", "آدرس‌ها"),
    ]),
    ("⭐ نظرات مشتریان", [
        ("reviews.review", "نظرات"),
    ]),
    ("📞 سرنخ‌های فروش", [
        ("leads.lead", "سرنخ‌ها"),
    ]),
    ("🧩 محتوای سایت", [
        ("pages.sitesettings", "⚙️ تنظیمات صفحه اصلی و سایت"),
        ("catalog.contentblock", "بلوک‌های محتوا"),
    ]),
    ("👥 کاربران و نقش‌ها", [
        ("auth.user", "کاربران"),
        ("rbac.role", "نقش‌ها"),
        ("rbac.userrole", "نقش اختصاص‌یافته"),
    ]),
]


def _badge_counts():
    """D-119: تعداد کارهای در انتظار برای بج قرمز کنار منو — سبک و فقط-خواندنی"""
    badges = {}
    try:
        from src.modules.order.models import Payment, Shipment
        pp = Payment.objects.filter(status=Payment.PaymentStatus.PENDING_REVIEW).count()
        if pp:
            badges['order.payment'] = pp
        ns = Shipment.objects.filter(status=Shipment.Status.NEW).count()
        if ns:
            badges['order.shipment'] = ns
        try:
            from src.modules.reviews.models import Review
            pr = Review.objects.filter(is_approved=False).count()
            if pr:
                badges['reviews.review'] = pr
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
    for title, entries in GROUPS:
        items = []
        for k, t in entries:
            if k in registry:
                item = {"title": t, "url": registry[k], "badge": badges.get(k, 0)}
                items.append(item)
                used.add(k)
        if items:
            groups.append({"title": title, "items": items})
        used.update(k for k, _t in entries if k in registry)

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
