"""
Models for Reviews Module (M8)

Implements US-009: Customer reviews for products
- Only customers with delivered orders can review
- Registered users: review from product page
- Guest users: review via SMS token (one-time, 7 days validity)
- Admin approval before display
- Max 500 characters
"""
import uuid
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Review(models.Model):
    """
    Product review (M8 - US-009)
    
    A review is tied to:
    - A product (what is being reviewed)
    - An order (proof of purchase, must be DELIVERED)
    - A user (if registered) OR guest_name + guest_phone (if guest)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What is being reviewed
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Proof of purchase (must be DELIVERED)
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Who is reviewing (registered user OR guest)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviews',
        verbose_name="Registered user"
    )
    guest_name = models.CharField(
        max_length=100, blank=True,
        verbose_name="Guest name"
    )
    # D-104: حریم خصوصی — پیش‌فرض نمایش ناشناس نظر
    display_anonymously = models.BooleanField(
        default=True,
        verbose_name="نمایش ناشناس نام نظردهنده",
        help_text="اگر روشن باشد، نام کاربر به‌صورت محرمانه (مثلاً «م. ح.» یا «خریدار تأییدشده») نمایش داده می‌شود.",
    )
    guest_phone = models.CharField(
        max_length=20, blank=True,
        verbose_name="Guest phone (for token verification)"
    )
    
    # Review content
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="Rating (1-5 stars)"
    )
    title = models.CharField(
        max_length=100, blank=True,
        verbose_name="Title (optional)"
    )
    text = models.TextField(
        max_length=500,
        verbose_name="Review text (max 500 chars)"
    )
    
    # Approval workflow
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Approved by admin"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_reviews',
        verbose_name="Approved by"
    )
    approved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Approval time"
    )
    admin_reply = models.TextField(
        blank=True,
        verbose_name="Admin reply"
    )
    
    # Guest token (for one-time access via SMS link)
    guest_token = models.CharField(
        max_length=64, blank=True, db_index=True,
        verbose_name="One-time token for guests"
    )
    token_expires_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Token expiration (7 days)"
    )
    token_used = models.BooleanField(
        default=False,
        verbose_name="Token has been used"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['order']),
        ]
        constraints = [
            # One review per order
            models.UniqueConstraint(
                fields=['order'],
                name='unique_review_per_order'
            ),
        ]
    
    def __str__(self):
        reviewer = self.user.username if self.user else self.guest_name
        return f"{reviewer} - {self.product.name} ({self.rating}★)"
    
    @classmethod
    def generate_guest_token(cls):
        """Generate a secure one-time token for guest reviews."""
        return secrets.token_urlsafe(32)
    
    def is_token_valid(self):
        """Check if guest token is still valid."""
        if not self.guest_token or self.token_used:
            return False
        if self.token_expires_at and timezone.now() > self.token_expires_at:
            return False
        return True
    
    def use_token(self):
        """Mark token as used."""
        self.token_used = True
        self.save(update_fields=['token_used'])
    
    def approve(self, admin_user):
        """Approve the review."""
        self.is_approved = True
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
    
    @classmethod
    def can_review(cls, order, user=None):
        """
        Check if an order can be reviewed.
        
        Rules:
        - Order must be DELIVERED
        - No existing review for this order
        """
        from src.modules.order.models import Order
        
        if order.status != Order.OrderStatus.DELIVERED:
            return False, "فقط سفارش‌های تحویل‌شده قابل نظر دادن هستند"
        
        if cls.objects.filter(order=order).exists():
            return False, "برای این سفارش قبلاً نظر ثبت شده است"
        
        return True, "مجاز به ثبت نظر"
    
    @classmethod
    def create_guest_review_token(cls, order):
        """
        Create a guest review token for a delivered order.
        Used when admin wants to send SMS link to guest customer.
        """
        token = cls.generate_guest_token()
        expires_at = timezone.now() + timedelta(days=7)
        
        # Create a placeholder review with token
        review = cls.objects.create(
            product=order.items.first().product if order.items.exists() else None,
            order=order,
            guest_name=order.guest_name,
            guest_phone=order.guest_phone,
            rating=5,  # Default, will be updated when guest submits
            text='',   # Empty, will be filled
            guest_token=token,
            token_expires_at=expires_at,
        )
        
        return review, token
