"""
URLs ماژول family_panel
منطبق بر US-017, US-025, US-026, US-027, US-055
"""
from django.urls import path
from .views import (
    # Dashboard
    dashboard_view,
    dashboard_summary_view,
    dashboard_alerts_view,
    # Admin Management
    list_family_members,
    add_family_member,
    deactivate_family_member,
    reactivate_family_member,
    # Activity Log
    activity_log_list,
    activity_log_stats,
    # Block Editor
    get_available_blocks,
    get_product_blocks,
    add_product_block,
    update_product_block,
    remove_product_block,
    reorder_product_blocks,
    preview_product,
    publish_product,
    save_draft,
)

app_name = 'family_panel'

urlpatterns = [
    # داشبورد (US-017)
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/summary/', dashboard_summary_view, name='dashboard-summary'),
    path('dashboard/alerts/', dashboard_alerts_view, name='dashboard-alerts'),
    
    # مدیریت کاربران خانواده (US-025)
    path('members/', list_family_members, name='list-members'),
    path('members/add/', add_family_member, name='add-member'),
    path('members/deactivate/', deactivate_family_member, name='deactivate-member'),
    path('members/reactivate/', reactivate_family_member, name='reactivate-member'),
    
    # لاگ فعالیت‌ها (US-026)
    path('activity-log/', activity_log_list, name='activity-log'),
    path('activity-log/stats/', activity_log_stats, name='activity-log-stats'),
    
    # ویرایشگر بلوک‌محور (US-055)
    path('blocks/available/', get_available_blocks, name='available-blocks'),
    path('products/<int:product_id>/blocks/', get_product_blocks, name='product-blocks'),
    path('products/<int:product_id>/blocks/add/', add_product_block, name='add-block'),
    path('products/<int:product_id>/blocks/<str:block_id>/update/', update_product_block, name='update-block'),
    path('products/<int:product_id>/blocks/<str:block_id>/remove/', remove_product_block, name='remove-block'),
    path('products/<int:product_id>/blocks/reorder/', reorder_product_blocks, name='reorder-blocks'),
    path('products/<int:product_id>/preview/', preview_product, name='preview-product'),
    path('products/<int:product_id>/publish/', publish_product, name='publish-product'),
    path('products/<int:product_id>/draft/', save_draft, name='save-draft'),
]
