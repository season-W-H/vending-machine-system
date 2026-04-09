from rest_framework import serializers
from .models import PaymentRecord, RefundRecord, PaymentArchive

class PaymentRecordSerializer(serializers.ModelSerializer):
    """支付记录序列化器"""
    status_display = serializers.ReadOnlyField(source='get_status_display')
    pay_type_display = serializers.ReadOnlyField(source='get_pay_type_display')
    order_id = serializers.ReadOnlyField(source='order.id')
    order_total_amount = serializers.ReadOnlyField(source='order.total_amount')
    order_user_id = serializers.ReadOnlyField(source='order.user.id')
    order_user_phone = serializers.ReadOnlyField(source='order.user.phone')
    
    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'record_no', 'order', 'order_id', 'order_total_amount',
            'order_user_id', 'order_user_phone', 'pay_type', 'pay_type_display',
            'amount', 'status', 'status_display', 'platform_trade_no',
            'pay_time', 'created_at', 'archived'
        ]
        read_only_fields = [
            'id', 'record_no', 'order', 'order_id', 'order_total_amount',
            'order_user_id', 'order_user_phone', 'amount', 'status', 
            'status_display', 'platform_trade_no', 'pay_time', 'created_at', 'archived'
        ]
        
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("支付金额必须大于0")
        return value


class RefundRecordSerializer(serializers.ModelSerializer):
    """退款记录序列化器"""
    status_display = serializers.ReadOnlyField(source='get_status_display')
    payment_record_no = serializers.ReadOnlyField(source='payment.record_no')
    payment_amount = serializers.ReadOnlyField(source='payment.amount')
    payment_pay_type = serializers.ReadOnlyField(source='payment.get_pay_type_display')
    
    class Meta:
        model = RefundRecord
        fields = [
            'id', 'refund_no', 'payment', 'payment_record_no', 'payment_amount',
            'payment_pay_type', 'amount', 'reason', 'status', 'status_display',
            'platform_refund_no', 'refund_time', 'error_message', 'created_at'
        ]
        read_only_fields = [
            'id', 'refund_no', 'payment', 'payment_record_no', 'payment_amount',
            'payment_pay_type', 'status', 'status_display', 'platform_refund_no',
            'refund_time', 'error_message', 'created_at'
        ]
        
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("退款金额必须大于0")
        return value


class PaymentArchiveSerializer(serializers.ModelSerializer):
    """支付归档记录序列化器"""
    pay_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentArchive
        fields = [
            'id', 'original_record_id', 'record_no', 'order_no', 'pay_type',
            'pay_type_display', 'amount', 'status', 'status_display',
            'platform_trade_no', 'pay_time', 'created_at', 'archived_at'
        ]
        read_only_fields = [
            'id', 'original_record_id', 'record_no', 'order_no', 'pay_type',
            'pay_type_display', 'amount', 'status', 'status_display',
            'platform_trade_no', 'pay_time', 'created_at', 'archived_at'
        ]
    
    def get_pay_type_display(self, obj):
        """获取支付类型显示名称"""
        pay_type_map = {
            'alipay': '支付宝',
            'wechat': '微信支付'
        }
        return pay_type_map.get(obj.pay_type, obj.pay_type)
    
    def get_status_display(self, obj):
        """获取支付状态显示名称"""
        status_map = {
            'pending': '待支付',
            'success': '支付成功',
            'failed': '支付失败'
        }
        return status_map.get(obj.status, obj.status)


class CreatePaymentSerializer(serializers.Serializer):
    """创建支付订单序列化器"""
    order_id = serializers.IntegerField(required=True, help_text="订单ID")
    pay_type = serializers.ChoiceField(
        choices=['alipay', 'wechat'],
        required=True,
        help_text="支付类型：alipay-支付宝，wechat-微信支付"
    )
    
    def validate_order_id(self, value):
        """验证订单是否存在"""
        from orders.models import Order
        try:
            order = Order.objects.get(id=value)
            if order.status != Order.Status.PENDING:
                raise serializers.ValidationError("订单状态不允许支付")
            return order
        except Order.DoesNotExist:
            raise serializers.ValidationError("订单不存在")
    
    def validate(self, attrs):
        """验证支付金额"""
        order = attrs['order_id']
        if order.total_amount <= 0:
            raise serializers.ValidationError("订单金额必须大于0")
        return attrs


class RefundSerializer(serializers.Serializer):
    """退款序列化器"""
    payment_id = serializers.IntegerField(required=True, help_text="支付记录ID")
    refund_amount = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="退款金额（不填则全额退款）"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="退款原因"
    )
    
    def validate_payment_id(self, value):
        """验证支付记录是否存在"""
        try:
            payment = PaymentRecord.objects.get(id=value)
            if payment.status != PaymentRecord.Status.SUCCESS:
                raise serializers.ValidationError("只能对已支付的订单进行退款")
            return payment
        except PaymentRecord.DoesNotExist:
            raise serializers.ValidationError("支付记录不存在")
    
    def validate_refund_amount(self, value):
        """验证退款金额"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("退款金额必须大于0")
        return value


class PaymentStatusQuerySerializer(serializers.Serializer):
    """支付状态查询序列化器"""
    record_no = serializers.CharField(required=True, help_text="支付单号")


class ArchiveQuerySerializer(serializers.Serializer):
    """归档查询序列化器"""
    start_date = serializers.DateField(required=False, help_text="开始日期")
    end_date = serializers.DateField(required=False, help_text="结束日期")
    page = serializers.IntegerField(required=False, default=1, help_text="页码")
    page_size = serializers.IntegerField(required=False, default=20, help_text="每页数量")