"""
M13: Visual Identity Views
"""
from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """صفحه اصلی ریهان"""
    template_name = 'visual_identity/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # TODO: دریافت محصولات ویژه از M1 (catalog)
        # فعلاً لیست خالی
        context['featured_products'] = []
        
        return context
