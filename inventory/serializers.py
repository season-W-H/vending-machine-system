from rest_framework import serializers
from .models import Inventory

class InventorySerializer(serializers.ModelSerializer):
    """库存序列化器"""
    product_id = serializers.ReadOnlyField(source='product.id')
    product_name = serializers.ReadOnlyField(source='product.name')
    product_location = serializers.ReadOnlyField(source='product.location')
    product_price = serializers.ReadOnlyField(source='product.price')
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'product_id', 'product_name', 'product_location',
            'product_price', 'current_stock', 'alarm_threshold', 
            'is_low_stock', 'last_checked', 'updated_at'
        ]
        read_only_fields = [
            'product', 'product_id', 'product_name', 'product_location',
            'product_price', 'is_low_stock', 'updated_at'
        ]
        
    def validate_current_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("当前库存数量不能为负数")
        return value
    
    def validate_alarm_threshold(self, value):
        if value < 0:
            raise serializers.ValidationError("预警阈值不能为负数")
        return value