import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/catalog/models.py to add ProductReview model & Product helper methods
models_file = BASE / "src/apps/catalog/models.py"
models_text = models_file.read_text(encoding="utf-8")

review_model_code = """

class ProductReview(models.Model):
    \"\"\"مدل نظرات و امتیازات خریداران معتمد (M8 - D-044 & D-048)\"\"\"
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="محصول")
    author_name = models.CharField(max_length=150, verbose_name="نام خریدار")
    author_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")
    order_number = models.CharField(max_length=50, blank=True, verbose_name="شماره سفارش مرتبط")
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} ستاره") for i in range(1, 6)], default=5, verbose_name="امتیاز (۱ تا ۵)")
    comment = models.TextField(verbose_name="متن نظر و تجربه خرید")
    
    is_approved = models.BooleanField(default=False, verbose_name="تأییدشده جهت نمایش عمومی")
    is_verified_buyer = models.BooleanField(default=False, verbose_name="خریدار تأییدشده")
    
    admin_reply = models.TextField(blank=True, verbose_name="پاسخ رسمی مدیریت ریهان")
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پاسخ ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    class Meta:
        verbose_name = "نظر محصول (M8)"
        verbose_name_plural = "نظرات و امتیازات محصولات"
        ordering = ['-created_at']

    def __str__(self):
        return f"نظر {self.author_name} برای {self.product.title} ({self.rating} ستاره)"
"""

if "class ProductReview" not in models_text:
    models_text += review_model_code
    
    # Add review helper methods to Product model
    helper_code = """
    @property
    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    @property
    def average_rating(self):
        reviews = self.approved_reviews
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 5.0

    @property
    def reviews_count(self):
        return self.approved_reviews.count()
"""
    models_text = models_text.replace(
        "def get_schema_json_ld(self):",
        helper_code + "\n    def get_schema_json_ld(self):"
    )
    models_file.write_text(models_text, encoding="utf-8")
    print("✓ Added ProductReview model to src/apps/catalog/models.py")

# Update src/apps/catalog/admin.py
admin_file = BASE / "src/apps/catalog/admin.py"
admin_text = admin_file.read_text(encoding="utf-8")
if "ProductReview" not in admin_text:
    admin_text = admin_text.replace(
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier",
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview"
    )
    review_admin_code = """

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'author_name', 'rating', 'is_verified_buyer', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'is_verified_buyer', 'rating', 'created_at']
    search_fields = ['author_name', 'comment', 'order_number', 'product__title']
    readonly_fields = ['created_at']
    actions = ['approve_reviews', 'reject_reviews']

    @admin.action(description="تأیید و انتشار عمومی نظرات انتخاب‌شده")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "نظرات انتخاب‌شده با موفقیت تأیید و منتشر شدند.")

    @admin.action(description="عدم تأیید / پنهان‌سازی نظرات")
    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, "نظرات انتخاب‌شده پنهان شدند.")
"""
    admin_text += review_admin_code
    admin_file.write_text(admin_text, encoding="utf-8")
    print("✓ Registered ProductReview in catalog admin.py")

# Update views in apps/catalog to add submit_review_view
views_file = BASE / "src/apps/catalog/views.py"
views_text = views_file.read_text(encoding="utf-8")
review_views_code = """
from .models import ProductReview

@require_POST
def submit_review_view(request, slug):
    \"\"\"ثبت نظر خریدار با تعاملات سریع HTMX (M8)\"\"\"
    product = get_object_or_404(Product, slug=slug, is_available=True)
    author_name = request.POST.get('author_name', '').strip()
    author_phone = request.POST.get('author_phone', '').strip()
    order_number = request.POST.get('order_number', '').strip()
    rating = int(request.POST.get('rating', 5))
    comment = request.POST.get('comment', '').strip()

    if author_name and comment:
        is_verified = False
        if order_number:
            from apps.orders.models import Order
            is_verified = Order.objects.filter(order_number__iexact=order_number).exists()

        ProductReview.objects.create(
            product=product,
            author_name=author_name,
            author_phone=author_phone,
            order_number=order_number,
            rating=min(max(rating, 1), 5),
            comment=comment,
            is_verified_buyer=is_verified,
            is_approved=False # منوط به تایید ادمین
        )
        msg = "دیدگاه ارزشمند شما با احترام ثبت شد و پس از بررسی منتشر خواهد شد."
    else:
        msg = "لطفاً نام و متن دیدگاه را وارد فرمایید."

    if request.headers.get('HX-Request'):
        return render(request, 'catalog/partials/review_feedback.html', {'message': msg})
    
    messages.success(request, msg)
    return redirect('product_detail', slug=slug)
"""
if "def submit_review_view" not in views_text:
    views_text += review_views_code
    views_file.write_text(views_text, encoding="utf-8")
    print("✓ Added submit_review_view to catalog/views.py")

# Update catalog/urls.py
urls_file = BASE / "src/apps/catalog/urls.py"
urls_text = urls_file.read_text(encoding="utf-8")
if "submit_review" not in urls_text:
    urls_text = urls_text.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('products/<slug:slug>/review/', views.submit_review_view, name='submit_review'),"
    )
    urls_file.write_text(urls_text, encoding="utf-8")
    print("✓ Added review route to catalog/urls.py")

# Create feedback partial: src/templates/catalog/partials/review_feedback.html
partial_file = BASE / "src/templates/catalog/partials/review_feedback.html"
partial_file.write_text("""<div class="p-4 bg-green-50 text-green-800 rounded-2xl border border-green-200 text-xs text-center font-bold">
    ✓ {{ message }}
</div>
""", encoding="utf-8")

# Update src/templates/catalog/detail.html to add Customer Reviews Section
detail_template = BASE / "src/templates/catalog/detail.html"
detail_text = detail_template.read_text(encoding="utf-8")
if "نظرات و تجربیات خریداران معتمد" not in detail_text:
    reviews_section_code = """
    <!-- Customer Reviews & Ratings Section (M8 - D-044) -->
    <div class="mt-16 bg-white rounded-3xl border border-gray-100 p-6 sm:p-10 shadow-sm space-y-8">
        <div class="flex flex-wrap justify-between items-center border-b border-gray-100 pb-4 gap-4">
            <div>
                <h2 class="text-xl font-bold text-gray-900">نظرات و تجربیات خریداران معتمد</h2>
                <p class="text-xs text-gray-500 mt-1">دیدگاه‌های ثبت‌شده پس از تحویل کالا</p>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-2xl font-black text-rihan-900 font-mono">{{ product.average_rating }}</span>
                <span class="text-rihan-gold text-lg">★★★★★</span>
                <span class="text-xs text-gray-400">({{ product.reviews_count }} نظر)</span>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Reviews List (2 Cols) -->
            <div class="lg:col-span-2 space-y-4">
                {% for rev in product.approved_reviews %}
                <div class="bg-gray-50 rounded-2xl p-5 border border-gray-100 space-y-2">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center gap-2">
                            <strong class="text-xs text-gray-900">{{ rev.author_name }}</strong>
                            {% if rev.is_verified_buyer %}
                            <span class="text-[10px] text-green-700 bg-green-50 px-2 py-0.5 rounded border border-green-200">✓ خریدار معتمد</span>
                            {% endif %}
                        </div>
                        <span class="text-[11px] text-gray-400">{{ rev.created_at|date:"Y/m/d" }}</span>
                    </div>
                    <p class="text-xs text-gray-700 leading-relaxed">{{ rev.comment }}</p>
                    
                    {% if rev.admin_reply %}
                    <div class="bg-white p-3 rounded-xl border-r-2 border-rihan-gold text-[11px] text-gray-600 mt-2 space-y-1">
                        <strong class="text-rihan-900 block">پاسخ مدیریت ریهان:</strong>
                        <p>{{ rev.admin_reply }}</p>
                    </div>
                    {% endif %}
                </div>
                {% empty %}
                <div class="text-center py-8 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                    <p class="text-xs text-gray-500">هنوز دیدگاهی برای این محصول منتشر نشده است. شما می‌توانید اولین تجربه را ثبت فرمایید.</p>
                </div>
                {% endfor %}
            </div>

            <!-- Submit Review Form (1 Col) -->
            <div class="bg-rihan-50 p-6 rounded-2xl border border-rihan-100 h-fit space-y-4">
                <h3 class="text-xs font-bold text-rihan-900">ثبت تجربه خرید شما</h3>
                
                <div id="review-feedback-box">
                    <form method="post" action="{% url 'submit_review' slug=product.slug %}" hx-post="{% url 'submit_review' slug=product.slug %}" hx-target="#review-feedback-box" class="space-y-3">
                        {% csrf_token %}
                        <div>
                            <label class="block text-[11px] font-semibold text-gray-700 mb-1">نام شما *</label>
                            <input type="text" name="author_name" required class="w-full bg-white border border-gray-200 rounded-xl p-2 text-xs focus:outline-none focus:border-rihan-gold" placeholder="مثال: مریم کارمند">
                        </div>
                        <div>
                            <label class="block text-[11px] font-semibold text-gray-700 mb-1">شماره سفارش (جهت دریافت نشان خریدار معتمد)</label>
                            <input type="text" name="order_number" class="w-full bg-white border border-gray-200 rounded-xl p-2 text-xs font-mono focus:outline-none focus:border-rihan-gold" placeholder="RH-1405-...">
                        </div>
                        <div>
                            <label class="block text-[11px] font-semibold text-gray-700 mb-1">امتیاز شما به کیفیت محصول</label>
                            <select name="rating" class="w-full bg-white border border-gray-200 rounded-xl p-2 text-xs focus:outline-none focus:border-rihan-gold">
                                <option value="5">۵ ستاره — عالی و اصیل</option>
                                <option value="4">۴ ستاره — بسیار خوب</option>
                                <option value="3">۳ ستاره — متوسط</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-[11px] font-semibold text-gray-700 mb-1">متن دیدگاه شما *</label>
                            <textarea name="comment" rows="3" required class="w-full bg-white border border-gray-200 rounded-xl p-2 text-xs focus:outline-none focus:border-rihan-gold" placeholder="کیفیت، عطر، بسته‌بندی..."></textarea>
                        </div>
                        <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-sm">
                            ارسال دیدگاه ↗
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
"""
    detail_text = detail_text.replace("{% endblock %}", reviews_section_code + "\n{% endblock %}")
    detail_template.write_text(detail_text, encoding="utf-8")
    print("✓ Added Reviews Section to src/templates/catalog/detail.html")

# Create Unit Tests: tests/test_reviews.py
test_file = BASE / "tests/test_reviews.py"
test_code = """from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, ProductReview
from apps.orders.models import Order

class ProductReviewsTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="چاشنی", slug="spices-r")
        self.p = Product.objects.create(
            category=self.cat, title="زعفران قائنات", slug="zaferan-qaenat",
            sku="RIHAN-ZAF-01", summary="زعفران نگین", price=650000, stock=20
        )
        self.order = Order.objects.create(
            customer_name="مریم کارمند", customer_phone="09121112233",
            shipping_address="تبریز", postal_code="5123456789",
            items_total=650000, grand_total=650000, status='delivered'
        )

    def test_review_submission_and_moderation(self):
        c = Client()
        # 1. Submit review
        res = c.post(reverse('submit_review', kwargs={'slug': self.p.slug}), {
            'author_name': 'مریم کارمند',
            'order_number': self.order.order_number,
            'rating': 5,
            'comment': 'عطر و رنگدهی فوق‌العاده بود.'
        })
        self.assertEqual(res.status_code, 302)

        # 2. Check in DB (is_approved=False by default)
        review = ProductReview.objects.filter(product=self.p).first()
        self.assertIsNotNone(review)
        self.assertFalse(review.is_approved)
        self.assertTrue(review.is_verified_buyer)

        # 3. Unapproved review does not appear on detail page
        res_detail = c.get(reverse('product_detail', kwargs={'slug': self.p.slug}))
        self.assertNotContains(res_detail, "عطر و رنگدهی فوق‌العاده بود")

        # 4. Admin approves review
        review.is_approved = True
        review.admin_reply = "از رضایت شما خرسندیم."
        review.save()

        # 5. Approved review appears with admin reply
        res_detail_approved = c.get(reverse('product_detail', kwargs={'slug': self.p.slug}))
        self.assertContains(res_detail_approved, "عطر و رنگدهی فوق‌العاده بود")
        self.assertContains(res_detail_approved, "از رضایت شما خرسندیم")
        self.assertEqual(self.p.average_rating, 5.0)
        self.assertEqual(self.p.reviews_count, 1)
"""
test_file.write_text(test_code, encoding="utf-8")
print("✓ Created tests/test_reviews.py")

# Register M8 in PluginRegistry
plugins_file = BASE / "src/apps/core/plugins.py"
plugins_text = plugins_file.read_text(encoding="utf-8")
if 'PluginRegistry.register("M8"' not in plugins_text:
    plugins_text += '\nPluginRegistry.register("M8", "نظرات و بازخورد خریداران معتمد D-044", "0.5.10", is_system=True)\n'
    plugins_file.write_text(plugins_text, encoding="utf-8")
    print("✓ Registered M8 in PluginRegistry")

print("Module M8 (Customer Reviews) Deployed Successfully.")
