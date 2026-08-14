import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

templates = {
    BASE / "src/templates/base.html": """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}ریهان | فروشگاه آنلاین اعتمادمحور{% endblock %}</title>
    <meta name="description" content="{% block meta_description %}پلتفرم خرید اعتمادمحور ریهان با گزینش اصیل‌ترین کالاها{% endblock %}">
    {% block extra_head %}{% endblock %}
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        rihan: {
                            50: '#fbf9f6',
                            100: '#f5f0e8',
                            600: '#7c5e38',
                            800: '#43311b',
                            900: '#23180c',
                            gold: '#c5a059',
                        }
                    },
                    fontFamily: {
                        sans: ['Vazirmatn', 'Tahoma', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script defer src="https://unpkg.com/alpinejs@3.14.0/dist/cdn.min.js"></script>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
        body { font-family: 'Vazirmatn', sans-serif; }
    </style>
</head>
<body class="bg-rihan-50 text-gray-800 antialiased min-h-screen flex flex-col justify-between">
    <header class="bg-white border-b border-rihan-100 sticky top-0 z-50 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-20">
                <div class="flex items-center space-x-6 space-x-reverse">
                    <a href="/products/" class="flex items-center gap-3">
                        <span class="text-2xl font-bold tracking-wider text-rihan-900">RIHAN <span class="text-rihan-gold text-lg">ریهان</span></span>
                    </a>
                    <nav class="hidden md:flex space-x-6 space-x-reverse text-sm font-medium text-gray-600">
                        <a href="/products/" class="hover:text-rihan-600 transition">کاتالوگ محصولات</a>
                        <a href="/api/health/" class="text-xs text-green-600 bg-green-50 px-2.5 py-1 rounded-full border border-green-200">سیستم فعال (v0.5)</a>
                    </nav>
                </div>
                <div class="flex items-center gap-4">
                    <a href="/products/" class="text-sm font-medium text-rihan-800 hover:text-rihan-gold transition">کاتالوگ و خرید</a>
                    <a href="/admin/" class="text-xs text-gray-500 hover:text-gray-900 border border-gray-200 px-3 py-1.5 rounded-lg transition">پنل مدیریت</a>
                </div>
            </div>
        </div>
    </header>
    <main class="flex-grow">
        {% block content %}{% endblock %}
    </main>
    <footer class="bg-rihan-900 text-rihan-100 py-12 border-t border-rihan-800 mt-16">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-gray-400">
            © ۱۴۰۵ تمامی حقوق برای برند مستقل ریهان محفوظ است. توسعه‌یافته بر پایه استانداردهای هوشمند AI-VOS.
        </div>
    </footer>
</body>
</html>
""",

    BASE / "src/templates/catalog/partials/product_grid.html": """<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for product in products %}
    <div class="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between">
        <div>
            <div class="relative bg-gray-50 h-56 flex items-center justify-center overflow-hidden">
                {% if product.primary_image %}
                <img src="{{ product.primary_image.image_url }}" alt="{{ product.title }}" class="object-cover w-full h-full">
                {% else %}
                <div class="text-gray-300 text-5xl">🛍️</div>
                {% endif %}
                {% if product.has_discount %}
                <span class="absolute top-3 right-3 bg-red-600 text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-sm">
                    {{ product.discount_percent }}% تخفیف
                </span>
                {% endif %}
            </div>
            <div class="p-5">
                <span class="text-xs text-rihan-gold font-semibold">{{ product.category.name }}</span>
                <h3 class="text-base font-bold text-gray-900 mt-1">
                    <a href="{% url 'product_detail' slug=product.slug %}">{{ product.title }}</a>
                </h3>
                <p class="text-gray-500 text-xs mt-2 line-clamp-2 leading-relaxed">{{ product.summary }}</p>
            </div>
        </div>
        <div class="p-5 pt-0 border-t border-gray-50 mt-4 flex items-center justify-between">
            <div>
                {% if product.has_discount %}
                <span class="text-xs text-gray-400 line-through block">{{ product.compare_at_price|floatformat:"0" }} تومان</span>
                {% endif %}
                <span class="text-base font-extrabold text-gray-900">{{ product.price|floatformat:"0" }} <span class="text-xs font-normal text-gray-500">تومان</span></span>
            </div>
            <a href="{% url 'product_detail' slug=product.slug %}" class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow-sm">
                مشاهده و انتخاب
            </a>
        </div>
    </div>
    {% empty %}
    <div class="col-span-full text-center py-12 bg-white rounded-2xl border border-dashed border-gray-200">
        <p class="text-gray-500 text-sm">هیچ محصولی یافت نشد.</p>
    </div>
    {% endfor %}
</div>
""",

    BASE / "src/templates/catalog/list.html": """{% extends 'base.html' %}
{% block title %}کاتالوگ محصولات گزینش‌شده | ریهان{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <div class="mb-8 text-center sm:text-right">
        <h1 class="text-3xl font-extrabold text-rihan-900">کاتالوگ محصولات ریهان</h1>
        <p class="text-gray-500 text-sm mt-2">مجموعه‌ای برگزیده از کالاهای اصیل با ضمانت کیفیت و رضایت</p>
    </div>
    <div class="flex flex-wrap gap-2 mb-8 pb-4 border-b border-gray-200" hx-target="#product-grid-container" hx-push-url="true">
        <a href="{% url 'product_list' %}" hx-get="{% url 'product_list' %}" class="px-4 py-2 rounded-xl text-xs font-semibold transition {% if not selected_category %}bg-rihan-900 text-white shadow-sm{% else %}bg-white text-gray-600 hover:bg-gray-100 border border-gray-200{% endif %}">
            همه دسته‌ها
        </a>
        {% for cat in categories %}
        <a href="{% url 'product_list' %}?category={{ cat.slug }}" hx-get="{% url 'product_list' %}?category={{ cat.slug }}" class="px-4 py-2 rounded-xl text-xs font-semibold transition {% if selected_category == cat.slug %}bg-rihan-900 text-white shadow-sm{% else %}bg-white text-gray-600 hover:bg-gray-100 border border-gray-200{% endif %}">
            {{ cat.icon }} {{ cat.name }}
        </a>
        {% endfor %}
    </div>
    <div id="product-grid-container">
        {% include 'catalog/partials/product_grid.html' %}
    </div>
</div>
{% endblock %}
""",

    BASE / "src/templates/catalog/detail.html": """{% extends 'base.html' %}
{% block title %}{{ product.meta_title|default:product.title }} | ریهان{% endblock %}
{% block meta_description %}{{ product.meta_description|default:product.summary }}{% endblock %}
{% block extra_head %}
<script type="application/ld+json">
{{ product.get_schema_json_ld|safe }}
</script>
<meta property="og:title" content="{{ product.title }}">
<meta property="og:description" content="{{ product.summary }}">
<meta property="og:type" content="product">
{% if product.primary_image %}
<meta property="og:image" content="{{ product.primary_image.image_url }}">
{% endif %}
{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <nav class="text-xs text-gray-500 mb-6 flex items-center gap-2">
        <a href="/products/" class="hover:text-gray-900">خانه</a>
        <span>/</span>
        <a href="{% url 'product_list' %}" class="hover:text-gray-900">کاتالوگ</a>
        <span>/</span>
        <a href="{% url 'product_list' %}?category={{ product.category.slug }}" class="hover:text-gray-900">{{ product.category.name }}</a>
        <span>/</span>
        <span class="text-gray-800 font-semibold">{{ product.title }}</span>
    </nav>
    <div class="bg-white rounded-3xl border border-gray-100 p-6 sm:p-10 shadow-sm grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div class="flex flex-col items-center">
            <div class="w-full h-80 sm:h-96 bg-gray-50 rounded-2xl overflow-hidden flex items-center justify-center border border-gray-100">
                {% if product.primary_image %}
                <img src="{{ product.primary_image.image_url }}" alt="{{ product.title }}" class="object-cover w-full h-full">
                {% else %}
                <span class="text-6xl text-gray-300">🎁</span>
                {% endif %}
            </div>
            {% if product.images.count > 1 %}
            <div class="flex gap-3 mt-4 overflow-x-auto w-full pb-2">
                {% for img in product.images.all %}
                <img src="{{ img.image_url }}" class="w-16 h-16 object-cover rounded-xl border border-gray-200">
                {% endfor %}
            </div>
            {% endif %}
        </div>
        <div class="flex flex-col justify-between">
            <div>
                <span class="bg-rihan-100 text-rihan-800 text-xs font-semibold px-3 py-1 rounded-full">{{ product.category.name }}</span>
                <h1 class="text-2xl sm:text-3xl font-extrabold text-gray-900 mt-3">{{ product.title }}</h1>
                <span class="text-xs text-gray-400 block mt-1">کد کالا: {{ product.sku }}</span>
                <p class="text-gray-600 text-sm mt-5 leading-relaxed bg-gray-50 p-4 rounded-2xl border border-gray-100">
                    {{ product.summary }}
                </p>
                <div class="mt-6 p-5 bg-rihan-50 rounded-2xl border border-rihan-100">
                    <div class="flex items-baseline gap-3">
                        {% if product.has_discount %}
                        <span class="text-sm text-gray-400 line-through">{{ product.compare_at_price|floatformat:"0" }} تومان</span>
                        <span class="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-md">{{ product.discount_percent }}% تخفیف</span>
                        {% endif %}
                    </div>
                    <div class="text-2xl font-black text-rihan-900 mt-1">
                        {{ product.price|floatformat:"0" }} <span class="text-sm font-medium text-gray-600">تومان</span>
                    </div>
                    <span class="text-xs text-green-700 font-medium block mt-2">✓ موجود در انبار ریهان و آماده ارسال</span>
                </div>
            </div>
            <div class="mt-8 pt-6 border-t border-gray-100">
                <button class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-4 rounded-2xl shadow-lg transition flex items-center justify-center gap-3">
                    <span>🛒 افزودن به سبد خرید</span>
                    <span class="text-xs font-normal opacity-80">(ارسال سریع با بسته‌بندی ویژه)</span>
                </button>
            </div>
        </div>
    </div>
    {% if content_blocks %}
    <div class="mt-12 space-y-8">
        <h2 class="text-xl font-bold text-gray-900">روایت و جزئیات تخصصی محصول</h2>
        {% for block in content_blocks %}
        <div class="bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
            <span class="text-xs font-bold text-rihan-gold uppercase tracking-wider">{{ block.get_block_type_display }}</span>
            <h3 class="text-lg font-bold text-gray-900 mt-1">{{ block.title }}</h3>
            {% if block.subtitle %}
            <p class="text-xs text-gray-500 mt-0.5">{{ block.subtitle }}</p>
            {% endif %}
            <div class="mt-4 text-sm text-gray-700 leading-relaxed">
                {{ block.content|linebreaks }}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>
{% endblock %}
"""
}

for path, content in templates.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Generated Template: {path.name}")
