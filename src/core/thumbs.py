"""نسخه بهینه‌شده وب تصاویر محصول — تولید خودکار WebP با کش دیسکی

نخستین فراخوانی نسخه فشرده را می‌سازد و در MEDIA_ROOT/cache نگه می‌دارد؛
فراخوانی‌های بعدی فقط از کش خوانده می‌شود. اگر Pillow نبود یا خطایی رخ داد،
نشانی اصلی تصویر برگردانده می‌شود تا هیچ‌گاه نمایش عکس نشکند.
"""
import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_MEMO = {}


def optimized_url(image_file, size=900):
    """نشانی نسخه WebP بهینه از فیلد ImageField — با کش حافظه و دیسک"""
    name = getattr(image_file, "name", "")
    if not name:
        return None
    key = "{}:{}".format(name, size)
    if key in _MEMO:
        return _MEMO[key]

    out_rel = Path("cache").with_segments(*Path("cache").parts) if False else Path("cache") / Path(name).parent
    out_rel = out_rel / (Path(name).stem + "_{}.webp".format(size))
    out_path = Path(settings.MEDIA_ROOT) / out_rel
    url = settings.MEDIA_URL + out_rel.as_posix()

    if not out_path.exists():
        try:
            from PIL import Image
            src_path = Path(settings.MEDIA_ROOT) / name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = out_path.with_suffix(".tmp")
            with Image.open(src_path) as im:
                rgb = im.convert("RGB")
                rgb.thumbnail((size, size))
                rgb.save(tmp_path, "WEBP", quality=82, method=6)
            os.replace(tmp_path, out_path)
        except Exception as e:
            logger.warning("thumbnail failed for %s: %s", name, e)
            fallback = None
            try:
                fallback = image_file.url
            except Exception:
                pass
            _MEMO[key] = fallback
            return fallback

    _MEMO[key] = url
    return url
