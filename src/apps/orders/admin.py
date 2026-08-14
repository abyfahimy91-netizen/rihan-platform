from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_title', 'product_sku', 'unit_price', 'quantity', 'subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'city', 'grand_total', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'tracking_code']
    readonly_fields = ['order_number', 'items_total', 'shipping_cost', 'grand_total', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
