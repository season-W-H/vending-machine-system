# -*- coding: utf-8 -*-
"""
订单统计服务模块

该模块负责实时计算和更新销售额、订单数量等统计信息，并通过WebSocket广播给前端。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from django.db.models import Sum, Count
from django.db import models
from asgiref.sync import async_to_sync

# 导入模型
from orders.models import Order, OrderItem
from products.services.websocket_consumer import websocket_manager

# 配置日志
logger = logging.getLogger(__name__)


class StatisticsService:
    """
    订单统计服务类
    负责计算和广播销售统计数据
    """
    
    @classmethod
    def get_sales_statistics(cls) -> Dict[str, Any]:
        """
        获取销售统计数据
        
        Returns:
            Dict: 包含销售额、订单数等统计信息的字典
        """
        try:
            # 获取今日开始时间
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 计算今日销售额
            today_sales = Order.objects.filter(
                status=Order.Status.COMPLETED,
                created_at__gte=today
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # 计算今日订单数
            today_orders = Order.objects.filter(
                status=Order.Status.COMPLETED,
                created_at__gte=today
            ).count()
            
            # 计算总销售额
            total_sales = Order.objects.filter(
                status=Order.Status.COMPLETED
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # 计算总订单数
            total_orders = Order.objects.filter(
                status=Order.Status.COMPLETED
            ).count()
            
            # 计算最近热销商品
            hot_products = OrderItem.objects.filter(
                order__status=Order.Status.COMPLETED,
                order__created_at__gte=today
            ).values('product_name').annotate(
                total_quantity=Sum('quantity'),
                total_sales=Sum(models.F('price') * models.F('quantity'))
            ).order_by('-total_quantity')[:5]
            
            # 计算各商品类别销售情况（如果有类别字段）
            # category_sales = OrderItem.objects.filter(
            #     order__status=Order.Status.COMPLETED,
            #     order__created_at__gte=today
            # ).values('product__category__name').annotate(
            #     total_sales=Sum(models.F('price') * models.F('quantity'))
            # ).order_by('-total_sales')
            
            # 构建统计数据
            statistics = {
                'today_sales': float(today_sales),
                'today_orders': today_orders,
                'total_sales': float(total_sales),
                'total_orders': total_orders,
                'hot_products': [
                {
                    'name': item['product_name'],
                    'quantity': item['total_quantity'],
                    'total_sales': float(item['total_sales'])
                }
                for item in hot_products
            ],
                # 'category_sales': [
                #     {
                #         'category': item['product__category__name'],
                #         'total_sales': float(item['total_sales'])
                #     }
                #     for item in category_sales
                # ],
                'last_updated': datetime.now().isoformat()
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取销售统计数据时出错: {e}")
            return {
                'today_sales': 0,
                'today_orders': 0,
                'total_sales': 0,
                'total_orders': 0,
                'hot_products': [],
                # 'category_sales': [],
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }
    
    @classmethod
    def broadcast_statistics_update(cls):
        """
        广播统计数据更新到WebSocket客户端
        """
        try:
            # 获取最新统计数据
            statistics = cls.get_sales_statistics()
            
            # 导入便捷函数
            from products.services.websocket_consumer import broadcast_statistics_update
            
            # 使用便捷函数广播统计数据
            broadcast_statistics_update(statistics)
            
        except Exception as e:
            logger.error(f"广播统计数据更新时出错: {e}")
    
    @classmethod
    def update_statistics_on_order_complete(cls, order: Order):
        """
        订单完成后更新统计数据并广播
        
        Args:
            order: 已完成的订单
        """
        try:
            if order.status == Order.Status.COMPLETED:
                logger.info(f"订单 {order.order_no} 已完成，触发统计数据更新")
                cls.broadcast_statistics_update()
        except Exception as e:
            logger.error(f"订单完成后更新统计数据时出错: {e}")
    
    @classmethod
    def get_realtime_sales_data(cls) -> Dict[str, Any]:
        """
        获取实时销售数据（用于实时更新）
        
        Returns:
            Dict: 简化的实时销售数据
        """
        try:
            # 获取最新的订单数据
            latest_order = Order.objects.filter(
                status=Order.Status.COMPLETED
            ).order_by('-created_at').first()
            
            # 获取基本统计数据
            base_statistics = cls.get_sales_statistics()
            
            # 构建实时数据
            realtime_data = {
                'today_sales': base_statistics['today_sales'],
                'today_orders': base_statistics['today_orders'],
                'total_sales': base_statistics['total_sales'],
                'total_orders': base_statistics['total_orders'],
                'last_updated': datetime.now().isoformat()
            }
            
            # 如果有最新订单，添加订单详情
            if latest_order:
                realtime_data['latest_order'] = {
                    'order_no': latest_order.order_no,
                    'total_amount': float(latest_order.total_amount),
                    'created_at': latest_order.created_at.isoformat(),
                    'items_count': latest_order.items.count()
                }
            
            return realtime_data
            
        except Exception as e:
            logger.error(f"获取实时销售数据时出错: {e}")
            return {
                'today_sales': 0,
                'today_orders': 0,
                'total_sales': 0,
                'total_orders': 0,
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }
