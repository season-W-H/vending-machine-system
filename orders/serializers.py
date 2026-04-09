from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    """订单项序列化器"""
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.ReadOnlyField(source='product.price')
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_price', 'quantity', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    """订单序列化器"""
    order_no = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_no', 'user', 'status', 'total_amount', 'created_at']

class OrderDetailSerializer(OrderSerializer):
    """订单详情序列化器"""
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['items']