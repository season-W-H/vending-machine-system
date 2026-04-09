from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity', 'total_price')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_no', 'user', 'total_amount', 'get_status_display', 'created_at', 'paid_at', 'completed_at')
    list_filter = ('status', 'created_at', 'paid_at', 'completed_at')
    search_fields = ('order_no', 'user__phone', 'user__username')
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    fieldsets = (
        ('订单基本信息', {'fields': ('order_no', 'user', 'total_amount', 'status')}),
        ('订单时间线', {'fields': ('created_at', 'confirmed_at', 'paid_at', 'completed_at', 'cancelled_at')}),
        ('识别记录', {'fields': ('recognition_record',)}),
    )
    readonly_fields = ('order_no', 'created_at', 'confirmed_at', 'paid_at', 'completed_at', 'cancelled_at')
    actions = ['confirm_order', 'mark_as_paid', 'complete_order', 'cancel_order']

    def confirm_order(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Order.Status.PENDING).update(
            status=Order.Status.CONFIRMED,
            confirmed_at=timezone.now()
        )
        self.message_user(request, f"已确认 {updated} 个订单")
    confirm_order.short_description = "确认选中的订单"

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Order.Status.CONFIRMED).update(
            status=Order.Status.PAID,
            paid_at=timezone.now()
        )
        self.message_user(request, f"已标记 {updated} 个订单为已支付")
    mark_as_paid.short_description = "标记选中的订单为已支付"

    def complete_order(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Order.Status.PAID).update(
            status=Order.Status.COMPLETED,
            completed_at=timezone.now()
        )
        self.message_user(request, f"已完成 {updated} 个订单")
    complete_order.short_description = "完成选中的订单"

    def cancel_order(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=[Order.Status.PENDING, Order.Status.CONFIRMED]).update(
            status=Order.Status.CANCELLED,
            cancelled_at=timezone.now()
        )
        self.message_user(request, f"已取消 {updated} 个订单")
    cancel_order.short_description = "取消选中的订单"