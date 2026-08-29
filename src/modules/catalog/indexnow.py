"""
IndexNow protocol (D-118 GEO) — اطلاع‌رسانی فوری صفحات به موتورهای تغذیه‌کنندهٔ
هوش مصنوعی و جستجو (Bing ← ChatGPT Search / Copilot، Yandex، Seznam، Naver، Yep).

کلید IndexNow راز نیست؛ یک شناسهٔ عمومی است که مالکیت دامنه را با فایل
https://rihan360.ir/{key}.txt اثبات می‌کند (ویو indexnow_key_file در seo_views).
"""
import json
import logging
import threading
import urllib.request

logger = logging.getLogger(__name__)

INDEXNOW_KEY = "e82db14450267428bb56d19eac4c3c1b"
HOST = "rihan360.ir"
ENDPOINT = "https://api.indexnow.org/IndexNow"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"


def product_url(product):
    """URL مطلق صفحه محصول (اسلاگ یونیکد percent-encode می‌شود)."""
    from urllib.parse import quote
    return "https://%s/products/%s/" % (HOST, quote(product.slug))


def collect_all_urls():
    """همهٔ صفحات عمومی قابل معرفی به IndexNow (مطابق sitemap)."""
    from .models import Product
    urls = [f"https://{HOST}/"]
    for p in Product.objects.filter(status='active', deleted_at__isnull=True):
        urls.append(product_url(p))
    urls += [
        f"https://{HOST}/{path}/"
        for path in ("about", "contact", "faq", "return-policy", "privacy")
    ]
    return urls


def submit_urls(url_list):
    """ارسال URLها به api.indexnow.org؛ کد HTTP برگشتی را می‌دهد (200/202 = موفق)."""
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": list(url_list),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "rihan360-indexnow/1.0"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.status


def _safe_submit(url_list):
    try:
        status = submit_urls(url_list)
        logger.info("IndexNow: %d URL submitted (HTTP %s)", len(url_list), status)
    except Exception as exc:  # هرگز جریان اصلی را خراب نکن
        logger.warning("IndexNow submit failed: %s", exc)


def submit_product_async(product):
    """پس از save محصول فعال، URL آن را در پس‌زمینه به IndexNow می‌دهد (best-effort)."""
    import sys
    if 'test' in sys.argv:  # در تست‌ها هیچ تماس شبکه‌ای
        return
    if getattr(product, 'status', '') != 'active' or product.deleted_at is not None:
        return
    threading.Thread(
        target=_safe_submit, args=([product_url(product)],), daemon=True
    ).start()
