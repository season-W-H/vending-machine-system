from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class User(AbstractUser):
    """扩展用户模型"""
    phone = models.CharField(_("手机号"), max_length=255, unique=True)
    id_card = models.CharField(_("身份证号"), max_length=255, blank=True, null=True)
    
    avatar = models.ImageField(_("头像"), upload_to="avatars/", blank=True, null=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)
    
    last_login_ip = models.GenericIPAddressField(_("最后登录IP"), blank=True, null=True)
    login_failed_count = models.PositiveIntegerField(_("登录失败次数"), default=0)
    is_locked = models.BooleanField(_("是否锁定"), default=False)
    locked_until = models.DateTimeField(_("锁定截止时间"), blank=True, null=True)

    class Meta:
        verbose_name = _("用户")
        verbose_name_plural = _("用户")

    def __str__(self):
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
