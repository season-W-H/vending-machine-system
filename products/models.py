import uuid
from django.db import models

class Product(models.Model):
    """商品模型"""
    name = models.CharField("商品名称", max_length=100)
    description = models.TextField("商品描述", blank=True)
    category = models.CharField("商品分类", max_length=50, blank=True, help_text="例如：Drink、Snack")
    price = models.DecimalField("单价", max_digits=6, decimal_places=2)
    stock = models.PositiveIntegerField("实际库存", default=0)
    locked_stock = models.PositiveIntegerField("锁定库存", default=0)
    location = models.CharField("货道位置", max_length=20, help_text="例如：A1、B3")
    image = models.ImageField("商品图片", upload_to="products/")
    is_active = models.BooleanField("是否在售", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ["location"]

    def __str__(self):
        return f"{self.name}（{self.location}）"

class VisualRecognitionRecord(models.Model):
    """视觉识别记录"""
    class Status(models.TextChoices):
        PENDING = "pending", "识别中"
        SUCCESS = "success", "识别成功"
        FAILED = "failed", "识别失败"

    record_id = models.UUIDField(
        "记录ID", 
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    image_path = models.CharField("图像路径", max_length=255)
    algorithm_used = models.CharField("使用算法", max_length=50)
    recognition_result = models.JSONField("识别结果", null=True)
    status = models.CharField(
        "识别状态", 
        max_length=20, 
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField("识别时间", auto_now_add=True)

    class Meta:
        verbose_name = "视觉识别记录"
        verbose_name_plural = "视觉识别记录"

    def __str__(self):
        return f"{self.record_id}（{self.get_status_display()}）"


class StockOperation(models.Model):
    """库存操作记录"""
    class OperationType(models.TextChoices):
        ADD = "add", "添加库存"
        SUBTRACT = "subtract", "减少库存"
        SET = "set", "设置库存"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="商品",
        related_name="stock_operations"
    )
    operation_type = models.CharField(
        "操作类型",
        max_length=20,
        choices=OperationType.choices
    )
    quantity = models.PositiveIntegerField("操作数量")
    reason = models.TextField("操作原因", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "库存操作记录"
        verbose_name_plural = "库存操作记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.product.name}（{self.quantity}）"

    def save(self, *args, **kwargs):
        """保存时更新商品库存"""
        # 先调用父类保存
        super().save(*args, **kwargs)
        
        # 更新商品库存
        if self.operation_type == self.OperationType.ADD:
            self.product.stock += self.quantity
        elif self.operation_type == self.OperationType.SUBTRACT:
            self.product.stock = max(0, self.product.stock - self.quantity)
        elif self.operation_type == self.OperationType.SET:
            self.product.stock = self.quantity
        
        self.product.save()
