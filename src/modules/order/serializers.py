from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from src.modules.catalog.models import Product

class ProductMinimalSerializer(serializers.ModelSerializer):
    '''نمایش حداقلی محصول در سبد خرید'''
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'stock_quantity', 'image']


class CartItemSerializer(serializers.ModelSerializer):
    '''اقلام سبد خرید - با شفافیت قیمت (D-046)'''
    product = ProductMinimalSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'unit_price_at_add', 'subtotal', 'added_at']


class CartSerializer(serializers.ModelSerializer):
    '''سبد خرید کامل'''
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'session_key', 'user', 'is_active', 'items', 'total_items', 'subtotal', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
