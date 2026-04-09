import cv2
import threading
import time
import logging
from PIL import Image
import numpy as np

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraManager:
    """摄像头管理类"""
    
    def __init__(self, camera_id=0):
        """初始化摄像头管理器
        
        Args:
            camera_id: 摄像头ID，默认为0（通常是内置摄像头）
        """
        self.camera_id = camera_id
        self.camera = None
        self.is_running = False
        self.current_frame = None
        self.lock = threading.Lock()
        self.last_frame_time = 0
        self.frame_rate = 0
        logger.info(f"初始化摄像头管理器，摄像头ID: {camera_id}")
    
    def start_camera(self):
        """启动摄像头
        
        Returns:
            bool: 是否成功启动
        """
        try:
            with self.lock:
                if self.is_running:
                    logger.warning("摄像头已经在运行")
                    return True
                
                # 尝试打开摄像头
                self.camera = cv2.VideoCapture(self.camera_id)
                
                # 检查摄像头是否成功打开
                if not self.camera.isOpened():
                    logger.error(f"无法打开摄像头，ID: {self.camera_id}")
                    self.camera = None
                    return False
                
                # 设置摄像头属性（如果需要）
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                
                # 启动摄像头读取线程
                self.is_running = True
                self.thread = threading.Thread(target=self._read_frames, daemon=True)
                self.thread.start()
                
                logger.info("摄像头成功启动")
                return True
                
        except Exception as e:
            logger.error(f"启动摄像头失败: {str(e)}")
            self.camera = None
            self.is_running = False
            return False
    
    def stop_camera(self):
        """停止摄像头
        
        Returns:
            bool: 是否成功停止
        """
        try:
            with self.lock:
                if not self.is_running:
                    logger.warning("摄像头未在运行")
                    return True
                
                # 停止运行标志
                self.is_running = False
                
                # 等待线程结束
                if hasattr(self, 'thread'):
                    self.thread.join(timeout=2.0)
                
                # 释放摄像头
                if self.camera is not None:
                    self.camera.release()
                    self.camera = None
                
                # 清空当前帧
                self.current_frame = None
                
                logger.info("摄像头成功停止")
                return True
                
        except Exception as e:
            logger.error(f"停止摄像头失败: {str(e)}")
            return False
    
    def _read_frames(self):
        """读取摄像头帧的线程函数"""
        frame_count = 0
        last_time = time.time()
        
        while self.is_running and self.camera is not None:
            try:
                # 读取一帧
                ret, frame = self.camera.read()
                
                if not ret:
                    logger.warning("无法读取摄像头帧")
                    time.sleep(0.1)
                    continue
                
                # 计算帧率
                frame_count += 1
                current_time = time.time()
                elapsed = current_time - last_time
                
                if elapsed >= 1.0:  # 每秒更新一次帧率
                    self.frame_rate = frame_count / elapsed
                    frame_count = 0
                    last_time = current_time
                
                # 更新当前帧
                with self.lock:
                    self.current_frame = frame.copy()
                    self.last_frame_time = current_time
                    
                # 控制帧率，避免CPU占用过高
                time.sleep(0.033)  # 大约30fps
                
            except Exception as e:
                logger.error(f"读取摄像头帧失败: {str(e)}")
                time.sleep(0.1)
    
    def get_frame(self):
        """获取当前帧
        
        Returns:
            numpy.ndarray or None: 当前帧图像，如果摄像头未运行或无法获取则返回None
        """
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_image(self):
        """捕获一张图像
        
        Returns:
            numpy.ndarray or None: 捕获的图像，如果摄像头未运行或无法获取则返回None
        """
        frame = self.get_frame()
        if frame is not None:
            logger.info("成功捕获图像")
        else:
            logger.warning("无法捕获图像")
        return frame
    
    def get_status(self):
        """获取摄像头状态
        
        Returns:
            dict: 包含摄像头状态信息的字典
        """
        with self.lock:
            return {
                "is_running": self.is_running,
                "has_frame": self.current_frame is not None,
                "frame_rate": round(self.frame_rate, 1),
                "last_frame_time": self.last_frame_time
            }
    
    def get_camera_info(self):
        """获取摄像头信息
        
        Returns:
            dict: 包含摄像头信息的字典
        """
        info = {
            "camera_id": self.camera_id,
            "is_available": False,
            "resolution": {"width": 0, "height": 0}
        }
        
        # 临时打开摄像头获取信息
        temp_camera = cv2.VideoCapture(self.camera_id)
        if temp_camera.isOpened():
            info["is_available"] = True
            info["resolution"]["width"] = int(temp_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["resolution"]["height"] = int(temp_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            temp_camera.release()
            logger.info(f"获取摄像头信息成功: {info}")
        else:
            logger.warning(f"无法获取摄像头信息，ID: {self.camera_id}")
        
        return info
    
    def convert_to_pil_image(self, frame):
        """将OpenCV帧转换为PIL图像
        
        Args:
            frame: OpenCV格式的图像帧
            
        Returns:
            PIL.Image: PIL格式的图像
        """
        if frame is None:
            return None
        
        # OpenCV使用BGR格式，PIL使用RGB格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_frame)
    
    def __del__(self):
        """析构函数，确保摄像头正确释放"""
        self.stop_camera()

# 创建摄像头管理器实例，供其他模块使用
camera_manager = CameraManager()