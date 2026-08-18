"""
SEO views for Rihan Platform
"""
from django.http import HttpResponse


def robots_txt(request):
    """
    Generate robots.txt dynamically
    Allows all crawlers, points to sitemap
    """
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
