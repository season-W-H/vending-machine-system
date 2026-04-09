# -*- coding: utf-8 -*-
"""
自动识别流程模块

该模块实现从摄像头识别到订单创建、支付、库存管理的完整自动化流程。
支持实时识别、自动下单、支付确认、库存扣减等操作。
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

# 导入模型
from products.models import Product, VisualRecognitionRecord
from orders.models import Order, OrderItem
from payments.models import PaymentRecord
from inventory.models import Inventory

# 导入服务模块
from products.services.camera_handler import CameraHandler
from products.services.websocket_consumer import WebSocketManager
from products.services.object_recognition import get_recognizer

logger = logging.getLogger(__name__)


class AutoRecognitionFlow:
    """
    自动识别流程管理器
    """
    
    def __init__(self):
        self.camera_handler = None
        self.is_running = False
        self.flow_thread = None
        self.confidence_threshold = 0.7  # 识别置信度阈值
        self.auto_order_delay = 5  # 自动下单延迟（秒）
        self.max_items_per_order = 5  # 每个订单最大商品数量
        self.processed_items = set()  # 已处理的识别记录ID集合
        
        # WebSocket管理器
        self.websocket_manager = WebSocketManager()
    
    def start_flow(self) -> bool:
        """
        启动自动识别流程
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 初始化摄像头
            self.camera_handler = CameraHandler()
            if not self.camera_handler.start():
                logger.error("摄像头启动失败")
                return False
            
            # 设置运行状态
            self.is_running = True
            
            # 启动识别流程线程
            self.flow_thread = threading.Thread(target=self._recognition_flow_loop)
            self.flow_thread.daemon = True
            self.flow_thread.start()
            
            logger.info("自动识别流程启动成功")
            
            # 广播流程启动消息
            self.websocket_manager.broadcast_message({
                'type': 'flow_status',
                'status': 'started',
                'message': '自动识别流程已启动',
                'timestamp': datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"启动自动识别流程失败: {e}")
            return False
    
    def stop_flow(self):
        """
        停止自动识别流程
        """
        try:
            self.is_running = False
            
            # 停止摄像头
            if self.camera_handler:
                self.camera_handler.stop()
            
            # 等待线程结束
            if self.flow_thread:
                self.flow_thread.join(timeout=5.0)
            
            logger.info("自动识别流程已停止")
            
            # 广播流程停止消息
            self.websocket_manager.broadcast_message({
                'type': 'flow_status',
                'status': 'stopped',
                'message': '自动识别流程已停止',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"停止自动识别流程失败: {e}")
    
    def _recognition_flow_loop(self):
        """
        识别流程主循环
        """
        while self.is_running:
            try:
                # 获取识别结果
                recognition_results = self.camera_handler.get_recognition_result()
                
                # 处理每个识别结果
                for result in recognition_results:
                    self._process_recognition_result(result)
                
                # 等待一段时间再继续
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"识别流程循环出错: {e}")
                time.sleep(2)
    
    def _process_recognition_result(self, result: Dict):
        """
        处理单个识别结果
        
        Args:
            result: 识别结果字典
        """
        try:
            # 检查置信度
            confidence = result.get('confidence', 0)
            if confidence < self.confidence_threshold:
                logger.debug(f"识别置信度 {confidence:.2f} 低于阈值 {self.confidence_threshold}")
                return
            
            # 获取商品信息
            class_name = result.get('class_name')
            product = self._find_product_by_name(class_name)
            
            if not product:
                logger.warning(f"未找到匹配的商品: {class_name}")
                return
            
            # 检查是否已处理过这个识别结果
            if result.get('id') in self.processed_items:
                return
            
            # 创建识别记录
            recognition_record = self._create_recognition_record(result, product)
            self.processed_items.add(result.get('id'))
            
            # 广播识别结果
            self._broadcast_recognition_result(recognition_record, product)
            
            # 检查是否需要自动下单
            if self._should_auto_order(product, recognition_record):
                self._create_auto_order(product, recognition_record)
            
        except Exception as e:
            logger.error(f"处理识别结果时出错: {e}")
    
    def _find_product_by_name(self, class_name: str) -> Optional[Product]:
        """
        根据识别类别名查找匹配的商品
        
        Args:
            class_name: 识别类别名
            
        Returns:
            Optional[Product]: 匹配的商品，如果未找到则返回None
        """
        try:
            # 尝试通过商品名称精确匹配
            products = Product.objects.filter(name__icontains=class_name)
            
            if products.exists():
                return products.first()
            
            # 尝试通过商品类别匹配（如果有类别字段）
            # products = Product.objects.filter(category__name__icontains=class_name)
            # if products.exists():
            #     return products.first()
            
            logger.debug(f"未找到匹配的商品: {class_name}")
            return None
            
        except Exception as e:
            logger.error(f"查找商品时出错: {e}")
            return None
    
    def _create_recognition_record(self, result: Dict, product: Product) -> VisualRecognitionRecord:
        """
        创建识别记录
        
        Args:
            result: 识别结果
            product: 匹配的商品
            
        Returns:
            VisualRecognitionRecord: 创建的识别记录
        """
        try:
            recognition_record = VisualRecognitionRecord.objects.create(
                product=product,
                confidence_score=result.get('confidence', 0),
                detection_box=result.get('bbox'),
                image_path=result.get('image_path'),
                processing_time=result.get('processing_time', 0),
                algorithm_used='auto_flow'
            )
            
            logger.info(f"创建识别记录: {recognition_record.id}")
            return recognition_record
            
        except Exception as e:
            logger.error(f"创建识别记录时出错: {e}")
            raise
    
    def _broadcast_recognition_result(self, recognition_record: VisualRecognitionRecord, product: Product):
        """
        广播识别结果到WebSocket客户端
        
        Args:
            recognition_record: 识别记录
            product: 商品
        """
        try:
            result_data = {
                'recognition_id': recognition_record.id,
                'product_id': product.id,
                'product_name': product.name,
                'product_price': float(product.price),
                'confidence': float(recognition_record.confidence_score),
                'timestamp': recognition_record.created_at.isoformat(),
                'status': 'recognized'
            }
            
            self.websocket_manager.broadcast_recognition_result(result_data)
            
        except Exception as e:
            logger.error(f"广播识别结果时出错: {e}")
    
    def _should_auto_order(self, product: Product, recognition_record: VisualRecognitionRecord) -> bool:
        """
        检查是否需要自动下单
        
        Args:
            product: 商品
            recognition_record: 识别记录
            
        Returns:
            bool: 是否需要自动下单
        """
        try:
            # 检查库存
            inventory = getattr(product, 'inventory', None)
            if not inventory or inventory.current_stock <= 0:
                logger.warning(f"商品 {product.name} 库存不足")
                return False
            
            # 检查最近是否有相同商品的下单
            recent_orders = Order.objects.filter(
                items__product=product,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
            )
            
            if recent_orders.exists():
                logger.debug(f"最近1分钟内已有商品 {product.name} 的订单，跳过自动下单")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查自动下单条件时出错: {e}")
            return False
    
    def _create_auto_order(self, product: Product, recognition_record: VisualRecognitionRecord):
        """
        创建自动订单
        
        Args:
            product: 商品
            recognition_record: 识别记录
        """
        try:
            with transaction.atomic():
                # 创建订单
                order = Order.objects.create(
                    recognition_record=recognition_record,
                    total_amount=product.price,
                    status=Order.Status.PENDING
                )
                
                # 创建订单项
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=product.price,
                    quantity=1
                )
                
                logger.info(f"创建自动订单: {order.order_no}")
                
                # 广播订单创建消息
                self._broadcast_order_created(order, order_item)
                
                # 延迟执行支付处理
                threading.Timer(
                    self.auto_order_delay,
                    self._process_payment,
                    args=[order.id]
                ).start()
                
        except Exception as e:
            logger.error(f"创建自动订单时出错: {e}")
    
    def _broadcast_order_created(self, order: Order, order_item: OrderItem):
        """
        广播订单创建消息
        
        Args:
            order: 订单
            order_item: 订单项
        """
        try:
            order_data = {
                'order_id': order.id,
                'order_no': order.order_no,
                'product_name': order_item.product_name,
                'product_price': float(order_item.price),
                'quantity': order_item.quantity,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'auto_created': True
            }
            
            self.websocket_manager.broadcast_message({
                'type': 'order_created',
                'data': order_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"广播订单创建消息时出错: {e}")
    
    def _process_payment(self, order_id: int):
        """
        处理支付
        
        Args:
            order_id: 订单ID
        """
        try:
            order = Order.objects.get(id=order_id)
            
            # 创建支付记录
            payment = PaymentRecord.objects.create(
                order=order,
                pay_type=PaymentRecord.PayType.ALIPAY,
                amount=order.total_amount,
                status=PaymentRecord.Status.SUCCESS,  # 自动模拟支付成功
                pay_time=timezone.now()
            )
            
            # 更新订单状态
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save()
            
            logger.info(f"订单 {order.order_no} 支付完成")
            
            # 广播支付完成消息
            self.websocket_manager.broadcast_message({
                'type': 'payment_completed',
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': float(order.total_amount),
                'payment_id': payment.id,
                'timestamp': datetime.now().isoformat()
            })
            
            # 延迟执行库存扣减
            threading.Timer(
                2,
                self._process_inventory_update,
                args=[order.id]
            ).start()
            
        except Order.DoesNotExist:
            logger.error(f"订单不存在: {order_id}")
        except Exception as e:
            logger.error(f"处理支付时出错: {e}")
    
    def _process_inventory_update(self, order_id: int):
        """
        处理库存扣减
        
        Args:
            order_id: 订单ID
        """
        try:
            order = Order.objects.get(id=order_id)
            
            with transaction.atomic():
                for item in order.items.all():
                    if hasattr(item.product, 'inventory'):
                        inventory = item.product.inventory
                        if inventory.current_stock >= item.quantity:
                            inventory.current_stock -= item.quantity
                            inventory.save()
                            
                            logger.info(f"库存扣减: {item.product.name} - {item.quantity}件")
                            
                            # 检查是否需要预警
                            if inventory.is_low_stock():
                                self._broadcast_low_stock_alert(inventory)
                        else:
                            logger.warning(f"库存不足: {item.product.name}")
                
                # 更新订单状态为已完成
                order.status = Order.Status.COMPLETED
                order.completed_at = timezone.now()
                order.save()
                
                logger.info(f"订单 {order.order_no} 已完成")
                
                # 广播订单完成和库存更新消息
                self._broadcast_order_completed(order)
                self._broadcast_inventory_updates(order)
                
        except Order.DoesNotExist:
            logger.error(f"订单不存在: {order_id}")
        except Exception as e:
            logger.error(f"处理库存更新时出错: {e}")
    
    def _broadcast_low_stock_alert(self, inventory: Inventory):
        """
        广播库存预警
        
        Args:
            inventory: 库存对象
        """
        try:
            self.websocket_manager.broadcast_message({
                'type': 'low_stock_alert',
                'product_name': inventory.product.name,
                'current_stock': inventory.current_stock,
                'alarm_threshold': inventory.alarm_threshold,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"广播库存预警时出错: {e}")
    
    def _broadcast_order_completed(self, order: Order):
        """
        广播订单完成消息
        
        Args:
            order: 订单
        """
        try:
            self.websocket_manager.broadcast_message({
                'type': 'order_completed',
                'order_id': order.id,
                'order_no': order.order_no,
                'total_amount': float(order.total_amount),
                'completed_at': order.completed_at.isoformat(),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"广播订单完成消息时出错: {e}")
    
    def _broadcast_inventory_updates(self, order: Order):
        """
        广播库存更新消息
        
        Args:
            order: 订单
        """
        try:
            inventory_data = []
            for item in order.items.all():
                if hasattr(item.product, 'inventory'):
                    inventory = item.product.inventory
                    inventory_data.append({
                        'product_id': item.product.id,
                        'product_name': item.product.name,
                        'current_stock': inventory.current_stock,
                        'is_low_stock': inventory.is_low_stock()
                    })
            
            self.websocket_manager.broadcast_message({
                'type': 'inventory_update',
                'items': inventory_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"广播库存更新消息时出错: {e}")
    
    def get_flow_status(self) -> Dict:
        """
        获取流程状态
        
        Returns:
            Dict: 流程状态信息
        """
        return {
            'is_running': self.is_running,
            'camera_running': self.camera_handler.is_running if self.camera_handler else False,
            'confidence_threshold': self.confidence_threshold,
            'auto_order_delay': self.auto_order_delay,
            'processed_items_count': len(self.processed_items),
            'last_updated': datetime.now().isoformat()
        }


# 全局自动识别流程实例
auto_flow = AutoRecognitionFlow()