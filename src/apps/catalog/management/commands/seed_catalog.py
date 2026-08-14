from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Product, ProductImage, ContentBlock

class Command(BaseCommand):
    help = 'Seed catalog data'

    def handle(self, *args, **options):
        cat_food, _ = Category.objects.get_or_create(slug="authentic-foods", defaults={"name": "خوراکی‌های اصیل و سنتی", "icon": "🌿", "sort_order": 1})
        cat_spices, _ = Category.objects.get_or_create(slug="spices-saffron", defaults={"name": "زعفران و چاشنی‌های ناب", "icon": "✨", "sort_order": 2})

        p1, _ = Product.objects.get_or_create(
            slug="sabalan-natural-honey",
            defaults={
                "category": cat_food,
                "title": "عسل گون و کوهستان سبلان (خالص و خام)",
                "sku": "RIHAN-HONEY-01",
                "summary": "عسل دست‌چین‌شده از زنبورستان‌های دامنه‌های مرتفع سبلان با ساکارز زیر ۲ درصد و تضمین آزمایشگاهی.",
                "price": 480000,
                "compare_at_price": 550000,
                "stock": 25,
                "is_available": True,
                "is_featured": True,
                "meta_title": "خرید عسل طبیعی سبلان با برگه آزمایش | ریهان",
                "meta_description": "عسل کوهستان سبلان با ساکارز زیر ۲ درصد و مستقیم از زنبوردار معتمد."
            }
        )
        ProductImage.objects.get_or_create(product=p1, defaults={"image_url": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=800", "alt_text": "عسل طبیعی سبلان ریهان", "is_primary": True})
        ContentBlock.objects.get_or_create(product=p1, block_type="story", defaults={"title": "روایت اصالت و خاستگاه", "subtitle": "از مراتع ۲۰۰۰ متری سبلان تا سفره شما", "content": "این عسل از مراتع بکر سبلان برداشت شده و کاملاً خام و بدون حرارت است.", "sort_order": 1})
        ContentBlock.objects.get_or_create(product=p1, block_type="trust", defaults={"title": "تضمین اصالت و سلامت ریهان", "subtitle": "آزمایش‌شده در آزمایشگاه صنایع غذایی", "content": "ساکارز ۱.۴٪، بدون شکر تغذیه‌ای و با ضمانت بازگشت وجه.", "sort_order": 2})

        p2, _ = Product.objects.get_or_create(
            slug="qaenat-super-negin-saffron",
            defaults={
                "category": cat_spices,
                "title": "زعفران سوپر نگین صادراتی قائنات (مثقالی)",
                "sku": "RIHAN-SAFFRON-01",
                "summary": "کلاله‌های ضخیم و یکدست زعفران امسالی با رنگ‌دهی بالای ۲۵۰ و عطر سرمست‌کننده.",
                "price": 650000,
                "compare_at_price": 720000,
                "stock": 40,
                "is_available": True,
                "is_featured": True,
                "meta_title": "خرید زعفران سوپر نگین قائنات اصیل | ریهان",
                "meta_description": "زعفران سوپر نگین قائنات امسالی، قلم‌درشت و بدون خامی."
            }
        )
        ProductImage.objects.get_or_create(product=p2, defaults={"image_url": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=800", "alt_text": "زعفران سوپر نگین قائنات", "is_primary": True})
        ContentBlock.objects.get_or_create(product=p2, block_type="story", defaults={"title": "چرا این زعفران متمایز است؟", "subtitle": "دست‌چین سپیده‌دم از مزارع قائنات", "content": "برداشت قبل از طلوع آفتاب جهت حفظ حداکثری عطر و کروسین.", "sort_order": 1})

        self.stdout.write(self.style.SUCCESS("✓ Seed data loaded successfully."))
