from django.contrib import admin
from .models import User, PaymentMethod

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'phone', 'email', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'phone', 'email', 'id_card')
    ordering = ('-created_at',)
    fieldsets = (
        ('基本信息', {'fields': ('username', 'phone', 'email', 'password')}),
        ('个人资料', {'fields': ('first_name', 'last_name', 'avatar', 'id_card')}),
        ('权限设置', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('日期信息', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('用户组与权限', {'fields': ('groups', 'user_permissions')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_pay_type_display', 'account', 'is_default', 'created_at')
    list_filter = ('pay_type', 'is_default', 'created_at')
    search_fields = ('user__phone', 'account')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)