from django.db import models
from django.utils import timezone
from products.models import Product

class Inventory(models.Model):
    """库存模型"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory",
        verbose_name="商品"
    )
    current_stock = models.PositiveIntegerField("当前库存", default=0)
    alarm_threshold = models.PositiveIntegerField("预警阈值", default=5)
    last_checked = models.DateTimeField("最后盘点时间", null=True, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    
    class Meta:
        verbose_name = "库存"
        verbose_name_plural = "库存"
    
    def __str__(self):
        return f"{self.product.name} - 库存: {self.current_stock}"
    
    def is_low_stock(self):
        """检查是否库存不足"""
        return self.current_stock <= self.alarm_threshold