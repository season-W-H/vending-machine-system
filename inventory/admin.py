from django.contrib import admin
from .models import Inventory

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'current_stock', 'alarm_threshold', 'is_low_stock', 'last_checked', 'updated_at')
    list_filter = ('last_checked', 'updated_at')
    search_fields = ('product__name', 'product__location')
    ordering = ('product__location',)
    fieldsets = (
        ('商品信息', {'fields': ('product',)}),
        ('库存信息', {'fields': ('current_stock', 'alarm_threshold', 'last_checked')}),
        ('更新时间', {'fields': ('updated_at',)}),
    )
    readonly_fields = ('updated_at',)
    actions = ['check_inventory']

    def check_inventory(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(last_checked=timezone.now())
        self.message_user(request, f"已完成 {updated} 个商品的库存盘点")
    check_inventory.short_description = "盘点选中的库存"