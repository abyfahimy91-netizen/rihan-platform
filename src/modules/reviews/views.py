"""
Views for Reviews Module (M8)

Implements US-009: Customer reviews for products
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages

from src.modules.catalog.models import Product
from src.modules.order.models import Order
from .models import Review


@require_http_methods(["GET", "POST"])
@login_required
def submit_review(request, product_slug):
    """
    Submit a review for a product (registered user).
    
    Rules:
    - User must have a DELIVERED order containing this product
    - One review per order
    - Review starts as pending (is_approved=False)
    """
    product = get_object_or_404(Product, slug=product_slug, status='active')
    
    # Find user's delivered orders containing this product
    delivered_orders = Order.objects.filter(
        user=request.user,
        status=Order.OrderStatus.DELIVERED,
        items__product=product
    ).distinct()
    
    if not delivered_orders.exists():
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'error': 'فقط مشتریان با سفارش تحویل‌شده می‌توانند نظر دهند'
            }, status=403)
        return render(request, 'reviews/no_access.html', {
            'product': product,
            'reason': 'no_delivered_order'
        })
    
    # Check if user already reviewed any of these orders
    reviewed_orders = [o for o in delivered_orders if Review.objects.filter(order=o).exists()]
    available_orders = [o for o in delivered_orders if o not in reviewed_orders]
    
    if not available_orders:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'error': 'شما قبلاً برای این محصول نظر ثبت کرده‌اید'
            }, status=403)
        return render(request, 'reviews/no_access.html', {
            'product': product,
            'reason': 'already_reviewed'
        })
    
    if request.method == 'GET':
        return render(request, 'reviews/submit_review.html', {
            'product': product,
            'orders': available_orders,
        })
    
    # POST - Process review submission
    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    text = request.POST.get('text', '').strip()
    order_number = request.POST.get('order_number')
    
    # Validate
    errors = []
    if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        errors.append('امتیاز باید بین ۱ تا ۵ باشد')
    if not text:
        errors.append('متن نظر نمی‌تواند خالی باشد')
    if len(text) > 500:
        errors.append(f'متن نظر نباید بیش از ۵۰۰ کاراکتر باشد (فعلی: {len(text)})')
    
    # Find the specific order
    selected_order = None
    if order_number:
        for order in available_orders:
            if order.order_number == order_number:
                selected_order = order
                break
    
    if not selected_order:
        selected_order = available_orders[0]
    
    if errors:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return render(request, 'reviews/submit_review.html', {
            'product': product,
            'orders': available_orders,
            'errors': errors,
            'form_data': {'rating': rating, 'title': title, 'text': text},
        })
    
    # Create review
    review = Review.objects.create(
        product=product,
        order=selected_order,
        user=request.user,
        rating=int(rating),
        title=title[:100],
        text=text[:500],
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود'
        })
    
    messages.success(request, 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود')
    return redirect('catalog:product_detail', slug=product_slug)


@require_http_methods(["GET", "POST"])
def guest_review_form(request, token):
    """
    Guest review form (access via SMS token link).
    
    Token is one-time use, 7 days validity.
    """
    review = get_object_or_404(Review, guest_token=token)
    
    # Check token validity
    if not review.is_token_valid():
        return render(request, 'reviews/token_expired.html', {
            'reason': 'used' if review.token_used else 'expired'
        })
    
    # If review already has text, token was used
    if review.text and review.token_used:
        return render(request, 'reviews/token_expired.html', {
            'reason': 'used'
        })
    
    if request.method == 'GET':
        return render(request, 'reviews/guest_review.html', {
            'review': review,
            'product': review.product,
        })
    
    # POST - Process submission
    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    text = request.POST.get('text', '').strip()
    
    errors = []
    if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        errors.append('امتیاز باید بین ۱ تا ۵ باشد')
    if not text:
        errors.append('متن نظر نمی‌تواند خالی باشد')
    if len(text) > 500:
        errors.append(f'متن نظر نباید بیش از ۵۰۰ کاراکتر باشد (فعلی: {len(text)})')
    
    if errors:
        return render(request, 'reviews/guest_review.html', {
            'review': review,
            'product': review.product,
            'errors': errors,
            'form_data': {'rating': rating, 'title': title, 'text': text},
        })
    
    # Update the placeholder review
    review.rating = int(rating)
    review.title = title[:100]
    review.text = text[:500]
    review.use_token()  # Mark token as used
    review.save()
    
    messages.success(request, 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود')
    return render(request, 'reviews/guest_success.html', {
        'review': review,
        'product': review.product,
    })


def product_reviews_api(request, product_slug):
    """
    API endpoint to get approved reviews for a product.
    Used for AJAX loading on product page.
    """
    product = get_object_or_404(Product, slug=product_slug, status='active')
    
    reviews = Review.objects.filter(
        product=product,
        is_approved=True
    ).select_related('user').order_by('-created_at')[:50]
    
    data = {
        'count': reviews.count(),
        'average_rating': _calculate_average_rating(product),
        'reviews': [
            {
                'id': str(r.id),
                'reviewer': _get_reviewer_name(r),
                'rating': r.rating,
                'title': r.title,
                'text': r.text,
                'date': r.created_at.strftime('%Y/%m/%d'),
                'admin_reply': r.admin_reply or None,
            }
            for r in reviews
        ]
    }
    
    return JsonResponse(data)


def _calculate_average_rating(product):
    """Calculate average rating for a product (approved reviews only)."""
    reviews = Review.objects.filter(product=product, is_approved=True)
    if not reviews.exists():
        return 0
    total = sum(r.rating for r in reviews)
    return round(total / reviews.count(), 1)


def _get_reviewer_name(review):
    """Get reviewer display name (privacy-safe)."""
    if review.user:
        if review.user.first_name:
            # Show first name + last initial
            last_initial = review.user.last_name[0] + '.' if review.user.last_name else ''
            return f"{review.user.first_name} {last_initial}".strip()
        # Mask username (phone)
        username = review.user.username
        if len(username) >= 11 and username.isdigit():
            return username[:4] + '***' + username[-4:]
        return username
    # Guest: show guest_name with masking
    if review.guest_name:
        name = review.guest_name
        if len(name) > 2:
            return name[:1] + '*' * (len(name) - 2) + name[-1]
        return name
    return 'مشتری'
