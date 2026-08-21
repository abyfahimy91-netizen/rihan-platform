from django.shortcuts import render

def about_view(request):
    """صفحه درباره ریهان - US-013"""
    context = {
        "page_title": "درباره ریهان",
    }
    return render(request, "pages/about.html", context)

def contact_view(request):
    """صفحه تماس با ما - US-014"""
    context = {
        "page_title": "تماس با ما",
    }
    return render(request, "pages/contact.html", context)

def return_policy_view(request):
    """صفحه سیاست مرجوعی - US-015"""
    context = {
        "page_title": "سیاست مرجوعی",
    }
    return render(request, "pages/return_policy.html", context)
