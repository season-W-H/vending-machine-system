# -*- coding: utf-8 -*-
"""
WebSocket消费者 - 实时识别结果推送

该模块实现WebSocket连接，用于将识别结果实时推送到前端页面。
支持多个客户端同时连接，实时推送识别结果和性能指标。
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class RecognitionConsumer(AsyncWebsocketConsumer):
    """
    识别结果WebSocket消费者
    """
    
    async def connect(self):
        """建立WebSocket连接"""
        self.room_group_name = 'recognition_results'
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket连接建立: {self.channel_name}")
        
        # 发送连接成功消息
        await self.send_text_data({
            'type': 'connection',
            'message': 'WebSocket连接成功',
            'timestamp': datetime.now().isoformat()
        })
    
    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket连接断开: {self.channel_name}")
    
    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # 心跳检测
                await self.send_text_data({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
            elif message_type == 'get_status':
                # 获取当前状态
                await self.send_text_data({
                    'type': 'status',
                    'status': 'connected',
                    'timestamp': datetime.now().isoformat()
                })
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
        except Exception as e:
            logger.error(f"处理WebSocket消息错误: {e}")
    
    async def send_text_data(self, data):
        """发送文本数据"""
        try:
            await self.send(text_data=json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送WebSocket数据错误: {e}")
    
    async def recognition_result(self, event):
        """处理识别结果推送"""
        await self.send_text_data({
            'type': 'recognition_result',
            'data': event['data'],
            'timestamp': datetime.now().isoformat()
        })
    
    async def performance_update(self, event):
        """处理性能指标更新"""
        await self.send_text_data({
            'type': 'performance_update',
            'data': event['data'],
            'timestamp': datetime.now().isoformat()
        })
    
    async def order_created(self, event):
        """处理订单创建事件"""
        await self.send_text_data({
            'type': 'order_created',
            'data': event['data'],
            'timestamp': datetime.now().isoformat()
        })
    
    async def statistics_update(self, event):
        """处理统计数据更新事件"""
        await self.send_text_data({
            'type': 'statistics_update',
            'data': event['data'],
            'timestamp': datetime.now().isoformat()
        })
    
    async def training_progress(self, event):
        """处理训练进度更新"""
        await self.send_text_data({
            'type': 'training_progress',
            'data': event['data'],
            'timestamp': datetime.now().isoformat()
        })
    
    async def broadcast_message(self, event):
        """处理通用消息广播"""
        await self.send_text_data(event['data'])


class WebSocketManager:
    """
    WebSocket管理器 - 单例模式
    """
    
    _instance = None
    _channel_layer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 延迟初始化Channel层，避免在模块导入时出错
        return cls._instance
    
    def _get_channel_layer(self):
        """延迟获取Channel层"""
        if self._channel_layer is None:
            self._channel_layer = get_channel_layer()
        return self._channel_layer
    
    @classmethod
    def broadcast_recognition_result(cls, result_data: Dict[str, Any]):
        """
        广播识别结果到所有连接的客户端
        
        Args:
            result_data: 识别结果数据
        """
        try:
            channel_layer = cls()._get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'recognition_result',
                    'data': result_data
                }
            )
            logger.info(f"广播识别结果: {result_data.get('class_name', 'Unknown')}")
        except Exception as e:
            logger.error(f"广播识别结果失败: {e}")
    
    @classmethod
    def broadcast_performance_update(cls, performance_data: Dict[str, Any]):
        """
        广播性能指标更新到所有连接的客户端
        
        Args:
            performance_data: 性能指标数据
        """
        try:
            channel_layer = cls()._get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'performance_update',
                    'data': performance_data
                }
            )
            logger.info("广播性能指标更新")
        except Exception as e:
            logger.error(f"广播性能指标失败: {e}")
    
    @classmethod
    def broadcast_training_progress(cls, training_data: Dict[str, Any]):
        """
        广播训练进度到所有连接的客户端
        
        Args:
            training_data: 训练进度数据
        """
        try:
            channel_layer = cls()._get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'training_progress',
                    'data': training_data
                }
            )
            logger.info("广播训练进度更新")
        except Exception as e:
            logger.error(f"广播训练进度失败: {e}")
    
    @classmethod
    def broadcast_statistics_update(cls, statistics_data: Dict[str, Any]):
        """
        广播统计数据更新到所有连接的客户端
        
        Args:
            statistics_data: 统计数据
        """
        try:
            channel_layer = cls()._get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'statistics_update',
                    'data': statistics_data
                }
            )
            logger.info("广播统计数据更新")
        except Exception as e:
            logger.error(f"广播统计数据失败: {e}")
    
    @classmethod
    def broadcast_message(cls, message_data: Dict[str, Any]):
        """
        广播通用消息到所有连接的客户端
        
        Args:
            message_data: 消息数据
        """
        try:
            channel_layer = cls()._get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'recognition_results',
                {
                    'type': 'broadcast_message',
                    'data': message_data
                }
            )
            logger.info(f"广播消息: {message_data.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"广播消息失败: {e}")


# 便捷函数
def broadcast_statistics_update(statistics_data: Dict[str, Any]):
    """
    便捷函数：广播统计数据更新
    
    Args:
        statistics_data: 统计数据
    """
    WebSocketManager.broadcast_message({
        'type': 'statistics_update',
        'data': statistics_data
    })


def broadcast_flow_status(status_data: Dict[str, Any]):
    """
    便捷函数：广播流程状态
    
    Args:
        status_data: 流程状态数据
    """
    WebSocketManager.broadcast_message({
        'type': 'flow_status',
        'data': status_data
    })


def broadcast_order_update(order_data: Dict[str, Any]):
    """
    便捷函数：广播订单更新
    
    Args:
        order_data: 订单数据
    """
    WebSocketManager.broadcast_message({
        'type': 'order_update',
        'data': order_data
    })


def broadcast_inventory_update(inventory_data: Dict[str, Any]):
    """
    便捷函数：广播库存更新
    
    Args:
        inventory_data: 库存数据
    """
    WebSocketManager.broadcast_message({
        'type': 'inventory_update',
        'data': inventory_data
    })


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


def broadcast_recognition_result(class_name: str, confidence: float, 
                               processing_time: float, image_info: Dict = None):
    """
    广播识别结果的便捷函数
    
    Args:
        class_name: 识别的类别名称
        confidence: 置信度
        processing_time: 处理时间（毫秒）
        image_info: 图像信息
    """
    result_data = {
        'class_name': class_name,
        'confidence': confidence,
        'processing_time_ms': processing_time,
        'image_info': image_info or {},
        'timestamp': datetime.now().isoformat()
    }
    websocket_manager.broadcast_recognition_result(result_data)


def broadcast_performance_update(accuracy: float, precision: float, 
                                recall: float, f1_score: float, 
                                total_recognitions: int):
    """
    广播性能指标更新的便捷函数
    
    Args:
        accuracy: 准确率
        precision: 精确率
        recall: 召回率
        f1_score: F1分数
        total_recognitions: 总识别次数
    """
    performance_data = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'total_recognitions': total_recognitions,
        'timestamp': datetime.now().isoformat()
    }
    websocket_manager.broadcast_performance_update(performance_data)


def broadcast_training_progress(epoch: int, total_epochs: int, 
                              loss: float, accuracy: float, 
                              val_loss: float, val_accuracy: float):
    """
    广播训练进度的便捷函数
    
    Args:
        epoch: 当前轮数
        total_epochs: 总轮数
        loss: 训练损失
        accuracy: 训练准确率
        val_loss: 验证损失
        val_accuracy: 验证准确率
    """
    training_data = {
        'epoch': epoch,
        'total_epochs': total_epochs,
        'loss': loss,
        'accuracy': accuracy,
        'val_loss': val_loss,
        'val_accuracy': val_accuracy,
        'progress_percentage': (epoch / total_epochs) * 100,
        'timestamp': datetime.now().isoformat()
    }
    websocket_manager.broadcast_training_progress(training_data)


def broadcast_statistics_update(statistics_data: Dict[str, Any]):
    """
    广播统计数据更新的便捷函数
    
    Args:
        statistics_data: 统计数据
    """
    websocket_manager.broadcast_statistics_update(statistics_data)