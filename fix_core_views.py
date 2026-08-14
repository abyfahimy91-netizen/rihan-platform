from pathlib import Path

BASE = Path("/root/rihan-platform")
views_file = BASE / "src/apps/core/views.py"

content = """from django.shortcuts import render
from django.http import JsonResponse

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
    return JsonResponse({
        "message": "به پلتفرم ریهان خوش آمدید",
        "brand": "RIHAN - Curated Marketplace",
        "description": "فروشگاه آنلاین اعتمادمحور مبتنی بر سیستم‌عامل AI-VOS",
        "health_endpoint": "/api/health/",
        "about_endpoint": "/about/",
        "catalog_endpoint": "/products/"
    }, json_dumps_params={'ensure_ascii': False})

def about_view(request):
    \"\"\"صفحه اصالت، فلسفه گزینش و داستان برند ریهان (M12 - CENTRAL-STORY.md)\"\"\"
    return render(request, 'core/about.html')
"""
views_file.write_text(content, encoding="utf-8")
print("✓ Successfully updated src/apps/core/views.py with render import")
