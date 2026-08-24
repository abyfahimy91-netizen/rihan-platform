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
