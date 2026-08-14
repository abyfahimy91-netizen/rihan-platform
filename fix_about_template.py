from pathlib import Path

BASE = Path("/root/rihan-platform")

# Ensure directory exists
about_template_file = BASE / "src/templates/core/about.html"
about_template_file.parent.mkdir(parents=True, exist_ok=True)

about_content = """{% extends 'base.html' %}
{% block title %}داستان اصالت و فلسفه گزینش | ریهان{% endblock %}
{% block meta_description %}روایت برند ریهان؛ گزینش‌گری امین از دل طبیعت هوراند و آذربایجان با منشور ۵ ستون انتخاب کالا و احترام به کرامت مشتری.{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-20">

    <!-- Hero Section -->
    <div class="text-center space-y-4 max-w-3xl mx-auto">
        <span class="text-xs font-bold text-rihan-gold uppercase tracking-widest bg-rihan-100 px-3.5 py-1.5 rounded-full">داستان برند ریهان</span>
        <h1 class="text-3xl sm:text-5xl font-black text-rihan-900 leading-tight">
            ریهان یک فروشگاه نیست؛<br><span class="text-rihan-gold">ریهان یک گزینش‌گر امین است.</span>
        </h1>
        <p class="text-sm sm:text-base text-gray-600 leading-relaxed pt-2">
            «محصول ممکن است تغییر کند، اما اعتماد همواره ثابت و پایدار می‌ماند.»
        </p>
    </div>

    <!-- Central Story Box -->
    <div class="bg-white rounded-3xl border border-gray-100 p-8 sm:p-14 shadow-sm space-y-6">
        <h2 class="text-2xl font-black text-gray-900 border-b border-gray-100 pb-4">از کجا آمده‌ایم؟</h2>
        
        <div class="text-sm text-gray-700 leading-loose space-y-4">
            <p>
                ریشه ریهان در دل کوهستان‌ها، مراتع بکر و باغ‌های آفتاب‌خورده <strong>هوراند و خطه آذربایجان</strong> جوانه زده است. سال‌ها بود که دوستان، همکاران و نزدیکان، خرید سماق اصیل کوهی، عسل خام مراتع سبلان، گردوی کاغذی یا چای ناب لاهیجان را به سلیقه و وسواس خانواده ریهان می‌سپردند؛ چرا که می‌دانستند آنچه برای خانه خودمان برمی‌گزینیم، از سخت‌گیرانه‌ترین فیلترهای کیفیت و سلامت عبور کرده است.
            </p>
            <p>
                پلتفرم ریهان برای کانالیزه کردن همین اعتماد دیرینه شکل گرفت؛ تا بتوانیم بدون هیاهوهای بازاری و تبلیغات فریبنده، دست‌چینی از اصیل‌ترین کالاهای سرزمینمان را با حفظ شأن، وقار و کرامت در اختیار خانواده‌های فهیم ایرانی قرار دهیم.
            </p>
        </div>
    </div>

    <!-- 5 Pillars of Selection (D-057) -->
    <div class="space-y-8">
        <div class="text-center">
            <h2 class="text-2xl font-black text-gray-900">۵ ستون گزینش کالا در ریهان</h2>
            <p class="text-xs text-gray-500 mt-1">معیارهای سخت‌گیرانه ما برای ورود یک محصول به کاتالوگ</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Pillar 1 -->
            <div class="bg-white rounded-3xl border border-gray-100 p-7 shadow-sm space-y-3">
                <span class="text-3xl block">🌿</span>
                <h3 class="text-base font-bold text-gray-900">۱. اصالت و مبدأ روشن</h3>
                <p class="text-xs text-gray-600 leading-relaxed">
                    هر محصول باید خاستگاه معین، قابل ردیابی و تولیدکننده شناخته‌شده داشته باشد. ادعاهای غلوآمیز یا محصولات بی‌هویت در ریهان جایی ندارند.
                </p>
            </div>

            <!-- Pillar 2 -->
            <div class="bg-white rounded-3xl border border-gray-100 p-7 shadow-sm space-y-3">
                <span class="text-3xl block">🔬</span>
                <h3 class="text-base font-bold text-gray-900">۲. آزمون کیفیت و آزمایشگاه</h3>
                <p class="text-xs text-gray-600 leading-relaxed">
                    تمامی اقلام پیش از عرضه، توسط تیم ریهان تست حضوری شده و در صورت لزوم (مانند عسل سبلان) برگه آزمایش معتبر صنایع غذایی دریافت می‌کنند.
                </p>
            </div>

            <!-- Pillar 3 -->
            <div class="bg-white rounded-3xl border border-gray-100 p-7 shadow-sm space-y-3">
                <span class="text-3xl block">💎</span>
                <h3 class="text-base font-bold text-gray-900">۳. قیمت تمام‌شده و شفاف</h3>
                <p class="text-xs text-gray-600 leading-relaxed">
                    منطبق بر مصوبه D-046، قیمت کالا شامل هزینه بسته‌بندی فاخر و ارسال است. در مرحله تسویه‌حساب، مشتری با هیچ هزینه پنهان یا غافلگیری روبرو نمی‌شود.
                </p>
            </div>

            <!-- Pillar 4 -->
            <div class="bg-white rounded-3xl border border-gray-100 p-7 shadow-sm space-y-3 md:col-span-1 md:col-start-1">
                <span class="text-3xl block">🤝</span>
                <h3 class="text-base font-bold text-gray-900">۴. کرامت و آرامش خریدار</h3>
                <p class="text-xs text-gray-600 leading-relaxed">
                    ما از تایمرهای استرس‌زای دروغین، پاپ‌آپ‌های آزاردهنده و پیامک‌های تبلیغاتی مکرر متنفریم. تصمیم‌گیری خرید با طمأنینه انجام می‌شود.
                </p>
            </div>

            <!-- Pillar 5 -->
            <div class="bg-white rounded-3xl border border-gray-100 p-7 shadow-sm space-y-3 md:col-span-2">
                <span class="text-3xl block">📦</span>
                <h3 class="text-base font-bold text-gray-900">۵. تضمین بازگشت و پاسخگویی مستقیم</h3>
                <p class="text-xs text-gray-600 leading-relaxed">
                    در صورت هرگونه عدم انطباق با برگه آزمایش یا نارضایتی از کیفیت، وجه سفارش با کمال احترام و بدون قیدوشرط مسترد خواهد شد.
                </p>
            </div>
        </div>
    </div>

    <!-- CTA Section -->
    <div class="bg-rihan-900 text-white rounded-3xl p-10 sm:p-14 text-center space-y-6 shadow-xl">
        <h2 class="text-2xl sm:text-3xl font-black">طعم اصالت را در کاتالوگ ریهان تجربه کنید</h2>
        <p class="text-xs sm:text-sm text-gray-300 max-w-xl mx-auto leading-relaxed">
            محصولات ما به صورت محدود و دست‌چین عرضه می‌شوند تا کیفیت فدای کمیت نگردد.
        </p>
        <div>
            <a href="{% url 'product_list' %}" class="inline-block bg-rihan-gold hover:bg-yellow-600 text-rihan-900 font-extrabold text-xs sm:text-sm px-8 py-3.5 rounded-2xl transition shadow-md">
                مشاهده کاتالوگ کالاهای اصیل →
            </a>
        </div>
    </div>

</div>
{% endblock %}
"""
about_template_file.write_text(about_content, encoding="utf-8")
print("✓ Created src/templates/core/about.html")

# Create test_about_page.py
test_file = BASE / "tests/test_about_page.py"
test_content = """from django.test import TestCase, Client
from django.urls import reverse

class AboutPageTestCase(TestCase):
    def test_about_page_rendering_and_pillars(self):
        c = Client()
        res = c.get(reverse('about'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "ریهان یک گزینش‌گر امین است")
        self.assertContains(res, "۵ ستون گزینش کالا")
        self.assertContains(res, "اصالت و مبدأ روشن")
        self.assertContains(res, "آزمون کیفیت و آزمایشگاه")
        self.assertContains(res, "کرامت و آرامش خریدار")
        # Verify Independent Brand Rule
        self.assertNotContains(res, "عبدالحسین فهیمی")
"""
test_file.write_text(test_content, encoding="utf-8")
print("✓ Created tests/test_about_page.py")
