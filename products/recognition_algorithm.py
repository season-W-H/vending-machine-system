import cv2
import numpy as np
from PIL import Image
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductRecognition:
    """商品识别算法类"""
    
    def __init__(self):
        """初始化识别算法"""
        logger.info("初始化商品识别算法")
        # 这里可以加载预训练模型或其他初始化操作
        # 目前使用模拟识别，后续可以替换为真实的深度学习模型
        
        # 模拟商品数据库
        self.products_database = [
            {"name": "矿泉水550ml", "price": 3.00, "barcode": "6921168509256"},
            {"name": "可乐330ml", "price": 3.50, "barcode": "6901028155102"},
            {"name": "奶茶500ml", "price": 6.00, "barcode": "6933162100586"},
            {"name": "薯片(原味)60g", "price": 5.50, "barcode": "6924743404932"},
            {"name": "饼干(奶油味)100g", "price": 4.00, "barcode": "6902083813755"},
        ]
    
    def preprocess_image(self, image_data):
        """预处理图像
        
        Args:
            image_data: 图像数据（numpy数组或图像路径）
            
        Returns:
            预处理后的图像
        """
        try:
            # 如果传入的是字符串，认为是文件路径
            if isinstance(image_data, str):
                image = cv2.imread(image_data)
            else:
                # 假设image_data已经是numpy数组
                image = image_data
            
            if image is None:
                logger.error("无法读取图像数据")
                return None
            
            # 图像预处理步骤
            # 1. 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 2. 调整大小
            resized = cv2.resize(gray, (640, 480))
            
            # 3. 应用高斯模糊以减少噪声
            blurred = cv2.GaussianBlur(resized, (5, 5), 0)
            
            # 4. 自适应阈值处理
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            logger.info("图像预处理完成")
            return thresh
            
        except Exception as e:
            logger.error(f"图像预处理失败: {str(e)}")
            return None
    
    def detect_objects(self, preprocessed_image):
        """检测图像中的物体
        
        Args:
            preprocessed_image: 预处理后的图像
            
        Returns:
            检测到的物体列表，每个物体包含位置信息
        """
        try:
            if preprocessed_image is None:
                return []
            
            # 查找轮廓
            contours, _ = cv2.findContours(
                preprocessed_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            objects = []
            for contour in contours:
                # 计算轮廓的边界框
                x, y, w, h = cv2.boundingRect(contour)
                
                # 过滤小物体（可能是噪声）
                if w < 50 or h < 50:
                    continue
                
                # 计算轮廓面积
                area = cv2.contourArea(contour)
                
                # 计算边界框面积
                rect_area = w * h
                
                # 计算轮廓与边界框的面积比（用来过滤非矩形物体）
                extent = float(area) / rect_area
                
                # 只保留有一定面积且形状较为规则的物体
                if extent > 0.3:
                    objects.append({
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                        "area": area,
                        "extent": extent
                    })
            
            logger.info(f"检测到 {len(objects)} 个物体")
            return objects
            
        except Exception as e:
            logger.error(f"物体检测失败: {str(e)}")
            return []
    
    def recognize_products(self, image_data):
        """识别图像中的商品
        
        Args:
            image_data: 图像数据
            
        Returns:
            识别结果，包含识别到的商品列表
        """
        try:
            logger.info("开始商品识别")
            
            # 预处理图像
            preprocessed = self.preprocess_image(image_data)
            
            # 检测物体
            detected_objects = self.detect_objects(preprocessed)
            
            # 模拟识别结果（基于物体数量和大小）
            # 实际项目中这里应该使用深度学习模型或其他识别算法
            recognized_products = []
            
            # 根据检测到的物体数量和大小分配模拟商品
            for i, obj in enumerate(detected_objects):
                # 简单的模拟逻辑：根据索引从数据库中选择商品
                product_index = i % len(self.products_database)
                product = self.products_database[product_index].copy()
                
                # 添加位置信息
                product["position"] = {
                    "x": obj["x"],
                    "y": obj["y"],
                    "width": obj["width"],
                    "height": obj["height"]
                }
                
                recognized_products.append(product)
            
            # 如果没有检测到物体，返回一些模拟数据
            if not recognized_products:
                # 返回一些默认商品作为演示
                recognized_products = [
                    {"name": "矿泉水550ml", "price": 3.00, "barcode": "6921168509256"},
                    {"name": "薯片(原味)60g", "price": 5.50, "barcode": "6924743404932"}
                ]
            
            logger.info(f"商品识别完成，识别到 {len(recognized_products)} 个商品")
            return recognized_products
            
        except Exception as e:
            logger.error(f"商品识别失败: {str(e)}")
            return []
    
    def calculate_total(self, recognized_products):
        """计算识别到的商品总价
        
        Args:
            recognized_products: 识别到的商品列表
            
        Returns:
            商品总价
        """
        try:
            total = sum(product.get("price", 0) for product in recognized_products)
            logger.info(f"计算总价: ¥{total:.2f}")
            return total
            
        except Exception as e:
            logger.error(f"计算总价失败: {str(e)}")
            return 0.0

# 创建识别器实例，供其他模块使用
recognition_engine = ProductRecognition()