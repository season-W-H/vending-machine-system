# -*- coding: utf-8 -*-
"""
物体识别服务模块

该模块负责识别图像中的商品，支持多种识别算法。
集成了深度学习模型和传统图像处理算法。
"""

import cv2
import numpy as np
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
import threading
import logging
import os

# 导入Django相关模块
from django.db import transaction
from django.conf import settings
from asgiref.sync import async_to_sync

# 导入深度学习识别器
from products.yolov8_integration import yolov8_recognition
from products.paddle_det_integration import paddle_det_recognition
from .websocket_consumer import (
    broadcast_recognition_result,
    broadcast_performance_update,
    websocket_manager
)

# 导入模型
from products.models import Product, VisualRecognitionRecord
from orders.models import Order, OrderItem

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObjectRecognition:
    """
    物体识别器类，负责识别图像中的商品
    """
    
    def __init__(self):
        """
        初始化物体识别器
        """
        self.yolov8_recognizer = yolov8_recognition
        self.paddle_det_recognizer = paddle_det_recognition
        self.is_initialized = True
        
        # 识别算法配置
        self.use_deep_learning = True  # 优先使用深度学习
        self.use_paddle_det = False  # 使用 YOLOv8 模型，不使用 PaddleDetection
        self.confidence_threshold = 0.1  # 置信度阈值
        
        # 性能指标广播控制
        self.last_performance_broadcast = time.time()
        self.performance_broadcast_interval = 10  # 每10秒广播一次性能指标
        
        logger.info("物体识别器初始化完成")
    
    def _maybe_broadcast_performance_update(self):
        """定期广播性能指标更新"""
        current_time = time.time()
        if (current_time - self.last_performance_broadcast) >= self.performance_broadcast_interval:
            performance_metrics = self.get_performance_metrics()
            stats = self.get_recognition_stats()
            
            broadcast_performance_update(
                accuracy=performance_metrics.get('accuracy', 0.0),
                precision=performance_metrics.get('precision', 0.0),
                recall=performance_metrics.get('recall', 0.0),
                f1_score=performance_metrics.get('f1_score', 0.0),
                total_recognitions=stats.get('total_recognitions', 0)
            )
            
            self.last_performance_broadcast = current_time
    
    def recognize_objects(self, image: np.ndarray) -> List[Dict]:
        """
        识别图像中的物体
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            List[Dict]: 识别结果列表
        """
        start_time = time.time()
        
        if image is None:
            logger.warning("输入图像为空")
            return []
        
        try:
            # 优先使用 PaddleDetection 模型
            if self.use_deep_learning and self.use_paddle_det:
                results = self.paddle_det_recognizer.detect_products(image)
                
                # 过滤低置信度结果
                filtered_results = [
                    result for result in results 
                    if result['confidence'] >= self.confidence_threshold
                ]
                
                # 计算处理时间
                processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                # 实时广播识别结果到WebSocket客户端
                for result in filtered_results:
                    broadcast_recognition_result(
                        class_name=result.get('class_name', 'Unknown'),
                        confidence=result.get('confidence', 0.0),
                        processing_time=processing_time,
                        image_info={
                            'width': image.shape[1],
                            'height': image.shape[0],
                            'channels': image.shape[2] if len(image.shape) > 2 else 1
                        }
                    )
                
                # 处理识别结果并自动创建订单
                if filtered_results:
                    self._process_recognition_results(filtered_results, image)
                
                # 定期广播性能指标更新
                self._maybe_broadcast_performance_update()
                
                logger.info(f"PaddleDetection识别完成，检测到 {len(filtered_results)} 个物体")
                return filtered_results
            elif self.use_deep_learning:
                # 回退到 YOLOv8 模型
                results = self.yolov8_recognizer.detect_products(image)
                
                # 过滤低置信度结果
                filtered_results = [
                    result for result in results 
                    if result['confidence'] >= self.confidence_threshold
                ]
                
                # 计算处理时间
                processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                # 实时广播识别结果到WebSocket客户端
                for result in filtered_results:
                    broadcast_recognition_result(
                        class_name=result.get('class_name', 'Unknown'),
                        confidence=result.get('confidence', 0.0),
                        processing_time=processing_time,
                        image_info={
                            'width': image.shape[1],
                            'height': image.shape[0],
                            'channels': image.shape[2] if len(image.shape) > 2 else 1
                        }
                    )
                
                # 处理识别结果并自动创建订单
                if filtered_results:
                    self._process_recognition_results(filtered_results, image)
                
                # 定期广播性能指标更新
                self._maybe_broadcast_performance_update()
                
                logger.info(f"YOLOv8识别完成，检测到 {len(filtered_results)} 个物体")
                return filtered_results
            else:
                # 回退到传统图像处理方法
                return self._traditional_recognition(image)
                
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"识别过程中出错: {e}")
            return []
    
    def _traditional_recognition(self, image: np.ndarray) -> List[Dict]:
        """
        传统图像处理识别方法（备用）
        
        Args:
            image: 输入图像
            
        Returns:
            List[Dict]: 识别结果列表
        """
        # 这里可以实现传统的图像处理算法
        # 作为深度学习方法的备用方案
        return []
    
    def _process_recognition_results(self, recognition_results: List[Dict], image: np.ndarray):
        """
        处理识别结果并自动创建订单
        
        Args:
            recognition_results: 识别结果列表
            image: 输入图像
        """
        try:
            # 保存识别记录
            recognition_record = self._save_recognition_record(recognition_results, image)
            
            # 创建订单
            if recognition_record:
                order = self._create_order_from_recognition(recognition_results, recognition_record)
                if order:
                    logger.info(f"成功为识别记录 {recognition_record.record_id} 创建订单 {order.order_no}")
                    # 广播订单创建事件
                    self._broadcast_order_created(order)
                    # 更新库存
                    self._update_inventory(order)
        except Exception as e:
            logger.error(f"处理识别结果并创建订单时出错: {e}")
    
    def _save_recognition_record(self, recognition_results: List[Dict], image: np.ndarray) -> Optional[VisualRecognitionRecord]:
        """
        保存识别记录到数据库
        
        Args:
            recognition_results: 识别结果列表
            image: 输入图像
            
        Returns:
            VisualRecognitionRecord: 保存的识别记录
        """
        try:
            # 保存图像到文件系统
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_filename = f"recognition_{timestamp}.jpg"
            image_path = os.path.join(settings.MEDIA_ROOT, 'recognition_records', image_filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            # 保存图像
            cv2.imwrite(image_path, image)
            
            # 保存识别记录
            recognition_record = VisualRecognitionRecord(
                image_path=os.path.join('recognition_records', image_filename),
                algorithm_used="YOLOv8+SAM" if self.use_deep_learning else "Traditional",
                recognition_result=recognition_results,
                status=VisualRecognitionRecord.Status.SUCCESS
            )
            recognition_record.save()
            
            return recognition_record
        except Exception as e:
            logger.error(f"保存识别记录时出错: {e}")
            return None
    
    @transaction.atomic
    def _create_order_from_recognition(self, recognition_results: List[Dict], 
                                     recognition_record: VisualRecognitionRecord) -> Optional[Order]:
        """
        从识别结果创建订单
        
        Args:
            recognition_results: 识别结果列表
            recognition_record: 识别记录
            
        Returns:
            Order: 创建的订单
        """
        try:
            # 统计识别到的商品
            product_counts = {}
            for result in recognition_results:
                class_name = result.get('class_name', 'Unknown')
                product_counts[class_name] = product_counts.get(class_name, 0) + 1
            
            # 查找对应的商品并计算总价
            total_amount = 0
            order_items = []
            
            for class_name, quantity in product_counts.items():
                try:
                    # 查找商品（这里简化处理，实际可能需要更复杂的匹配逻辑）
                    product = Product.objects.filter(name__icontains=class_name, is_active=True).first()
                    
                    if product:
                        # 检查库存
                        if product.stock >= quantity:
                            item_total = product.price * quantity
                            total_amount += item_total
                            
                            order_items.append({
                                'product': product,
                                'product_name': product.name,
                                'price': product.price,
                                'quantity': quantity
                            })
                        else:
                            logger.warning(f"商品 {class_name} 库存不足，当前库存: {product.stock}，需求: {quantity}")
                except Exception as e:
                    logger.error(f"处理商品 {class_name} 时出错: {e}")
            
            # 如果有有效的订单项，创建订单
            if order_items:
                # 创建订单
                order = Order(
                    total_amount=total_amount,
                    recognition_record=recognition_record,
                    status=Order.Status.PENDING
                )
                order.save()
                
                # 创建订单项
                for item_data in order_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        product_name=item_data['product_name'],
                        price=item_data['price'],
                        quantity=item_data['quantity']
                    )
                
                # 自动确认订单
                order.status = Order.Status.CONFIRMED
                order.confirmed_at = datetime.now()
                order.save()
                
                # 自动设置为已支付（在实际系统中可能需要支付接口集成）
                order.status = Order.Status.PAID
                order.paid_at = datetime.now()
                order.save()
                
                # 自动完成订单
                order.status = Order.Status.COMPLETED
                order.completed_at = datetime.now()
                order.save()
                
                return order
            
            return None
        except Exception as e:
            logger.error(f"创建订单时出错: {e}")
            return None
    
    def _update_inventory(self, order: Order):
        """
        更新库存数量
        
        Args:
            order: 已完成的订单
        """
        try:
            for item in order.items.all():
                if item.product:
                    item.product.stock -= item.quantity
                    if item.product.stock < 0:
                        item.product.stock = 0
                    item.product.save()
                    logger.info(f"更新商品 {item.product.name} 库存: 剩余 {item.product.stock}")
        except Exception as e:
            logger.error(f"更新库存时出错: {e}")
    
    def _broadcast_order_created(self, order: Order):
        """
        广播订单创建事件到WebSocket客户端
        
        Args:
            order: 创建的订单
        """
        try:
            # 构建订单数据
            order_data = {
                'order_no': order.order_no,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'items': [
                    {
                        'name': item.product_name,
                        'price': float(item.price),
                        'quantity': item.quantity,
                        'total_price': float(item.total_price)
                    }
                    for item in order.items.all()
                ],
                'timestamp': datetime.now().isoformat()
            }
            
            # 广播订单创建事件
            async_to_sync(websocket_manager._channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'order_created',
                    'data': order_data
                }
            )
            logger.info(f"广播订单创建事件: {order.order_no}")
        except Exception as e:
            logger.error(f"广播订单创建事件时出错: {e}")
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表
            
        Returns:
            np.ndarray: 绘制了检测结果的图像
        """
        # 使用YOLOv8识别器的visualize_detection方法
        result = {
            "products": detections
        }
        return self.yolov8_recognizer.visualize_detection(image, result)
    
    def get_performance_metrics(self) -> Dict:
        """
        获取识别性能指标
        
        Returns:
            Dict: 性能指标
        """
        # 返回YOLOv8模型信息
        model_info = self.yolov8_recognizer.get_model_info()
        return {
            'model_performance': {
                'model_type': 'YOLOv8',
                'device': model_info.get('device', 'unknown'),
                'class_count': model_info.get('class_count', 0),
                'last_updated': datetime.now().isoformat()
            },
            'recognition_stats': self.get_recognition_stats()
        }
    
    def get_recognition_stats(self) -> Dict:
        """
        获取识别统计信息
        
        Returns:
            Dict: 识别统计信息
        """
        # 简单的统计信息实现
        return {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_confidence': 0.0,
            'class_counts': {}
        }
    
    def train_model(self, epochs: int = 50, batch_size: int = 32) -> Dict:
        """
        训练深度学习模型
        
        Args:
            epochs: 训练轮数
            batch_size: 批次大小
            
        Returns:
            Dict: 训练结果
        """
        logger.info("开始训练YOLOv8模型...")
        # 这里需要指定数据集配置文件路径
        # 实际使用时需要根据具体情况修改
        dataset_config = "d:\Django\vending-machine-system\dataset.yaml"
        return self.yolov8_recognizer.train(
            data_path=dataset_config,
            epochs=epochs,
            batch=batch_size
        )
    
    def set_confidence_threshold(self, threshold: float):
        """
        设置置信度阈值
        
        Args:
            threshold: 置信度阈值 (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"置信度阈值已设置为: {threshold}")
        else:
            logger.warning("置信度阈值必须在0.0到1.0之间")
    
    def toggle_recognition_method(self):
        """
        切换识别方法
        """
        self.use_deep_learning = not self.use_deep_learning
        method = "深度学习" if self.use_deep_learning else "传统图像处理"
        logger.info(f"已切换到{method}识别方法")
    
    def reset_statistics(self):
        """重置识别统计信息"""
        # YOLOv8识别器统计信息重置
        logger.info("识别统计信息已重置")


# 全局识别器实例
_recognizer = None


def get_recognizer() -> ObjectRecognition:
    """
    获取全局识别器实例
    
    Returns:
        ObjectRecognition: 识别器实例
    """
    global _recognizer
    if _recognizer is None:
        _recognizer = ObjectRecognition()
    return _recognizer