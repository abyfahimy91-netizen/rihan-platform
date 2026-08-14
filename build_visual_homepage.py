from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/core/views.py to render home.html with live products and categories
views_file = BASE / "src/apps/core/views.py"
views_content = """from django.shortcuts import render
from django.http import JsonResponse
from apps.catalog.models import Category, Product, ProductReview

def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "platform": "RIHAN Platform",
        "version": "0.6.0-mvp",
        "phase": 5,
        "active_modules": 14,
        "os_framework": "AI-VOS v1.1.1"
    })

def home_view(request):
    \"\"\"صفحه اصلی و لندینگ‌پیج فاخر ریهان (M13 - Home Landing Page)\"\"\"
    categories = Category.objects.filter(is_active=True)
    featured_products = Product.objects.filter(is_featured=True, is_available=True)[:6]
    recent_reviews = ProductReview.objects.filter(is_approved=True)[:3]

    context = {
        'categories': categories,
        'featured_products': featured_products,
        'recent_reviews': recent_reviews
    }
    return render(request, 'core/home.html', context)

def about_view(request):
    \"\"\"صفحه اصالت، فلسفه گزینش و داستان برند ریهان (M12 - CENTRAL-STORY.md)\"\"\"
    return render(request, 'core/about.html')
"""
views_file.write_text(views_content, encoding="utf-8")

# Create src/templates/core/home.html
home_template_file = BASE / "src/templates/core/home.html"
home_template_content = """{% extends 'base.html' %}
{% block title %}ریهان | فروشگاه آنلاین گزینش کالاهای اصیل و اعتمادمحور{% endblock %}

{% block content %}
<div class="space-y-24 py-12">

    <!-- Hero Section -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="bg-white rounded-3xl border border-gray-100 p-8 sm:p-16 shadow-sm text-center space-y-6 relative overflow-hidden">
            <span class="text-xs font-bold text-rihan-gold uppercase tracking-widest bg-rihan-100 px-4 py-1.5 rounded-full inline-block">
                پلتفرم گزینش کالاهای اصیل
            </span>
            <h1 class="text-3xl sm:text-5xl lg:text-6xl font-black text-rihan-900 leading-tight">
                ریهان؛ گزینش‌گری امین<br>
                <span class="text-rihan-gold">از دل طبیعت بکر هوراند و آذربایجان</span>
            </h1>
            <p class="text-sm sm:text-base text-gray-600 max-w-2xl mx-auto leading-relaxed">
                ما فروشگاه انبوه نیستیم؛ ما انتخاب‌های ناب خانوادگی‌مان را که از سخت‌گیرانه‌ترین فیلترهای اصالت و کیفیت عبور کرده‌اند، با کمال احترام با شما به اشتراک می‌گذاریم.
            </p>
            <div class="pt-4 flex flex-wrap justify-center gap-4">
                <a href="{% url 'product_list' %}" class="bg-rihan-900 hover:bg-rihan-800 text-white font-extrabold text-xs sm:text-sm px-8 py-4 rounded-2xl shadow-lg transition flex items-center gap-2">
                    <span>مشاهده کاتالوگ محصولات</span>
                    <span>←</span>
                </a>
                <a href="{% url 'about' %}" class="bg-rihan-50 hover:bg-rihan-100 text-rihan-900 font-bold text-xs sm:text-sm px-8 py-4 rounded-2xl border border-rihan-200 transition">
                    روایت اصالت و داستان ما
                </a>
            </div>
        </div>
    </div>

    <!-- 4 Trust Pillars (D-046 & Principle 11) -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-2 text-center sm:text-right">
                <span class="text-3xl block mb-2">💎</span>
                <h3 class="text-sm font-bold text-gray-900">قیمت تمام‌شده و شفاف</h3>
                <p class="text-xs text-gray-500 leading-relaxed">هزینه ارسال و بسته‌بندی ویژه در قیمت کالا لحاظ شده و هیچ هزینه پنهانی وجود ندارد.</p>
            </div>
            <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-2 text-center sm:text-right">
                <span class="text-3xl block mb-2">🔬</span>
                <h3 class="text-sm font-bold text-gray-900">آزمون کیفیت و اصالت</h3>
                <p class="text-xs text-gray-500 leading-relaxed">تست حضوری و برگه‌های آزمایش معتبر برای محصولات طبیعی (مانند ساکارز عسل سبلان).</p>
            </div>
            <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-2 text-center sm:text-right">
                <span class="text-3xl block mb-2">🤝</span>
                <h3 class="text-sm font-bold text-gray-900">حفظ شأن و کرامت خریدار</h3>
                <p class="text-xs text-gray-500 leading-relaxed">بدون تایمرهای فیک، بدون تبلیغات پیامکی مزاحم و با احترام کامل به آرامش خریدار.</p>
            </div>
            <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-2 text-center sm:text-right">
                <span class="text-3xl block mb-2">📦</span>
                <h3 class="text-sm font-bold text-gray-900">ضمانت بازگشت بی‌قیدوشرط</h3>
                <p class="text-xs text-gray-500 leading-relaxed">در صورت هرگونه نارضایتی از کیفیت یا عطر کالا، وجه سفارش با احترام کامل مسترد می‌گردد.</p>
            </div>
        </div>
    </div>

    <!-- Featured Products Carousel / Grid -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div class="flex justify-between items-end border-b border-gray-200 pb-4">
            <div>
                <span class="text-xs font-bold text-rihan-gold uppercase tracking-wider">دست‌چین ویژه</span>
                <h2 class="text-2xl font-black text-rihan-900 mt-1">محصولات منتخب ریهان</h2>
            </div>
            <a href="{% url 'product_list' %}" class="text-xs font-bold text-rihan-800 hover:text-rihan-gold transition">
                مشاهده همه محصولات کاتالوگ ←
            </a>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {% for product in featured_products %}
            <div class="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between group">
                <div>
                    <div class="relative bg-gray-50 h-64 flex items-center justify-center overflow-hidden">
                        {% if product.primary_image %}
                        <img src="{{ product.primary_image.image_url }}" alt="{{ product.title }}" class="object-cover w-full h-full group-hover:scale-105 transition duration-300">
                        {% else %}
                        <span class="text-5xl text-gray-300">🎁</span>
                        {% endif %}
                        
                        {% if product.has_discount %}
                        <span class="absolute top-4 right-4 bg-red-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-sm">
                            {{ product.discount_percent }}% تخفیف
                        </span>
                        {% endif %}
                    </div>
                    <div class="p-6">
                        <span class="text-xs text-rihan-gold font-bold uppercase tracking-wider">{{ product.category.name }}</span>
                        <h3 class="text-base font-bold text-gray-900 mt-1.5 line-clamp-1 hover:text-rihan-600 transition">
                            <a href="{% url 'product_detail' slug=product.slug %}">{{ product.title }}</a>
                        </h3>
                        <p class="text-gray-500 text-xs mt-2.5 line-clamp-2 leading-relaxed">{{ product.summary }}</p>
                    </div>
                </div>

                <div class="p-6 pt-0 border-t border-gray-50 mt-4 flex items-center justify-between">
                    <div>
                        {% if product.has_discount %}
                        <span class="text-xs text-gray-400 line-through block">{{ product.compare_at_price|floatformat:"0" }} تومان</span>
                        {% endif %}
                        <span class="text-lg font-black text-gray-900">{{ product.price|floatformat:"0" }} <span class="text-xs font-normal text-gray-500">تومان</span></span>
                    </div>
                    <a href="{% url 'product_detail' slug=product.slug %}" class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition shadow-sm">
                        مشاهده و انتخاب
                    </a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Central Story Teaser Box -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="bg-rihan-900 text-white rounded-3xl p-8 sm:p-14 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center shadow-xl">
            <div class="space-y-4">
                <span class="text-xs font-bold text-rihan-gold uppercase tracking-widest bg-rihan-800 px-3.5 py-1 rounded-full inline-block">خاستگاه و اصالت</span>
                <h2 class="text-2xl sm:text-3xl font-black leading-tight">چرا ریهان به وجود آمد؟</h2>
                <p class="text-xs sm:text-sm text-gray-300 leading-loose">
                    سال‌ها بود که دوستان و همکاران می‌گفتند: «سماق هوراند رفتی برای ما هم بیار»، «عسل طبیعی خوب سراغ داری؟». ما می‌خریدیم، می‌آوردیم و به همان قیمت می‌دادیم؛ چون از تعارف و رویکردهای بازاری خجالت می‌کشیدیم. ریهان ساخته شد تا همان خرید امین، اصیل و باوسواس را با حفظ شأن و احترام به دست همه خانواده‌ها برساند.
                </p>
                <div class="pt-2">
                    <a href="{% url 'about' %}" class="inline-block bg-rihan-gold hover:bg-yellow-600 text-rihan-900 font-extrabold text-xs px-6 py-3 rounded-xl transition shadow-md">
                        مطالعه متن کامل داستان ریهان →
                    </a>
                </div>
            </div>

            <div class="bg-rihan-800 p-8 rounded-2xl border border-rihan-700 space-y-4 text-xs text-gray-200">
                <h3 class="text-sm font-bold text-white border-b border-rihan-700 pb-2">منشور اعتماد ثابت ریهان:</h3>
                <ul class="space-y-2.5 leading-relaxed">
                    <li>✓ محصول متغیر است، اما اعتماد همواره ثابت می‌ماند.</li>
                    <li>✓ سود واقعی ما در رضایت عمیق و همیشگی شماست.</li>
                    <li>✓ هیچ کالایی بدون آزمایش و بررسی حضوری عرضه نمی‌شود.</li>
                    <li>✓ قیمت نهایی شفاف است؛ هیچ هزینه‌ای در لحظه پرداخت اضافه نمی‌شود.</li>
                </ul>
            </div>
        </div>
    </div>

</div>
{% endblock %}
"""
home_template_file.write_text(home_template_content, encoding="utf-8")
print("✓ Created visual landing page in src/templates/core/home.html")
