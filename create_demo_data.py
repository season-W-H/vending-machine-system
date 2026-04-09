#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建演示数据脚本
用于为比赛项目准备示例数据
"""

import os
import django
from django.utils import timezone
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vending_machine.settings')
django.setup()

from products.models import Product, StockOperation
from orders.models import Order, OrderItem
from users.models import User

def create_demo_products():
    """创建演示商品数据"""
    print("正在创建演示商品...")
    
    products_data = [
        {"name": "百岁山矿泉水", "category": "饮料", "price": 3.00, "stock": 50, "location": "A1"},
        {"name": "芬达橙味", "category": "饮料", "price": 3.50, "stock": 45, "location": "A2"},
        {"name": "加多宝凉茶", "category": "饮料", "price": 4.00, "stock": 40, "location": "A3"},
        {"name": "康师傅红茶", "category": "饮料", "price": 3.00, "stock": 35, "location": "A4"},
        {"name": "维他命水", "category": "饮料", "price": 5.00, "stock": 30, "location": "B1"},
        {"name": "脉动", "category": "饮料", "price": 4.50, "stock": 25, "location": "B2"},
        {"name": "美之源果粒橙", "category": "饮料", "price": 4.00, "stock": 20, "location": "B3"},
        {"name": "统一阿萨姆绿茶", "category": "饮料", "price": 4.00, "stock": 15, "location": "B4"},
        {"name": "统一阿萨姆红茶", "category": "饮料", "price": 4.00, "stock": 10, "location": "C1"},
        {"name": "营养快线", "category": "饮料", "price": 5.00, "stock": 5, "location": "C2"},
    ]
    
    created_count = 0
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            name=product_data["name"],
            defaults=product_data
        )
        if created:
            created_count += 1
            print(f"  - 创建商品: {product.name}")
    
    print(f"共创建 {created_count} 个商品\n")
    return Product.objects.all()

def create_demo_orders(products):
    """创建演示订单数据"""
    print("正在创建演示订单...")
    
    # 创建一个测试用户
    user, _ = User.objects.get_or_create(
        username="demo_user",
        defaults={
            "phone": "13800138000",
            "is_superuser": False,
            "is_staff": False
        }
    )
    
    # 生成最近30天的订单
    today = timezone.now()
    created_count = 0
    
    for i in range(30):
        order_date = today - timedelta(days=i)
        
        # 每天随机生成1-5个订单
        num_orders = random.randint(1, 5)
        
        for j in range(num_orders):
            # 随机选择1-3个商品
            num_items = random.randint(1, 3)
            selected_products = random.sample(list(products), num_items)
            
            total_amount = 0
            items_data = []
            
            for product in selected_products:
                quantity = random.randint(1, 2)
                item_total = product.price * quantity
                total_amount += item_total
                items_data.append({
                    "product": product,
                    "quantity": quantity,
                    "price": product.price
                })
            
            # 随机选择订单状态
            statuses = [Order.Status.COMPLETED, Order.Status.COMPLETED, Order.Status.COMPLETED, 
                       Order.Status.PAID, Order.Status.CANCELLED]
            status = random.choice(statuses)
            
            # 创建订单
            order = Order.objects.create(
                user=user,
                total_amount=total_amount,
                status=status,
                created_at=order_date + timedelta(hours=random.randint(8, 22))
            )
            
            if status == Order.Status.CONFIRMED:
                order.confirmed_at = order.created_at
            elif status == Order.Status.PAID:
                order.confirmed_at = order.created_at
                order.paid_at = order.created_at + timedelta(minutes=random.randint(1, 5))
            elif status == Order.Status.COMPLETED:
                order.confirmed_at = order.created_at
                order.paid_at = order.created_at + timedelta(minutes=random.randint(1, 5))
                order.completed_at = order.paid_at + timedelta(seconds=random.randint(30, 60))
            elif status == Order.Status.CANCELLED:
                order.cancelled_at = order.created_at + timedelta(minutes=random.randint(5, 30))
            
            order.save()
            
            # 创建订单项
            for item_data in items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item_data["product"],
                    product_name=item_data["product"].name,
                    price=item_data["price"],
                    quantity=item_data["quantity"]
                )
            
            created_count += 1
            if created_count % 10 == 0:
                print(f"  - 已创建 {created_count} 个订单...")
    
    print(f"共创建 {created_count} 个演示订单\n")

def main():
    print("=" * 50)
    print("无人零售智能结算系统 - 演示数据创建")
    print("=" * 50 + "\n")
    
    products = create_demo_products()
    create_demo_orders(products)
    
    print("=" * 50)
    print("演示数据创建完成！")
    print("=" * 50)
    print("\n您可以通过以下方式访问系统：")
    print("  - 首页: http://localhost:8000/")
    print("  - 管理后台: http://localhost:8000/admin-dashboard/")
    print("  - 工作界面: http://localhost:8000/workspace/")
    print("\n提示: 如需创建管理员账户，请运行: python manage.py createsuperuser")

if __name__ == "__main__":
    main()
