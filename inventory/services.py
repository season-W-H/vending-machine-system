from django.db import transaction
from django.db.models import F
from products.models import Product

class InventoryService:
    """库存管理服务"""
    
    @staticmethod
    @transaction.atomic
    def lock_inventory(product_items):
        """
        锁定商品库存
        :param product_items: 商品列表，格式: [{'product_id': 1, 'quantity': 2}, ...]
        :return: 成功返回True，失败返回错误信息
        """
        for item in product_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            # 使用select_for_update获取行锁，防止并发问题
            try:
                product = Product.objects.select_for_update().get(
                    id=product_id, 
                    is_active=True
                )
            except Product.DoesNotExist:
                transaction.set_rollback(True)
                return {'success': False, 'error': f"商品ID {product_id} 不存在或已下架"}
            
            # 检查库存是否充足
            if product.stock < quantity:
                transaction.set_rollback(True)
                return {
                    'success': False, 
                    'error': f"{product.name} 库存不足，当前库存: {product.stock}, 请求: {quantity}"
                }
            
            # 锁定库存
            product.locked_stock = F('locked_stock') + quantity
            product.save()
        
        return {'success': True}
    
    @staticmethod
    @transaction.atomic
    def release_inventory(product_items):
        """
        释放锁定的库存
        :param product_items: 商品列表，格式同上
        """
        for item in product_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            try:
                product = Product.objects.select_for_update().get(id=product_id)
                # 减少锁定库存，不能小于0
                new_locked = max(0, product.locked_stock - quantity)
                product.locked_stock = new_locked
                product.save()
            except Product.DoesNotExist:
                continue  # 商品不存在则忽略
    
    @staticmethod
    @transaction.atomic
    def deduct_inventory(product_items):
        """
        扣减实际库存（从锁定库存中扣减）
        :param product_items: 商品列表，格式同上
        """
        for item in product_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            try:
                product = Product.objects.select_for_update().get(id=product_id)
                # 扣减实际库存并释放锁定库存
                product.stock = F('stock') - quantity
                product.locked_stock = F('locked_stock') - quantity
                product.save()
            except Product.DoesNotExist:
                continue
