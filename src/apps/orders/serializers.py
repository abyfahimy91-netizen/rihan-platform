from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'product_sku', 'unit_price', 'quantity', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer_name', 'customer_phone', 'customer_email', 'province', 'city', 'shipping_address', 'postal_code', 'customer_notes', 'items_total', 'shipping_cost', 'grand_total', 'status', 'payment_method', 'tracking_code', 'created_at', 'items']
