"""
Admin panel for Reviews Module (M8)
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import Review

from src.core.fa import jalali_datetime_str


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin panel for product reviews"""
    
    list_display = (
        'reviewer_display',
        'product',
        'rating_display',
        'text_preview',
        'is_approved',
        'created_at_fa',
        'approve_action',
    )
    
    list_filter = (
        'is_approved',
        'rating',
        'created_at',
    )
    
    search_fields = (
        'product__name',
        'user__username',
        'guest_name',
        'guest_phone',
        'text',
    )
    
    readonly_fields = (
        'id',
        'order',
        'guest_token',
        'token_expires_at',
        'token_used',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Review Info', {
            'fields': (
                'product',
                'order',
                'rating',
                'title',
                'text',
            )
        }),
        ('Reviewer', {
            'fields': (
                'user',
                'guest_name',
                'guest_phone',
            )
        }),
        ('Approval', {
            'fields': (
                'is_approved',
                'approved_by',
                'approved_at',
                'admin_reply',
            )
        }),
        ('Guest Token', {
            'fields': (
                'guest_token',
                'token_expires_at',
                'token_used',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'id',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['approve_reviews', 'unapprove_reviews']
    
    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ثبت'
    created_at_fa.admin_order_field = 'created_at'

    def reviewer_display(self, obj):
        """Display reviewer name"""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return f"{obj.guest_name} (مهمان)"
    reviewer_display.short_description = 'Reviewer'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        return format_html('⭐' * obj.rating)
    rating_display.short_description = 'Rating'
    
    def text_preview(self, obj):
        """Show first 50 chars of review text"""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Review'
    
    def approve_action(self, obj):
        """Show approve/unapprove button"""
        if obj.is_approved:
            return format_html(
                '<span style="color: green;">✅ Approved</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending</span>'
        )
    approve_action.short_description = 'Status'
    
    def approve_reviews(self, request, queryset):
        """Bulk approve selected reviews"""
        count = 0
        for review in queryset:
            if not review.is_approved:
                review.approve(request.user)
                count += 1
        self.message_user(request, f'{count} review(s) approved')
    approve_reviews.short_description = 'Approve selected reviews'
    
    def unapprove_reviews(self, request, queryset):
        """Bulk unapprove selected reviews"""
        count = queryset.update(
            is_approved=False,
            approved_by=None,
            approved_at=None
        )
        self.message_user(request, f'{count} review(s) unapproved')
    unapprove_reviews.short_description = 'Unapprove selected reviews'
