"""اعتبارسنجی آپلود تصاویر — لایه دفاعی امنیتی (فاز ۶)

روی فیلدهای مدل نصب می‌شود تا هم فرم‌ها و هم ادمین و هم هر مسیر آینده
بدون استثنا از همین قانون عبور کنند: فقط JPG/PNG/WebP و حداکثر ۵ مگابایت.
"""
import os

from django.core.exceptions import ValidationError

MAX_IMAGE_MB = 5
MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def validate_upload_image(f):
    """اعتبارسنجی پسوند، content-type و حجم فایل آپلودی."""
    size = getattr(f, 'size', 0) or 0
    if size > MAX_IMAGE_BYTES:
        raise ValidationError('حجم تصویر نباید بیش از %d مگابایت باشد.' % MAX_IMAGE_MB)

    name = getattr(f, 'name', '') or ''
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('فقط تصاویر JPG، PNG یا WebP پذیرفته می‌شود.')

    ctype = (getattr(f, 'content_type', '') or '').split(';')[0].strip().lower()
    if ctype and ctype not in ALLOWED_CONTENT_TYPES:
        raise ValidationError('نوع فایل مجاز نیست؛ فقط تصویر آپلود کنید.')
