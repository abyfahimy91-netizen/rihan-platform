import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/catalog/models.py to add LeadCapture model
models_file = BASE / "src/apps/catalog/models.py"
models_text = models_file.read_text(encoding="utf-8")

lead_model_code = """

class LeadCapture(models.Model):
    \"\"\"مدل ثبت سرنخ و درخواست کالای ناموجود یا اختصاصی (M9 - Flow C3 & MVP-SCOPE)\"\"\"
    STATUS_CHOICES = [
        ('new', 'درخواست جدید'),
        ('in_progress', 'در حال پیگیری و گزینش تأمین‌کننده'),
        ('supplied', 'تأمین‌شده و اطلاع‌رسانی‌شده'),
        ('rejected', 'عدم امکان تأمین / بسته شده'),
    ]

    full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی")
    phone = models.CharField(max_length=20, verbose_name="شماره موبایل")
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads', verbose_name="محصول ناموجود کاتالوگ")
    requested_product_name = models.CharField(max_length=200, blank=True, verbose_name="عنوان کالای درخواستی")
    notes = models.TextField(blank=True, verbose_name="توضیحات و ویژگی‌های خاص")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new', verbose_name="وضعیت پیگیری")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت و اقدامات ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    class Meta:
        verbose_name = "سرنخ / درخواست محصول (M9)"
        verbose_name_plural = "سرنخ‌ها و درخواست‌های محصولات"
        ordering = ['-created_at']

    def __str__(self):
        prod = self.product.title if self.product else (self.requested_product_name or "کالای درخواستی")
        return f"درخواست {prod} از {self.phone} ({self.get_status_display()})"
"""

if "class LeadCapture" not in models_text:
    models_text += lead_model_code
    models_file.write_text(models_text, encoding="utf-8")
    print("✓ Added LeadCapture model to src/apps/catalog/models.py")

# Update src/apps/catalog/admin.py
admin_file = BASE / "src/apps/catalog/admin.py"
admin_text = admin_file.read_text(encoding="utf-8")
if "LeadCapture" not in admin_text:
    admin_text = admin_text.replace(
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview",
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview, LeadCapture"
    )
    lead_admin_code = """

@admin.register(LeadCapture)
class LeadCaptureAdmin(admin.ModelAdmin):
    list_display = ['phone', 'requested_item_display', 'full_name', 'status_badge', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['phone', 'full_name', 'requested_product_name', 'product__title']
    readonly_fields = ['created_at']
    actions = ['mark_in_progress', 'mark_supplied', 'mark_rejected']

    @admin.display(description="کالای درخواستی")
    def requested_item_display(self, obj):
        if obj.product:
            return f"کالای ناموجود: {obj.product.title}"
        return obj.requested_product_name or "کالای سفارشی"

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            'new': '#0d6efd',
            'in_progress': '#ffc107',
            'supplied': '#198754',
            'rejected': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )

    @admin.action(description="تغییر وضعیت به: در حال پیگیری تأمین")
    def mark_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, "سرنخ‌های انتخاب‌شده در حال پیگیری قرار گرفتند.")

    @admin.action(description="تغییر وضعیت به: تأمین شد و اطلاع‌رسانی گردید")
    def mark_supplied(self, request, queryset):
        queryset.update(status='supplied')
        self.message_user(request, "سرنخ‌های انتخاب‌شده به عنوان تأمین‌شده علامت‌گذاری شدند.")
"""
    admin_text += lead_admin_code
    admin_file.write_text(admin_text, encoding="utf-8")
    print("✓ Registered LeadCapture in catalog admin.py")

# Update views in apps/catalog to add submit_lead_view
views_file = BASE / "src/apps/catalog/views.py"
views_text = views_file.read_text(encoding="utf-8")
lead_views_code = """
from .models import LeadCapture

@require_POST
def submit_lead_view(request):
    \"\"\"ثبت درخواست کالای ناموجود یا سرنخ اختصاصی (M9 - Flow C3)\"\"\"
    phone = request.POST.get('phone', '').strip()
    full_name = request.POST.get('full_name', '').strip()
    product_id = request.POST.get('product_id')
    requested_name = request.POST.get('requested_product_name', '').strip()
    notes = request.POST.get('notes', '').strip()

    if phone and len(phone) >= 10:
        product = None
        if product_id:
            product = Product.objects.filter(id=product_id).first()

        LeadCapture.objects.create(
            phone=phone,
            full_name=full_name,
            product=product,
            requested_product_name=requested_name,
            notes=notes,
            status='new'
        )
        msg = "درخواست شما با احترام ثبت شد. به محض تأمین و موجود شدن، از طریق پیامک به شما اطلاع‌رسانی خواهد شد."
    else:
        msg = "لطفاً شماره تلفن همراه معتبر را وارد فرمایید."

    if request.headers.get('HX-Request'):
        return render(request, 'catalog/partials/lead_feedback.html', {'message': msg})
    
    messages.success(request, msg)
    return redirect('product_list')
"""
if "def submit_lead_view" not in views_text:
    views_text += lead_views_code
    views_file.write_text(views_text, encoding="utf-8")
    print("✓ Added submit_lead_view to catalog/views.py")

# Update catalog/urls.py
urls_file = BASE / "src/apps/catalog/urls.py"
urls_text = urls_file.read_text(encoding="utf-8")
if "submit_lead" not in urls_text:
    urls_text = urls_text.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('leads/submit/', views.submit_lead_view, name='submit_lead'),"
    )
    urls_file.write_text(urls_text, encoding="utf-8")
    print("✓ Added lead submission route to catalog/urls.py")

# Create feedback partial: src/templates/catalog/partials/lead_feedback.html
partial_file = BASE / "src/templates/catalog/partials/lead_feedback.html"
partial_file.write_text("""<div class="p-4 bg-rihan-100 text-rihan-900 rounded-2xl border border-rihan-200 text-xs text-center font-bold">
    ✓ {{ message }}
</div>
""", encoding="utf-8")

# Update src/templates/catalog/list.html to add Custom Request Box
list_template = BASE / "src/templates/catalog/list.html"
list_text = list_template.read_text(encoding="utf-8")
if "درخواست گزینش محصول خاص" not in list_text:
    lead_box_code = """
    <!-- Custom Product Request & Lead Capture Box (M9 - Flow C3) -->
    <div class="mt-16 bg-white rounded-3xl border border-gray-100 p-8 shadow-sm">
        <div class="max-w-2xl mx-auto text-center space-y-3">
            <span class="text-3xl block">🌿</span>
            <h2 class="text-xl font-bold text-gray-900">محصول خاصی از اصالت آذربایجان یا شمال مدنظرتان است؟</h2>
            <p class="text-xs text-gray-500 leading-relaxed">
                اگر کالای ناب و اصیلی می‌شناسید که در کاتالوگ ریهان موجود نیست، نام آن را بنویسید تا تیم ریهان پس از بررسی و آزمایش اصالت، آن را برای شما تأمین کند.
            </p>

            <div id="lead-feedback-box" class="pt-4">
                <form method="post" action="{% url 'submit_lead' %}" hx-post="{% url 'submit_lead' %}" hx-target="#lead-feedback-box" class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-right">
                    {% csrf_token %}
                    <div>
                        <input type="text" name="requested_product_name" required 
                               class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" 
                               placeholder="نام کالای درخواستی *">
                    </div>
                    <div>
                        <input type="tel" name="phone" required 
                               class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" 
                               placeholder="شماره موبایل شما *">
                    </div>
                    <div>
                        <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-sm">
                            ثبت درخواست گزینش ↗
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
"""
    list_text = list_text.replace("{% endblock %}", lead_box_code + "\n{% endblock %}")
    list_template.write_text(list_text, encoding="utf-8")
    print("✓ Added Lead Capture Box to src/templates/catalog/list.html")

# Create Unit Tests: tests/test_leads.py
test_file = BASE / "tests/test_leads.py"
test_code = """from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, LeadCapture

class LeadCaptureTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="سوغات", slug="souvenir-l")
        self.p = Product.objects.create(
            category=self.cat, title="توت خشک هوراند", slug="tut-khoshk",
            sku="RIHAN-TUT-01", summary="توت خشک ارگانیک", price=320000, stock=0, is_available=False
        )

    def test_submit_lead_for_custom_product(self):
        c = Client()
        res = c.post(reverse('submit_lead'), {
            'phone': '09121112233',
            'full_name': 'حسن معلم',
            'requested_product_name': 'گردوی درجه یک کلیبر',
            'notes': 'پوست کاغذی و پرچرب'
        })
        self.assertEqual(res.status_code, 302)
        
        lead = LeadCapture.objects.filter(phone='09121112233').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.requested_product_name, 'گردوی درجه یک کلیبر')
        self.assertEqual(lead.status, 'new')

    def test_submit_lead_for_out_of_stock_product(self):
        c = Client()
        res = c.post(reverse('submit_lead'), {
            'phone': '09149998877',
            'product_id': self.p.id
        })
        self.assertEqual(res.status_code, 302)
        
        lead = LeadCapture.objects.filter(product=self.p).first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.product.title, 'توت خشک هوراند')
"""
test_file.write_text(test_code, encoding="utf-8")
print("✓ Created tests/test_leads.py")

# Register M9 in PluginRegistry
plugins_file = BASE / "src/apps/core/plugins.py"
plugins_text = plugins_file.read_text(encoding="utf-8")
if 'PluginRegistry.register("M9"' not in plugins_text:
    plugins_text += '\nPluginRegistry.register("M9", "فرم ثبت سرنخ و اطلاع‌رسانی کالای ناموجود C3", "0.5.11", is_system=True)\n'
    plugins_file.write_text(plugins_text, encoding="utf-8")
    print("✓ Registered M9 in PluginRegistry")

print("Module M9 (Lead Capture) Deployed Successfully.")
