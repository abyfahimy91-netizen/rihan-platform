import uuid
from django.db import models


class AuditLog(models.Model):
    """
    Model AuditLog based on ADR-002 section 2.17 and ADR-006
    Tracks all important events in the system for security and compliance
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('otp_request', 'OTP Request'),
        ('otp_verify', 'OTP Verify'),
        ('payment_confirm', 'Payment Confirm'),
        ('payment_reject', 'Payment Reject'),
        ('order_status', 'Order Status Change'),
        ('feature_flag', 'Feature Flag Change'),
        ('block_edit', 'Block Edit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-created_at']

    def __str__(self):
        user_str = str(self.user_id) if self.user_id else 'System'
        return f"{self.action} on {self.entity_type} by {user_str} at {self.created_at}"

    @classmethod
    def log(cls, user, action, entity_type, entity_id=None, old_values=None, new_values=None, ip_address=None, user_agent=None):
        """Helper method to create audit log entries"""
        return cls.objects.create(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            device_user_agent=user_agent
        )
