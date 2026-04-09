import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

class PaymentRecord(models.Model):
    """支付记录模型"""
    class Status(models.TextChoices):
        PENDING = "pending", "待支付"
        SUCCESS = "success", "支付成功"
        FAILED = "failed", "支付失败"

    class PayType(models.TextChoices):
        ALIPAY = "alipay", "支付宝"
        WECHAT = "wechat", "微信支付"

    record_no = models.CharField("支付单号", max_length=32, unique=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="订单"
    )
    pay_type = models.CharField(
        "支付方式",
        max_length=20,
        choices=PayType.choices
    )
    amount = models.DecimalField("支付金额", max_digits=8, decimal_places=2)
    status = models.CharField(
        "支付状态",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    platform_trade_no = models.CharField("第三方交易号", max_length=100, blank=True)
    pay_time = models.DateTimeField("支付时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    archived = models.BooleanField("已归档", default=False)

    class Meta:
        verbose_name = "支付记录"
        verbose_name_plural = "支付记录"
        ordering = ["-created_at"]

    def __str__(self):
        return self.record_no

    def save(self, *args, **kwargs):
        if not self.record_no:
            # 生成支付单号
            self.record_no = f"PAY{uuid.uuid4().hex[:16].upper()}"
        super().save(*args, **kwargs)


class RefundRecord(models.Model):
    """退款记录模型"""
    class Status(models.TextChoices):
        PENDING = "pending", "退款中"
        SUCCESS = "success", "退款成功"
        FAILED = "failed", "退款失败"

    refund_no = models.CharField("退款单号", max_length=32, unique=True)
    payment = models.ForeignKey(
        PaymentRecord,
        on_delete=models.CASCADE,
        related_name="refunds",
        verbose_name="原支付记录"
    )
    amount = models.DecimalField("退款金额", max_digits=8, decimal_places=2)
    reason = models.TextField("退款原因", blank=True)
    status = models.CharField(
        "退款状态",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    platform_refund_no = models.CharField("第三方退款号", max_length=100, blank=True)
    refund_time = models.DateTimeField("退款时间", null=True, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "退款记录"
        verbose_name_plural = "退款记录"
        ordering = ["-created_at"]

    def __str__(self):
        return self.refund_no


class PaymentArchive(models.Model):
    """支付归档记录模型"""
    original_record_id = models.IntegerField("原记录ID")
    record_no = models.CharField("支付单号", max_length=32)
    order_no = models.CharField("订单号", max_length=32)
    pay_type = models.CharField("支付方式", max_length=20)
    amount = models.DecimalField("支付金额", max_digits=8, decimal_places=2)
    status = models.CharField("支付状态", max_length=20)
    platform_trade_no = models.CharField("第三方交易号", max_length=100, blank=True)
    pay_time = models.DateTimeField("支付时间", null=True, blank=True)
    created_at = models.DateTimeField("原创建时间")
    archived_at = models.DateTimeField("归档时间", auto_now_add=True)

    class Meta:
        verbose_name = "支付归档"
        verbose_name_plural = "支付归档"
        ordering = ["-archived_at"]

    def __str__(self):
        return f"{self.record_no} (归档)"