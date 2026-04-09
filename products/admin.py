from django.contrib import admin
from .models import Product, VisualRecognitionRecord

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'stock', 'locked_stock', 'location', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'location')
    ordering = ('location', '-created_at')
    list_editable = ('is_active',)
    prepopulated_fields = {'location': ('name',)}
    fieldsets = (
        ('基本信息', {'fields': ('name', 'description', 'price', 'location')}),
        ('库存信息', {'fields': ('stock', 'locked_stock')}),
        ('状态与图片', {'fields': ('image', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(VisualRecognitionRecord)
class VisualRecognitionRecordAdmin(admin.ModelAdmin):
    list_display = ('record_id', 'algorithm_used', 'get_status_display', 'created_at')
    list_filter = ('status', 'algorithm_used', 'created_at')
    search_fields = ('record_id', 'image_path')
    ordering = ('-created_at',)
    fieldsets = (
        ('记录信息', {'fields': ('record_id', 'algorithm_used', 'status')}),
        ('识别结果', {'fields': ('recognition_result', 'image_path')}),
        ('时间信息', {'fields': ('created_at',)}),
    )
    readonly_fields = ('record_id', 'created_at')