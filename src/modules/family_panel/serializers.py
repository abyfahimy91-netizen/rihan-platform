"""
Serializers ماژول family_panel
منطبق بر US-025, US-026
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import ActivityLog

User = get_user_model()


class FamilyMemberSerializer(serializers.Serializer):
    """Serializer برای اعضای خانواده"""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    phone = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    
    def get_phone(self, obj):
        # ماسک شماره: ۰۹۱۲***۷۸۹۰
        phone = obj.username
        if len(phone) >= 8:
            return f"{phone[:4]}***{phone[-4:]}"
        return phone
    
    def get_role(self, obj):
        from src.modules.rbac.services import RoleService
        primary_role = RoleService.get_user_primary_role(obj)
        if primary_role:
            return {
                'code': primary_role.code,
                'name': primary_role.name,
            }
        return None


class AddFamilyMemberSerializer(serializers.Serializer):
    """Serializer برای افزودن عضو خانواده"""
    phone = serializers.CharField(max_length=11, min_length=11)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    role_code = serializers.ChoiceField(
        choices=['family_admin', 'family_member', 'observer'],
        default='family_member'
    )


class ActivityLogSerializer(serializers.Serializer):
    """Serializer برای لاگ فعالیت‌ها"""
    id = serializers.UUIDField(read_only=True)
    user = serializers.SerializerMethodField()
    action = serializers.CharField(read_only=True)
    action_display = serializers.SerializerMethodField()
    description = serializers.CharField(read_only=True)
    entity_type = serializers.CharField(read_only=True)
    entity_id = serializers.CharField(read_only=True)
    ip_address = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def get_user(self, obj):
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.username
    
    def get_action_display(self, obj):
        return obj.get_action_display()
