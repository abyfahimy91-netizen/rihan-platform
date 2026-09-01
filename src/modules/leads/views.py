"""
Views for Leads Module (M9)

Implements US-010: Product availability notification form
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from src.modules.catalog.models import Product
from .models import Lead


@require_http_methods(["GET", "POST"])
def lead_form_page(request, product_slug=None):
    """
    Lead registration form.
    
    GET: Show form
    POST: Validate and create lead
    
    If product_slug is provided, the lead is tied to that product.
    Otherwise, it's a general lead.
    """
    product = None
    if product_slug:
        product = get_object_or_404(Product, slug=product_slug, status='active')
    
    if request.method == 'GET':
        return render(request, 'leads/lead_form.html', {
            'product': product,
        })
    
    # POST - Process submission
    phone = request.POST.get('phone', '').strip()
    name = request.POST.get('name', '').strip()
    
    # Validate phone
    if not phone:
        error = 'شماره موبایل الزامی است'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error}, status=400)
        return render(request, 'leads/lead_form.html', {
            'product': product,
            'error': error,
            'form_data': {'phone': phone, 'name': name},
        })
    
    # Check if lead can be created
    can_create, message = Lead.can_create_lead(phone, product)
    
    if not can_create:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': message}, status=400)
        return render(request, 'leads/lead_form.html', {
            'product': product,
            'error': message,
            'form_data': {'phone': phone, 'name': name},
        })
    
    # Create lead
    lead = Lead.objects.create(
        phone=phone,
        name=name[:100] if name else '',
        product=product,
        status=Lead.LeadStatus.PENDING,
    )
    
    # Success response
    success_message = ('درخواست شما با موفقیت ثبت شد؛ به‌محض موجود شدن این محصول، '
                       'به شما اطلاع خواهیم داد. سپاس از صبر و همراهی شما.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': success_message,
            'lead_id': str(lead.id),
        })
    
    messages.success(request, success_message)
    return render(request, 'leads/lead_success.html', {
        'lead': lead,
        'product': product,
    })


@require_http_methods(["POST"])
def submit_lead_api(request):
    """
    API endpoint for lead submission (AJAX).
    
    Expected POST data:
    - phone (required)
    - name (optional)
    - product_slug (optional)
    """
    phone = request.POST.get('phone', '').strip()
    name = request.POST.get('name', '').strip()
    product_slug = request.POST.get('product_slug', '').strip()
    
    # Get product if provided
    product = None
    if product_slug:
        try:
            product = Product.objects.get(slug=product_slug, status='active')
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'محصول یافت نشد'
            }, status=404)
    
    # Validate
    if not phone:
        return JsonResponse({
            'success': False,
            'error': 'شماره موبایل الزامی است'
        }, status=400)
    
    can_create, message = Lead.can_create_lead(phone, product)
    
    if not can_create:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)
    
    # Create lead
    lead = Lead.objects.create(
        phone=phone,
        name=name[:100] if name else '',
        product=product,
        status=Lead.LeadStatus.PENDING,
    )
    
    return JsonResponse({
        'success': True,
        'message': 'ثبت شد. اطلاع می‌دهیم.',
        'lead_id': str(lead.id),
    })


# ══════════════════════════════════════════════════════════════════
# D-125: پنل ردیابی سرنخ‌های بازدید (staff-only)
# ══════════════════════════════════════════════════════════════════
import json
import os
import jdatetime
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .analytics import SNAPSHOT_CACHE_KEY, funnel_counts, import_from_snapshot
from .models import VisitorLead


def _snapshot_path():
    return getattr(settings, 'LEADS_SNAPSHOT_PATH', '/tmp/rihan_analytics.json')


def _visitor_staff(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, 'دسترسی غیرمجاز. فقط ادمین‌ها مجاز هستند.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _jdate(dt, with_time=True):
    if not dt:
        return '—'
    j = jdatetime.datetime.fromgregorian(datetime=timezone.localtime(dt))
    return j.strftime('%Y/%m/%d %H:%M' if with_time else '%Y/%m/%d')


def _panel_queryset(request):
    """فیلترهای GET → queryset (بین پنل و CSV مشترک)."""
    qs = VisitorLead.objects.all()
    g = request.GET
    q = (g.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(ip__icontains=q) | Q(city__icontains=q) | Q(isp__icontains=q) |
                       Q(order_refs__icontains=q) | Q(admin_notes__icontains=q) |
                       Q(phone__icontains=q) | Q(name__icontains=q) | Q(link_code__icontains=q))
    stage = g.get('stage') or ''
    if stage in VisitorLead.Stage.values:
        qs = qs.filter(stage=stage)
    reach = g.get('reach') or ''
    if reach.isdigit() and 1 <= int(reach) <= 6:
        qs = qs.filter(stage_rank__gte=int(reach))
    status = g.get('status') or ''
    if status in VisitorLead.LeadStatus.values:
        qs = qs.filter(status=status)
    device = (g.get('device') or '').strip()
    if device:
        qs = qs.filter(device__iexact=device)
    channel = (g.get('channel') or '').strip()
    if channel:
        qs = qs.filter(Q(channel_first__iexact=channel) | Q(channels__icontains=channel))
    vpn = g.get('vpn') or ''
    if vpn == '1':
        qs = qs.filter(is_vpn=True)
    elif vpn == '0':
        qs = qs.filter(is_vpn=False)
    hot = g.get('hot') or ''
    if hot == '1':
        qs = qs.filter(is_hot=True).exclude(status__in=[VisitorLead.LeadStatus.BUYER, VisitorLead.LeadStatus.JUNK])
    ordering = g.get('o') or '-last_seen'
    allowed = {'-last_seen', 'last_seen', '-page_views', 'page_views', '-stage_rank', 'stage_rank', '-sessions_count'}
    if ordering in allowed:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-last_seen')
    return qs


def _panel_summary():
    agg = VisitorLead.objects.aggregate(views=Sum('page_views'), sessions=Sum('sessions_count'))
    return {
        'visitors': VisitorLead.objects.count(),
        'views': agg['views'] or 0,
        'sessions': agg['sessions'] or 0,
        'funnel': funnel_counts(),
        'hot_count': VisitorLead.objects.filter(is_hot=True).exclude(
            status__in=[VisitorLead.LeadStatus.BUYER, VisitorLead.LeadStatus.JUNK]).count(),
        'converted_count': VisitorLead.objects.filter(stage='CONVERTED').count(),
        'devices': VisitorLead.objects.exclude(device='').values('device').annotate(
            n=Count('id')).order_by('-n')[:6],
        'channels': VisitorLead.objects.values('channel_first').annotate(
            n=Count('id')).order_by('-n')[:8],
        'meta': _snapshot_meta(),
    }


def _snapshot_meta():
    """متادیتای آخرین import — از فایل (پایدار) یا کش."""
    try:
        with open('/tmp/rihan_snapshot_meta.json') as f:
            return json.load(f)
    except Exception:
        return cache.get(SNAPSHOT_CACHE_KEY) or {}


@_visitor_staff
def lead_panel(request):
    qs = _panel_queryset(request)
    try:
        page_num = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page_num = 1
    paginator = Paginator(qs, 50)
    page = paginator.get_page(page_num)
    for lead in page.object_list:
        lead.last_seen_j = _jdate(lead.last_seen)
        lead.first_seen_j = _jdate(lead.first_seen)
    code_q = (request.GET.get('code') or '').strip().upper()
    code_q = (request.GET.get('code') or '').strip().upper()
    context = {
        'title': 'ردیابی سرنخ‌های بازدید',
        'page': page,
        'filters': request.GET,
        'filters_qs': _filters_qs(request),
        'stages': VisitorLead.Stage.choices,
        'statuses': VisitorLead.LeadStatus.choices,
        'summary': _panel_summary(),
        'snapshot_path': _snapshot_path(),
        'link_target': (VisitorLead.objects.filter(
            link_code=code_q).first() if code_q else None),
    }
    return render(request, 'leads/panel.html', context)


def _filters_qs(request):
    """کوئری‌استرینگ فعلی بدون page — برای لینک CSV و صفحه‌بندی."""
    from urllib.parse import urlencode
    qd = request.GET.copy()
    qd.pop('page', None)
    return urlencode(qd)


@_visitor_staff
def lead_panel_status(request, pk):
    """تغییر سریع وضعیت CRM از داخل جدول پنل (POST از select)."""
    if request.method == 'POST':
        lead = VisitorLead.objects.filter(pk=pk).first()
        new_status = request.POST.get('status') or ''
        if lead and new_status in VisitorLead.LeadStatus.values:
            lead.status = new_status
            lead.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'وضعیت {lead.ip} → {lead.get_status_display()} ثبت شد.')
        else:
            messages.error(request, 'درخواست نامعتبر بود.')
    return redirect('leads:panel')


@_visitor_staff
def lead_panel_refresh(request):
    """دکمهٔ «به‌روزرسانی از آخرین snapshot» — POST فقط."""
    if request.method != 'POST':
        return redirect('leads:panel')
    if os.path.exists(_snapshot_path()):
        try:
            stats = import_from_snapshot(_snapshot_path())
            messages.success(request, (
                f"به‌روزرسانی شد — {stats['visitors']} سرنخ "
                f"({stats['created']} جدید، {stats['updated']} به‌روز، {stats['hot']} داغ)"))
        except Exception as e:  # snapshot ناقص/خراب نباید صفحه را بترکاند
            messages.error(request, f'خطا در import: {e}')
    else:
        messages.warning(request, 'فایل snapshot روی سرور نیست — cron آن را تولید می‌کند.')
    return redirect('leads:panel')


@_visitor_staff
def lead_panel_csv(request):
    import csv as csv_mod
    qs = _panel_queryset(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="visitor-leads.csv"'
    response.write('\ufeff')  # BOM برای اکسل فارسی
    w = csv_mod.writer(response)
    w.writerow(['IP', 'هویت (شماره)', 'نام', 'کشور', 'شهر', 'ISP', 'دستگاه', 'کانال ورود', 'همهٔ کانال‌ها',
                'مرحله', 'ویو', 'سشن', 'اولین بازدید', 'آخرین بازدید',
                'سفارش‌ها در لاگ', 'وضعیت سفارش‌های DB', 'داغ', 'وضعیت CRM', 'یادداشت'])
    for v in qs:
        w.writerow([
            v.ip, v.phone or '—', v.name or '—', v.country, v.city, v.isp, v.device, v.channel_first,
            '، '.join(v.channels or []),
            v.get_stage_display(), v.page_views, v.sessions_count,
            _jdate(v.first_seen), _jdate(v.last_seen),
            v.order_refs or '—',
            '؛ '.join(f"{m['number']}={m['status']}" for m in (v.orders_matched or [])) or '—',
            'بله' if v.is_hot else '',
            v.get_status_display(),
            (v.admin_notes or '').replace('\n', ' '),
        ])
    return response
