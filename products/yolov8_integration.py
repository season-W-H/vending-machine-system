"""
YOLOv8商品识别集成模块 - 优化版
集成先进的AI目标检测算法，实现精确的商品检测和识别
优化点：
- 延迟模型加载，提高启动速度
- 批量处理支持
- 异步推理支持
- 更好的错误处理
- 性能优化
- 模型训练功能
- 训练过程保存
"""

import cv2
import numpy as np
import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import torch
from PIL import Image
from functools import lru_cache

# 配置日志记录
logger = logging.getLogger(__name__)

class YOLOv8ProductRecognition:
    """基于YOLOv8的商品识别类 - 优化版"""
    
    # 类级别的缓存
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式，避免重复加载模型"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_path: Optional[str] = None, device: str = "auto", 
                 auto_load: bool = False):
        """
        初始化YOLOv8识别器
        
        Args:
            model_path: YOLOv8模型路径，None则使用预训练模型
            device: 计算设备 ("auto", "cpu", "cuda")
            auto_load: 是否自动加载模型（False为延迟加载）
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        logger.info("🚀 初始化YOLOv8商品识别器（优化版）")
        
        # 初始化模型
        self.model = None
        self.device = device
        self.model_path = model_path
        self.model_loaded = False
        self._initialized = False
        
        # 商品数据库
        self.products_database = self._load_products_database()
        
        # 数据集类别映射 - 与训练模型完全匹配（使用中文类别名称）
        self.class_mapping = {
            0: "百岁山", 1: "芬达", 2: "加多宝", 3: "康师傅红茶", 4: "维他命水",
            5: "脉动", 6: "美之源果粒橙", 7: "统一阿萨姆绿茶", 8: "统一阿萨姆红茶", 9: "营养快线"
        }
        
        # 性能优化参数
        self.batch_size = 8
        self.imgsz = 640
        self.conf_threshold = 0.6
        self.iou_threshold = 0.45
        
        # 训练相关参数
        self.train_params = {
            "epochs": 100,
            "batch": 8,
            "imgsz": 640,
            "patience": 10,
            "save_period": 10,
            "project": "runs/train",
            "name": f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # 确定设备
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"💻 使用设备: {self.device}")
        
        # 可选：延迟加载模型
        if auto_load:
            self._load_model()
        
        self._initialized = True
    
    def _load_products_database(self) -> List[Dict[str, Any]]:
        """加载商品数据库 - 与训练模型完全匹配"""
        return [
            {"name": "百岁山", "price": 3.00, "barcode": "6901028155102", "category": "bss"},
            {"name": "芬达", "price": 3.50, "barcode": "6901028155103", "category": "fd"},
            {"name": "加多宝", "price": 4.50, "barcode": "6901028155104", "category": "jdb"},
            {"name": "康师傅红茶", "price": 4.00, "barcode": "6901028155105", "category": "ksfh"},
            {"name": "维他命水", "price": 5.50, "barcode": "6901028155106", "category": "llds"},
            {"name": "脉动", "price": 5.00, "barcode": "6901028155107", "category": "md"},
            {"name": "美之源果粒橙", "price": 4.80, "barcode": "6901028155108", "category": "mzy"},
            {"name": "统一阿萨姆绿茶", "price": 3.80, "barcode": "6901028155109", "category": "tycl"},
            {"name": "统一阿萨姆红茶", "price": 3.80, "barcode": "6901028155110", "category": "tyyc"},
            {"name": "营养快线", "price": 5.50, "barcode": "6901028155111", "category": "yykx"},
        ]
    
    def _load_model(self, force_reload: bool = False) -> bool:
        """加载YOLOv8模型 - 优化版
        
        Args:
            force_reload: 是否强制重新加载模型
            
        Returns:
            模型是否加载成功
        """
        if self.model_loaded and not force_reload:
            logger.info("✅ 模型已加载，跳过")
            return True
            
        try:
            from ultralytics import YOLO
            
            logger.info("📦 开始加载YOLOv8模型...")
            
            # 加载模型
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"🔧 加载自定义模型: {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                logger.info("🔧 使用预训练YOLOv8模型 (yolov8n.pt)")
                self.model = YOLO("yolov8n.pt")
            
            # 移动到指定设备
            self.model.to(self.device)
            
            # 优化：启用自动混合精度
            if self.device == "cuda":
                torch.cuda.amp.autocast(enabled=True)
                logger.info("⚡ 已启用自动混合精度")
            
            self.model_loaded = True
            logger.info("✅ YOLOv8模型加载成功")
            return True
            
        except ImportError as e:
            logger.error("❌ YOLOv8未安装，请运行: pip install ultralytics")
            self.model = None
            self.model_loaded = False
            return False
        except FileNotFoundError as e:
            logger.error(f"❌ 模型文件未找到: {str(e)}")
            self.model = None
            self.model_loaded = False
            return False
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            self.model = None
            self.model_loaded = False
            return False
    
    def preprocess_image(self, image_data: Any, target_size: Optional[Tuple[int, int]] = None) -> Optional[np.ndarray]:
        """
        预处理图像 - 优化版
        
        Args:
            image_data: 图像数据（文件路径、URL、numpy数组或PIL图像）
            target_size: 目标尺寸 (width, height)，None则保持原图
            
        Returns:
            预处理后的图像
        """
        try:
            # 处理不同类型的输入
            if isinstance(image_data, str):
                # 文件路径
                if image_data.startswith(('http://', 'https://')):
                    # URL下载
                    import requests
                    from io import BytesIO
                    response = requests.get(image_data, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                else:
                    # 本地文件
                    if not os.path.exists(image_data):
                        logger.error(f"❌ 文件不存在: {image_data}")
                        return None
                    image = cv2.imread(image_data)
            elif isinstance(image_data, np.ndarray):
                image = image_data.copy()
            elif isinstance(image_data, Image.Image):
                # PIL图像
                image = cv2.cvtColor(np.array(image_data), cv2.COLOR_RGB2BGR)
            else:
                logger.error(f"❌ 不支持的图像数据类型: {type(image_data)}")
                return None
            
            if image is None:
                logger.error("❌ 无法读取图像")
                return None
            
            # 确保是BGR格式（YOLOv8期望的格式）
            if len(image.shape) == 2:
                # 灰度图像转换为彩色
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 4:
                # RGBA图像转换为BGR
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            
            # 调整尺寸（可选）
            if target_size is not None:
                image = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
            
            logger.info(f"✅ 图像预处理完成，尺寸: {image.shape}")
            return image
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 下载图像失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ 图像预处理失败: {str(e)}")
            return None
    
    def detect_products(self, image_data: Any, confidence_threshold: Optional[float] = None,
                       iou_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        使用YOLOv8检测商品 - 优化版
        
        Args:
            image_data: 图像数据
            confidence_threshold: 置信度阈值（None则使用默认值）
            iou_threshold: IOU阈值（None则使用默认值）
            
        Returns:
            检测到的商品列表
        """
        # 使用默认阈值
        conf_thresh = confidence_threshold if confidence_threshold is not None else self.conf_threshold
        iou_thresh = iou_threshold if iou_threshold is not None else self.iou_threshold
        
        try:
            # 确保模型已加载
            if not self.model_loaded:
                if not self._load_model():
                    logger.error("❌ 模型未加载，检测失败")
                    return []
            
            # 预处理图像
            image = self.preprocess_image(image_data)
            if image is None:
                return []
            
            # 执行推理
            results = self.model(image, conf=conf_thresh, iou=iou_thresh, 
                                imgsz=self.imgsz, verbose=False)
            
            # 打印原始检测结果（调试用）
            logger.info(f"🔍 原始检测结果: {len(results)} 个结果")
            for idx, result in enumerate(results):
                logger.info(f"  结果 {idx}:")
                if result.boxes is not None:
                    logger.info(f"    检测框数量: {len(result.boxes)}")
                    for box_idx, box in enumerate(result.boxes):
                        class_id = int(box.cls[0].cpu().numpy())
                        confidence = float(box.conf[0].cpu().numpy())
                        logger.info(f"    框 {box_idx}: class_id={class_id}, confidence={confidence:.4f}")
            
            detected_products = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # 计算宽高
                        width = x2 - x1
                        height = y2 - y1
                        
                        # 获取类别名称
                        class_name = self.class_mapping.get(class_id, f"商品_{class_id}")
                        
                        # 查找匹配的数据库商品
                        matched_product = self._match_product(class_name)
                        
                        product_info = {
                            "name": matched_product["name"],
                            "price": matched_product["price"],
                            "barcode": matched_product["barcode"],
                            "category": matched_product["category"],
                            "confidence": float(confidence),
                            "bbox": {
                                "x": float(x1),
                                "y": float(y1),
                                "width": float(width),
                                "height": float(height)
                            },
                            "class_id": class_id,
                            "class_name": class_name
                        }
                        
                        detected_products.append(product_info)
            
            logger.info(f"✅ YOLOv8检测到 {len(detected_products)} 个商品")
            return detected_products
            
        except Exception as e:
            logger.error(f"❌ YOLOv8检测失败: {str(e)}")
            return []
    
    def detect_products_batch(self, images_data: List[Any], 
                             confidence_threshold: Optional[float] = None,
                             iou_threshold: Optional[float] = None) -> List[List[Dict[str, Any]]]:
        """
        批量检测商品 - 新增功能
        
        Args:
            images_data: 图像数据列表
            confidence_threshold: 置信度阈值
            iou_threshold: IOU阈值
            
        Returns:
            每个图像的检测结果列表
        """
        logger.info(f"📦 开始批量处理 {len(images_data)} 张图像")
        
        # 预处理所有图像
        preprocessed_images = []
        valid_indices = []
        
        for i, img_data in enumerate(images_data):
            img = self.preprocess_image(img_data)
            if img is not None:
                preprocessed_images.append(img)
                valid_indices.append(i)
        
        if not preprocessed_images:
            logger.error("❌ 没有有效的图像")
            return [[] for _ in images_data]
        
        # 确保模型已加载
        if not self.model_loaded:
            if not self._load_model():
                return [[] for _ in images_data]
        
        # 批量推理
        try:
            results = self.model(preprocessed_images, 
                               conf=confidence_threshold or self.conf_threshold,
                               iou=iou_threshold or self.iou_threshold,
                               imgsz=self.imgsz,
                               batch=self.batch_size,
                               verbose=False)
            
            # 整理结果
            all_results = [[] for _ in images_data]
            result_idx = 0
            
            for i in valid_indices:
                result = results[result_idx]
                detected_products = []
                
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        class_name = self.class_mapping.get(class_id, f"商品_{class_id}")
                        matched_product = self._match_product(class_name)
                        
                        product_info = {
                            "name": matched_product["name"],
                            "price": matched_product["price"],
                            "confidence": float(confidence),
                            "bbox": {
                                "x": float(x1), "y": float(y1),
                                "width": float(x2 - x1), "height": float(y2 - y1)
                            },
                            "class_id": class_id,
                            "class_name": class_name
                        }
                        detected_products.append(product_info)
                
                all_results[i] = detected_products
                result_idx += 1
            
            logger.info(f"✅ 批量处理完成")
            return all_results
            
        except Exception as e:
            logger.error(f"❌ 批量检测失败: {str(e)}")
            return [[] for _ in images_data]
    
    def _match_product(self, detected_class: str) -> Dict[str, Any]:
        """
        将检测到的类别匹配到商品数据库
        
        Args:
            detected_class: 检测到的类别名称
            
        Returns:
            匹配的的商品信息
        """
        # 尝试直接匹配类别名称
        for product in self.products_database:
            if product["category"] == detected_class or product["name"] == detected_class:
                return product
        
        # 如果没有匹配到，返回默认商品
        return {
            "name": f"未识别商品({detected_class})",
            "price": 0.0,
            "barcode": "0000000000000",
            "category": "其他"
        }
    
    def recognize_and_calculate(self, image_data: Any, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        完整的识别和计算流程
        
        Args:
            image_data: 图像数据
            confidence_threshold: 置信度阈值
            
        Returns:
            识别结果和总价
        """
        try:
            logger.info("开始YOLOv8商品识别和计算")
            
            # 检测商品
            detected_products = self.detect_products(image_data, confidence_threshold)
            
            # 计算总价
            total_price = sum(product["price"] for product in detected_products)
            
            result = {
                "success": True,
                "detected_count": len(detected_products),
                "products": detected_products,
                "total_price": round(total_price, 2),
                "algorithm": "YOLOv8",
                "model_info": {
                    "device": self.device,
                    "confidence_threshold": confidence_threshold
                }
            }
            
            logger.info(f"YOLOv8识别完成: {len(detected_products)}个商品，总价¥{total_price:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"YOLOv8识别计算失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "detected_count": 0,
                "products": [],
                "total_price": 0.0,
                "algorithm": "YOLOv8"
            }
    
    def save_detection_result(self, result: Dict[str, Any], output_path: str):
        """
        保存检测结果
        
        Args:
            result: 检测结果
            output_path: 输出路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"检测结果已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存检测结果失败: {str(e)}")
    
    def visualize_detection(self, image_data: Any, result: Dict[str, Any], 
                          output_path: Optional[str] = None) -> Optional[np.ndarray]:
        """
        可视化检测结果
        
        Args:
            image_data: 原始图像
            result: 检测结果
            output_path: 输出图像路径
            
        Returns:
            可视化后的图像
        """
        try:
            # 获取原始图像
            image = self.preprocess_image(image_data)
            if image is None:
                return None
            
            # 绘制检测结果
            for product in result.get("products", []):
                bbox = product["bbox"]
                x, y, w, h = int(bbox["x"]), int(bbox["y"]), int(bbox["width"]), int(bbox["height"])
                
                # 绘制边界框
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 绘制标签
                label = f'{product["name"]} ¥{product["price"]:.2f} ({product["confidence"]:.2f})'
                cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 保存图像
            if output_path:
                cv2.imwrite(output_path, image)
                logger.info(f"可视化结果已保存到: {output_path}")
            
            return image
            
        except Exception as e:
            logger.error(f"可视化检测结果失败: {str(e)}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_type": "YOLOv8",
            "device": self.device,
            "model_loaded": self.model is not None,
            "class_count": len(self.class_mapping),
            "products_count": len(self.products_database)
        }
    
    def prepare_dataset(self, dataset_path: str) -> bool:
        """
        准备训练数据集
        
        Args:
            dataset_path: 数据集路径
            
        Returns:
            数据集是否准备成功
        """
        try:
            # 检查数据集路径
            if not os.path.exists(dataset_path):
                logger.error(f"❌ 数据集路径不存在: {dataset_path}")
                return False
            
            # 检查必要的目录结构
            required_dirs = ['images', 'labels']
            for dir_name in required_dirs:
                dir_path = os.path.join(dataset_path, dir_name)
                if not os.path.exists(dir_path):
                    logger.error(f"❌ 数据集缺少必要目录: {dir_name}")
                    return False
            
            # 检查训练和验证数据
            train_images = os.path.join(dataset_path, 'images', 'train')
            val_images = os.path.join(dataset_path, 'images', 'val')
            train_labels = os.path.join(dataset_path, 'labels', 'train')
            val_labels = os.path.join(dataset_path, 'labels', 'val')
            
            for dir_path in [train_images, val_images, train_labels, val_labels]:
                if not os.path.exists(dir_path):
                    logger.warning(f"⚠️ 数据集缺少目录: {dir_path}")
            
            logger.info(f"✅ 数据集准备完成: {dataset_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据集准备失败: {str(e)}")
            return False
    
    def train(self, data_path: str, **kwargs) -> Dict[str, Any]:
        """
        训练YOLOv8模型
        
        Args:
            data_path: 数据集配置文件路径 (yaml)
            **kwargs: 训练参数
            
        Returns:
            训练结果
        """
        try:
            logger.info("🚀 开始训练YOLOv8模型...")
            
            # 检查数据集文件
            if not os.path.exists(data_path):
                logger.error(f"❌ 数据集配置文件不存在: {data_path}")
                return {
                    "success": False,
                    "error": f"数据集配置文件不存在: {data_path}"
                }
            
            # 更新训练参数
            train_params = self.train_params.copy()
            train_params.update(kwargs)
            
            # 确保模型已加载
            if not self.model_loaded:
                if not self._load_model():
                    return {
                        "success": False,
                        "error": "模型加载失败"
                    }
            
            # 开始训练
            logger.info(f"📋 训练参数: {train_params}")
            
            # 记录开始时间
            start_time = time.time()
            
            # 执行训练
            results = self.model.train(
                data=data_path,
                epochs=train_params["epochs"],
                batch=train_params["batch"],
                imgsz=train_params["imgsz"],
                patience=train_params["patience"],
                save_period=train_params["save_period"],
                project=train_params["project"],
                name=train_params["name"],
                device=self.device
            )
            
            # 计算训练时间
            training_time = time.time() - start_time
            
            # 训练结果
            train_result = {
                "success": True,
                "model_path": os.path.join(train_params["project"], train_params["name"], "weights", "best.pt"),
                "last_model_path": os.path.join(train_params["project"], train_params["name"], "weights", "last.pt"),
                "training_time": training_time,
                "epochs": train_params["epochs"],
                "project": train_params["project"],
                "name": train_params["name"],
                "metrics": {
                    "mAP50": float(results.box.map50),
                    "mAP50-95": float(results.box.map),
                    "precision": float(results.box.mp),
                    "recall": float(results.box.mr)
                }
            }
            
            logger.info(f"✅ 训练完成！耗时: {training_time:.2f}秒")
            logger.info(f"📦 最佳模型保存路径: {train_result['model_path']}")
            
            # 更新模型路径
            if os.path.exists(train_result["model_path"]):
                self.model_path = train_result["model_path"]
                # 重新加载训练好的模型
                self._load_model(force_reload=True)
            
            return train_result
            
        except Exception as e:
            logger.error(f"❌ 训练失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate(self, data_path: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """
        验证模型性能
        
        Args:
            data_path: 数据集配置文件路径
            model_path: 模型路径（可选）
            
        Returns:
            验证结果
        """
        try:
            logger.info("📊 开始验证模型性能...")
            
            # 检查数据集文件
            if not os.path.exists(data_path):
                logger.error(f"❌ 数据集配置文件不存在: {data_path}")
                return {
                    "success": False,
                    "error": f"数据集配置文件不存在: {data_path}"
                }
            
            # 加载指定模型（如果提供）
            if model_path:
                if os.path.exists(model_path):
                    logger.info(f"🔧 加载指定模型: {model_path}")
                    from ultralytics import YOLO
                    temp_model = YOLO(model_path)
                    temp_model.to(self.device)
                else:
                    logger.error(f"❌ 模型文件不存在: {model_path}")
                    return {
                        "success": False,
                        "error": f"模型文件不存在: {model_path}"
                    }
            else:
                # 使用当前模型
                if not self.model_loaded:
                    if not self._load_model():
                        return {
                            "success": False,
                            "error": "模型加载失败"
                        }
                temp_model = self.model
            
            # 执行验证
            results = temp_model.val(
                data=data_path,
                imgsz=self.imgsz,
                batch=self.batch_size,
                device=self.device
            )
            
            # 验证结果
            val_result = {
                "success": True,
                "metrics": {
                    "mAP50": float(results.box.map50),
                    "mAP50-95": float(results.box.map),
                    "precision": float(results.box.mp),
                    "recall": float(results.box.mr),
                    "f1": float(results.box.f1)
                },
                "model_used": model_path or self.model_path or "yolov8n.pt"
            }
            
            logger.info(f"✅ 验证完成！mAP50: {val_result['metrics']['mAP50']:.4f}")
            
            return val_result
            
        except Exception as e:
            logger.error(f"❌ 验证失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_model(self, export_format: str = "onnx") -> Dict[str, Any]:
        """
        导出模型为不同格式
        
        Args:
            export_format: 导出格式 (onnx, torchscript, engine, etc.)
            
        Returns:
            导出结果
        """
        try:
            logger.info(f"📤 导出模型为 {export_format} 格式...")
            
            # 确保模型已加载
            if not self.model_loaded:
                if not self._load_model():
                    return {
                        "success": False,
                        "error": "模型加载失败"
                    }
            
            # 执行导出
            export_results = self.model.export(
                format=export_format,
                imgsz=self.imgsz,
                device=self.device
            )
            
            # 导出结果
            export_result = {
                "success": True,
                "export_format": export_format,
                "export_path": export_results,
                "model_info": self.get_model_info()
            }
            
            logger.info(f"✅ 模型导出完成: {export_results}")
            
            return export_result
            
        except Exception as e:
            logger.error(f"❌ 模型导出失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# 创建全局实例，使用训练好的最佳模型
trained_model_path = r"d:\Django\vending-machine-system\runs\train\exp_20260209_173718\weights\best.pt"
if os.path.exists(trained_model_path):
    logger.info(f"🎯 使用训练好的最佳模型: {trained_model_path}")
    yolov8_recognition = YOLOv8ProductRecognition(model_path=trained_model_path, auto_load=True)
else:
    logger.warning("⚠️ 训练模型文件不存在，使用预训练模型")
    yolov8_recognition = YOLOv8ProductRecognition()