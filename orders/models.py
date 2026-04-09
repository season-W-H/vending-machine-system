# -*- coding: utf-8 -*-
"""
订单模块模型定义

定义订单相关的数据库模型，包括订单主表和订单项。
"""

import uuid
import logging
from datetime import datetime
from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# 配置日志
logger = logging.getLogger(__name__)

class Order(models.Model):
    """订单模型"""
    class Status(models.TextChoices):
        PENDING = "pending", "待确认"
        CONFIRMED = "confirmed", "已确认"
        PAID = "paid", "已支付"
        COMPLETED = "completed", "已完成"
        CANCELLED = "cancelled", "已取消"

    order_no = models.CharField("订单编号", max_length=32, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name="用户"
    )
    recognition_record = models.ForeignKey(
        "products.VisualRecognitionRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="识别记录"
    )
    total_amount = models.DecimalField("总金额", max_digits=8, decimal_places=2)
    status = models.CharField(
        "订单状态",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    confirmed_at = models.DateTimeField("确认时间", null=True, blank=True)
    paid_at = models.DateTimeField("支付时间", null=True, blank=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    cancelled_at = models.DateTimeField("取消时间", null=True, blank=True)

    class Meta:
        verbose_name = "订单"
        verbose_name_plural = "订单"
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_no

    def save(self, *args, **kwargs):
        if not self.order_no:
            # 生成订单编号：VM + 日期 + 随机字符串
            import datetime
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            random_str = uuid.uuid4().hex[:8].upper()
            self.order_no = f"VM{date_str}{random_str}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """订单项模型"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="订单"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="商品"
    )
    product_name = models.CharField("商品名称", max_length=100)
    price = models.DecimalField("购买单价", max_digits=6, decimal_places=2)
    quantity = models.PositiveIntegerField("数量", default=1)

    class Meta:
        verbose_name = "订单项"
        verbose_name_plural = "订单项"

    def __str__(self):
        return f"{self.order.order_no} - {self.product_name}"

    @property
    def total_price(self):
        return self.price * self.quantity


@receiver(post_save, sender=Order)
def update_statistics_when_order_completed(sender, instance, created, **kwargs):
    """
    订单完成时自动更新统计数据并广播
    """
    # 检查订单是否刚被更新为已完成状态
    if not created and instance.status == Order.Status.COMPLETED:
        try:
            # 导入统计服务
            from .services.statistics_service import StatisticsService
            
            # 更新并广播统计数据
            StatisticsService.update_statistics_on_order_complete(instance)
            
            logger.info(f"订单 {instance.order_no} 完成，统计数据已更新并广播")
        except Exception as e:
            logger.error(f"更新统计数据时出错: {str(e)}", exc_info=True)
