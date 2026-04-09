# -*- coding: utf-8 -*-
"""
摄像头处理模块

该模块负责连接摄像头设备（当前使用电脑自带摄像头作为替代），捕获图像并传递给识别算法。
"""
import cv2
import threading
import time
from typing import Optional, Tuple, Dict, List
import numpy as np

# 导入识别算法模块
from products.services.object_recognition import get_recognizer


class CameraHandler:
    """
    摄像头处理器类，负责摄像头的连接和图像捕获
    """
    
    def __init__(self, camera_id: int = 0):
        """
        初始化摄像头处理器
        
        Args:
            camera_id: 摄像头ID，默认为0（通常是电脑自带摄像头）
        """
        self.camera_id = camera_id
        self.camera = None
        self.is_running = False
        self.last_frame = None
        self.last_recognition_result = []
        self.lock = threading.Lock()
        self.thread = None
        self.recognition_interval = 2  # 识别间隔（秒）
        self.last_recognition_time = 0
        
        # 获取识别器实例
        self.recognizer = get_recognizer()
    
    def start(self) -> bool:
        """
        启动摄像头
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 直接使用测试模式，避免与前端争夺摄像头资源
            # 前端会通过getUserMedia直接访问摄像头并显示画面
            print("使用测试模式启动摄像头服务")
            self._start_test_mode()
            return True
            
        except Exception as e:
            print(f"启动摄像头时出错: {e}")
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            self.is_running = False
            
            # 启动测试模式
            print("启动测试图像模式")
            self._start_test_mode()
            return True
    
    def _start_test_mode(self):
        """
        启动测试模式，使用测试图像代替摄像头
        """
        self.is_running = True
        self.use_test_mode = True
        self.test_frame_count = 0
        
        # 创建测试图像
        self.test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(self.test_image, "测试模式", (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
        
        # 启动测试模式循环
        self.thread = threading.Thread(target=self._test_mode_loop)
        self.thread.daemon = True
        self.thread.start()
        
        print("测试模式已启动")
    
    def _test_mode_loop(self):
        """
        测试模式循环，模拟摄像头画面变化
        """
        import random
        
        while self.is_running and getattr(self, 'use_test_mode', False):
            try:
                # 创建动态测试图像
                test_frame = self.test_image.copy()
                
                # 添加随机元素模拟画面变化
                x = random.randint(50, 590)
                y = random.randint(50, 430)
                cv2.circle(test_frame, (x, y), 20, (random.randint(0, 255), 
                       random.randint(0, 255), random.randint(0, 255)), -1)
                
                # 更新时间戳
                timestamp = time.strftime("%H:%M:%S")
                cv2.putText(test_frame, f"测试时间: {timestamp}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 更新帧
                with self.lock:
                    self.last_frame = test_frame.copy()
                    self.test_frame_count += 1
                
                # 定期进行识别
                current_time = time.time()
                if current_time - self.last_recognition_time >= self.recognition_interval:
                    self._recognize_objects()
                    self.last_recognition_time = current_time
                
                time.sleep(0.1)  # 10fps
                
            except Exception as e:
                print(f"测试模式出错: {e}")
                time.sleep(1)
    
    def stop(self):
        """
        停止摄像头
        """
        self.is_running = False
        self.use_test_mode = False
        
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
        # 清理测试模式数据
        if hasattr(self, 'test_image'):
            self.test_image = None
        
        print("摄像头已停止")
    
    def _capture_loop(self):
        """
        捕获图像的循环，在独立线程中运行
        """
        while self.is_running:
            try:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("无法获取图像帧")
                    time.sleep(0.1)
                    continue
                
                # 更新最新帧
                with self.lock:
                    self.last_frame = frame.copy()
                
                # 定期进行识别
                current_time = time.time()
                if current_time - self.last_recognition_time >= self.recognition_interval:
                    self._recognize_objects()
                    self.last_recognition_time = current_time
                
                # 限制帧率，避免CPU占用过高
                time.sleep(0.03)  # 约30fps
                
            except Exception as e:
                print(f"捕获图像时出错: {e}")
                time.sleep(0.1)
    
    def _recognize_objects(self):
        """
        调用识别算法识别图像中的物品
        """
        with self.lock:
            if self.last_frame is None:
                return
            frame = self.last_frame.copy()
        
        try:
            # 调用识别器进行识别
            recognition_result = self.recognizer.recognize_objects(frame)
            
            # 获取性能指标
            performance_metrics = self.recognizer.get_performance_metrics()
            print(f"识别完成，检测到 {len(recognition_result)} 个物体")
            print(f"识别统计: 总次数={performance_metrics.get('total_recognitions', 0)}, "
                  f"成功率={performance_metrics.get('success_rate', 0):.2%}")
            
            # 更新识别结果
            with self.lock:
                self.last_recognition_result = recognition_result
                
        except Exception as e:
            print(f"识别物品时出错: {e}")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        获取最新的摄像头帧
        
        Returns:
            Optional[np.ndarray]: 摄像头帧，如果没有则返回None
        """
        with self.lock:
            if self.last_frame is None:
                return None
            return self.last_frame.copy()
    
    def get_recognition_result(self) -> List[Dict]:
        """
        获取最新的识别结果
        
        Returns:
            List[Dict]: 识别结果列表
        """
        with self.lock:
            return self.last_recognition_result.copy()
    
    def get_frame_with_detections(self) -> Optional[np.ndarray]:
        """
        获取绘制了检测结果的帧
        
        Returns:
            Optional[np.ndarray]: 绘制了检测结果的帧
        """
        with self.lock:
            if self.last_frame is None:
                return None
            frame = self.last_frame.copy()
            result = self.last_recognition_result.copy()
        
        # 绘制检测结果
        return self.recognizer.draw_detections(frame, result)
    
    def get_camera_status(self) -> Dict:
        """
        获取摄像头状态信息
        
        Returns:
            Dict: 摄像头状态信息
        """
        status = {
            "running": self.is_running,
            "camera_id": self.camera_id,
            "frame_available": self.last_frame is not None,
            "last_recognition_time": self.last_recognition_time,
            "recognized_objects_count": len(self.last_recognition_result)
        }
        
        return status


# 全局摄像头处理器实例
_camera_handler = None


def get_camera_handler(camera_id: int = 0) -> CameraHandler:
    """
    获取摄像头处理器实例（单例模式）
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        CameraHandler: 摄像头处理器实例
    """
    global _camera_handler
    if _camera_handler is None:
        _camera_handler = CameraHandler(camera_id)
    return _camera_handler


def start_camera(camera_id: int = 0) -> bool:
    """
    启动摄像头（便捷函数）
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        bool: 启动是否成功
    """
    handler = get_camera_handler(camera_id)
    return handler.start()


def stop_camera():
    """
    停止摄像头（便捷函数）
    """
    global _camera_handler
    if _camera_handler is not None:
        _camera_handler.stop()
        _camera_handler = None


def get_latest_frame() -> Optional[np.ndarray]:
    """
    获取最新的摄像头帧（便捷函数）
    
    Returns:
        Optional[np.ndarray]: 摄像头帧
    """
    global _camera_handler
    if _camera_handler is not None:
        return _camera_handler.get_frame()
    return None


def get_latest_recognition_result() -> List[Dict]:
    """
    获取最新的识别结果（便捷函数）
    
    Returns:
        List[Dict]: 识别结果列表
    """
    global _camera_handler
    if _camera_handler is not None:
        return _camera_handler.get_recognition_result()
    return []