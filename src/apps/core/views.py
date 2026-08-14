from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "platform": "RIHAN Platform",
        "version": "0.5.0-dev",
        "phase": 5,
        "active_modules": 14,
        "os_framework": "AI-VOS v1.1.1"
    })

def home_view(request):
    return JsonResponse({
        "message": "به پلتفرم ریهان خوش آمدید",
        "brand": "RIHAN - Curated Marketplace",
        "description": "فروشگاه آنلاین اعتمادمحور مبتنی بر سیستم‌عامل AI-VOS",
        "health_endpoint": "/api/health/"
    }, json_dumps_params={'ensure_ascii': False})
