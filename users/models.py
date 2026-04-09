from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class EncryptedField(models.CharField):
    """加密字段 - 使用Fernet对称加密"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = None
    
    def get_fernet(self):
        """获取Fernet实例"""
        if self._fernet is None:
            # 从SECRET_KEY生成加密密钥
            import hashlib
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(key)
            self._fernet = Fernet(key)
        return self._fernet
    
    def get_prep_value(self, value):
        """保存前加密"""
        if value is None or value == '':
            return value
        try:
            fernet = self.get_fernet()
            encrypted = fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception:
            return value
    
    def from_db_value(self, value, expression, connection):
        """从数据库读取后解密"""
        if value is None or value == '':
            return value
        try:
            fernet = self.get_fernet()
            decrypted = fernet.decrypt(value.encode())
            return decrypted.decode()
        except Exception:
            return value
    
    def to_python(self, value):
        """转换为Python对象"""
        if value is None or value == '':
            return value
        if isinstance(value, str):
            # 检查是否已加密（Fernet加密后的字符串以gAAAA开头）
            if value.startswith('gAAAA'):
                try:
                    fernet = self.get_fernet()
                    decrypted = fernet.decrypt(value.encode())
                    return decrypted.decode()
                except Exception:
                    pass
        return value


class User(AbstractUser):
    """扩展用户模型 - 敏感信息加密存储"""
    # 敏感信息使用加密字段
    phone = EncryptedField(_("手机号"), max_length=255, unique=True)
    id_card = EncryptedField(_("身份证号"), max_length=255, blank=True, null=True)
    
    # 非敏感信息
    avatar = models.ImageField(_("头像"), upload_to="avatars/", blank=True, null=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)
    
    # 安全相关字段
    last_login_ip = models.GenericIPAddressField(_("最后登录IP"), blank=True, null=True)
    login_failed_count = models.PositiveIntegerField(_("登录失败次数"), default=0)
    is_locked = models.BooleanField(_("是否锁定"), default=False)
    locked_until = models.DateTimeField(_("锁定截止时间"), blank=True, null=True)

    class Meta:
        verbose_name = _("用户")
        verbose_name_plural = _("用户")

    def __str__(self):
        # 解密后显示
        return self.phone or self.username
    
    def increment_login_failed(self):
        """增加登录失败次数"""
        self.login_failed_count += 1
        if self.login_failed_count >= 5:
            from django.utils import timezone
            from datetime import timedelta
            self.is_locked = True
            self.locked_until = timezone.now() + timedelta(minutes=30)
        self.save(update_fields=['login_failed_count', 'is_locked', 'locked_until'])
    
    def reset_login_failed(self):
        """重置登录失败次数"""
        self.login_failed_count = 0
        self.is_locked = False
        self.locked_until = None
        self.save(update_fields=['login_failed_count', 'is_locked', 'locked_until'])
    
    def is_account_locked(self):
        """检查账户是否被锁定"""
        if not self.is_locked:
            return False
        from django.utils import timezone
        if self.locked_until and self.locked_until < timezone.now():
            # 锁定时间已过，自动解锁
            self.reset_login_failed()
            return False
        return True


class PaymentMethod(models.Model):
    """支付方式模型 - 敏感信息加密存储"""
    class PayType(models.TextChoices):
        ALIPAY = "alipay", _("支付宝")
        WECHAT = "wechat", _("微信支付")

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="payment_methods",
        verbose_name=_("用户")
    )
    pay_type = models.CharField(
        _("支付类型"), 
        max_length=20, 
        choices=PayType.choices,
        default=PayType.ALIPAY
    )
    # 支付账号加密存储
    account = EncryptedField(_("账号标识"), max_length=255)
    # 支付账号掩码（用于显示）
    account_mask = models.CharField(_("账号掩码"), max_length=100, blank=True)
    is_default = models.BooleanField(_("是否默认"), default=False)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("支付方式")
        verbose_name_plural = _("支付方式")
        unique_together = ("user", "pay_type", "account")

    def __str__(self):
        return f"{self.get_pay_type_display()} ({self.account_mask})"
    
    def save(self, *args, **kwargs):
        # 自动生成账号掩码
        if self.account and not self.account_mask:
            self.account_mask = self._mask_account(self.account)
        super().save(*args, **kwargs)
    
    def _mask_account(self, account):
        """生成账号掩码"""
        account_str = str(account)
        if len(account_str) <= 4:
            return "****"
        return account_str[:2] + "****" + account_str[-2:]


class SecurityAuditLog(models.Model):
    """安全审计日志"""
    class ActionType(models.TextChoices):
        LOGIN = "login", _("登录")
        LOGIN_FAILED = "login_failed", _("登录失败")
        LOGOUT = "logout", _("登出")
        PASSWORD_CHANGE = "password_change", _("密码修改")
        PAYMENT = "payment", _("支付")
        REFUND = "refund", _("退款")
        DATA_EXPORT = "data_export", _("数据导出")
        SENSITIVE_OPERATION = "sensitive_operation", _("敏感操作")
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("用户")
    )
    action = models.CharField(_("操作类型"), max_length=50, choices=ActionType.choices)
    ip_address = models.GenericIPAddressField(_("IP地址"), blank=True, null=True)
    user_agent = models.TextField(_("用户代理"), blank=True)
    details = models.JSONField(_("详细信息"), default=dict, blank=True)
    timestamp = models.DateTimeField(_("时间戳"), auto_now_add=True)
    is_suspicious = models.BooleanField(_("是否可疑"), default=False)
    risk_level = models.CharField(_("风险等级"), max_length=20, default="low")

    class Meta:
        verbose_name = _("安全审计日志")
        verbose_name_plural = _("安全审计日志")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['is_suspicious']),
        ]

    def __str__(self):
        return f"{self.action} - {self.user} - {self.timestamp}"


class LoginAttempt(models.Model):
    """登录尝试记录 - 用于防暴力破解"""
    ip_address = models.GenericIPAddressField(_("IP地址"))
    username = models.CharField(_("用户名"), max_length=150, blank=True)
    attempted_at = models.DateTimeField(_("尝试时间"), auto_now_add=True)
    is_successful = models.BooleanField(_("是否成功"), default=False)
    user_agent = models.TextField(_("用户代理"), blank=True)
    
    class Meta:
        verbose_name = _("登录尝试")
        verbose_name_plural = _("登录尝试")
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['ip_address', 'attempted_at']),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.username} - {self.attempted_at}"
