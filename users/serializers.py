from rest_framework import serializers
from .models import User, PaymentMethod

class PaymentMethodSerializer(serializers.ModelSerializer):
    """支付方式序列化器"""
    user = serializers.ReadOnlyField(source='user.id')
    user_phone = serializers.ReadOnlyField(source='user.phone')
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'user', 'user_phone', 'pay_type', 'account', 'is_default', 'created_at']
        extra_kwargs = {
            'account': {'write_only': True}
        }

class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'phone', 'id_card', 'avatar', 'first_name', 'last_name', 'email',
                  'is_active', 'is_staff', 'is_superuser', 'payment_methods', 'created_at', 'updated_at']
        read_only_fields = ['is_active', 'is_staff', 'is_superuser']
        extra_kwargs = {
            'password': {'write_only': True},
            'phone': {'required': True},
            'avatar': {'required': False}
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data.get('username', validated_data['phone']),
            phone=validated_data['phone'],
            password=validated_data.get('password')
        )
        
        # 设置其他字段
        if 'id_card' in validated_data:
            user.id_card = validated_data['id_card']
        if 'avatar' in validated_data:
            user.avatar = validated_data['avatar']
        if 'first_name' in validated_data:
            user.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            user.last_name = validated_data['last_name']
        if 'email' in validated_data:
            user.email = validated_data['email']
        
        user.save()
        return user