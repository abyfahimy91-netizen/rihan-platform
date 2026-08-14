from django.shortcuts import render
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
    """صفحه اصلی و لندینگ‌پیج فاخر ریهان (M13 - Home Landing Page)"""
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
    """صفحه اصالت، فلسفه گزینش و داستان برند ریهان (M12 - CENTRAL-STORY.md)"""
    return render(request, 'core/about.html')
