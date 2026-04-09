from rest_framework import serializers
from .models import Product, VisualRecognitionRecord, StockOperation

class ProductSerializer(serializers.ModelSerializer):
    """商品序列化器"""
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'price', 'stock', 'locked_stock', 'location', 'image', 'is_active', 'created_at', 'updated_at']
        extra_kwargs = {
            'image': {'read_only': True}
        }
    
    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("库存数量不能为负数")
        return value
    
    def validate_locked_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("锁定库存数量不能为负数")
        return value

class VisualRecognitionRecordSerializer(serializers.ModelSerializer):
    """视觉识别记录序列化器"""
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = VisualRecognitionRecord
        fields = ['record_id', 'image_path', 'algorithm_used', 'recognition_result', 'status', 'status_display', 'created_at']
        read_only_fields = ['record_id', 'status', 'status_display', 'created_at']
        extra_kwargs = {
            'recognition_result': {'read_only': True}
        }


class StockOperationSerializer(serializers.ModelSerializer):
    """库存操作记录序列化器"""
    product_name = serializers.ReadOnlyField(source='product.name')
    operation_type_display = serializers.ReadOnlyField(source='get_operation_type_display')
    
    class Meta:
        model = StockOperation
        fields = ['id', 'product', 'product_name', 'operation_type', 'operation_type_display', 'quantity', 'reason', 'created_at']
        read_only_fields = ['id', 'product_name', 'operation_type_display', 'created_at']