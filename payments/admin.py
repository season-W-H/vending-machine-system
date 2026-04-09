from django.contrib import admin
from .models import PaymentRecord

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'record_no', 'order', 'get_pay_type_display', 'amount', 'get_status_display', 'created_at', 'pay_time')
    list_filter = ('status', 'pay_type', 'created_at', 'pay_time')
    search_fields = ('record_no', 'order__order_no', 'platform_trade_no')
    ordering = ('-created_at',)
    fieldsets = (
        ('支付基本信息', {'fields': ('record_no', 'order', 'pay_type', 'amount', 'status')}),
        ('第三方交易信息', {'fields': ('platform_trade_no', 'pay_time')}),
        ('时间信息', {'fields': ('created_at',)}),
    )
    readonly_fields = ('record_no', 'created_at')
    actions = ['mark_as_success', 'mark_as_failed']

    def mark_as_success(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=PaymentRecord.Status.PENDING).update(
            status=PaymentRecord.Status.SUCCESS,
            pay_time=timezone.now()
        )
        self.message_user(request, f"已标记 {updated} 个支付记录为支付成功")
    mark_as_success.short_description = "标记选中的支付为成功"

    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status=PaymentRecord.Status.PENDING).update(
            status=PaymentRecord.Status.FAILED
        )
        self.message_user(request, f"已标记 {updated} 个支付记录为支付失败")
    mark_as_failed.short_description = "标记选中的支付为失败"