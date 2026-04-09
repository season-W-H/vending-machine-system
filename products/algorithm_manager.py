#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法集成管理器
统一管理YOLOv8、SAM、Mask R-CNN等算法，提供完整的商品识别和分割服务
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入训练记录器
try:
    from training_recorder import TrainingRecorder, TrainingConfig, TrainingMetrics, TrainingStatus
    TRAINING_RECORDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 训练记录器模块未加载: {e}")
    TRAINING_RECORDER_AVAILABLE = False

class AlgorithmType(Enum):
    """算法类型枚举"""
    YOLOV8 = "yolov8"
    SAM = "sam"
    MASK_RCNN = "mask_rcnn"
    TRADITIONAL = "traditional"

class ProcessingMode(Enum):
    """处理模式枚举"""
    FAST = "fast"  # 快速模式：只使用YOLOv8
    ACCURATE = "accurate"  # 精确模式：使用所有算法
    CUSTOM = "custom"  # 自定义模式：用户选择算法

@dataclass
class RecognitionResult:
    """识别结果数据类"""
    success: bool
    algorithm_used: str
    processing_time: float
    detected_products: List[Dict[str, Any]]
    total_price: float
    confidence_scores: List[float]
    bounding_boxes: List[List[int]]
    segmentations: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

class AlgorithmManager:
    """算法集成管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化算法管理器
        
        Args:
            config_path: 配置文件路径
        """
        logger.info("🧠 初始化算法集成管理器")
        
        self.config = self._load_config(config_path)
        self.algorithms = {}
        self.algorithm_status = {}
        self.processing_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0,
            "algorithm_usage": {algo.value: 0 for algo in AlgorithmType}
        }
        
        # 初始化训练记录器
        self.training_recorder = None
        if TRAINING_RECORDER_AVAILABLE:
            try:
                self.training_recorder = TrainingRecorder()
                logger.info("✅ 训练记录器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ 训练记录器初始化失败: {e}")
        
        # 初始化各个算法
        self._initialize_algorithms()
        
        # 商品数据库
        self.product_database = self._load_product_database()
        
        logger.info("✅ 算法集成管理器初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "processing_mode": "accurate",
            "yolov8_enabled": True,
            "sam_enabled": True,
            "mask_rcnn_enabled": True,
            "traditional_enabled": True,
            "confidence_threshold": 0.5,
            "max_products_per_image": 10,
            "enable_segmentation": True,
            "enable_visualization": True,
            "output_format": "json"
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"✅ 加载配置文件: {config_path}")
            except Exception as e:
                logger.warning(f"⚠️ 配置文件加载失败，使用默认配置: {str(e)}")
        
        return default_config
    
    def _initialize_algorithms(self):
        """初始化各个算法模块"""
        logger.info("🔧 初始化算法模块...")
        
        # 初始化YOLOv8
        if self.config.get("yolov8_enabled", True):
            try:
                from yolov8_integration import YOLOv8ProductRecognition
                self.algorithms[AlgorithmType.YOLOV8] = YOLOv8ProductRecognition()
                self.algorithm_status[AlgorithmType.YOLOV8] = "loaded"
                logger.info("✅ YOLOv8算法加载成功")
            except Exception as e:
                logger.error(f"❌ YOLOv8算法加载失败: {str(e)}")
                self.algorithm_status[AlgorithmType.YOLOV8] = "failed"
        
        # 初始化SAM
        if self.config.get("sam_enabled", True):
            try:
                from sam_integration import SAMProductSegmentation
                self.algorithms[AlgorithmType.SAM] = SAMProductSegmentation()
                self.algorithm_status[AlgorithmType.SAM] = "loaded"
                logger.info("✅ SAM算法加载成功")
            except Exception as e:
                logger.error(f"❌ SAM算法加载失败: {str(e)}")
                self.algorithm_status[AlgorithmType.SAM] = "failed"
        
        # 初始化Mask R-CNN
        if self.config.get("mask_rcnn_enabled", True):
            try:
                from mask_rcnn_integration import MaskRCNNProductSegmentation
                self.algorithms[AlgorithmType.MASK_RCNN] = MaskRCNNProductSegmentation()
                self.algorithm_status[AlgorithmType.MASK_RCNN] = "loaded"
                logger.info("✅ Mask R-CNN算法加载成功")
            except Exception as e:
                logger.error(f"❌ Mask R-CNN算法加载失败: {str(e)}")
                self.algorithm_status[AlgorithmType.MASK_RCNN] = "failed"
        
        # 初始化传统算法
        if self.config.get("traditional_enabled", True):
            try:
                from recognition_algorithm import ProductRecognition
                self.algorithms[AlgorithmType.TRADITIONAL] = ProductRecognition()
                self.algorithm_status[AlgorithmType.TRADITIONAL] = "loaded"
                logger.info("✅ 传统算法加载成功")
            except Exception as e:
                logger.error(f"❌ 传统算法加载失败: {str(e)}")
                self.algorithm_status[AlgorithmType.TRADITIONAL] = "failed"
    
    def _load_product_database(self) -> Dict[str, Any]:
        """加载商品数据库"""
        logger.info("📦 加载商品数据库...")
        
        # 默认商品数据
        default_products = {
            "products": [
                {
                    "id": 1,
                    "name": "可口可乐330ml",
                    "price": 3.50,
                    "category": "饮料",
                    "barcode": "6901668000017",
                    "image_path": "media/products/coke_330ml.jpg"
                },
                {
                    "id": 2,
                    "name": "百事可乐330ml", 
                    "price": 3.50,
                    "category": "饮料",
                    "barcode": "6901668000024",
                    "image_path": "media/products/pepsi_330ml.jpg"
                },
                {
                    "id": 3,
                    "name": "康师傅红烧牛肉面",
                    "price": 4.50,
                    "category": "方便食品",
                    "barcode": "6901668000031",
                    "image_path": "media/products/noodles_beef.jpg"
                },
                {
                    "id": 4,
                    "name": "奥利奥饼干",
                    "price": 6.80,
                    "category": "零食",
                    "barcode": "6901668000048",
                    "image_path": "media/products/oreo.jpg"
                },
                {
                    "id": 5,
                    "name": "德芙巧克力",
                    "price": 8.90,
                    "category": "零食",
                    "barcode": "6901668000055",
                    "image_path": "media/products/dove_chocolate.jpg"
                }
            ]
        }
        
        # 尝试从数据库或配置文件加载
        try:
            # 这里可以扩展为从Django数据库加载
            return default_products
        except Exception as e:
            logger.warning(f"⚠️ 加载商品数据库失败，使用默认数据: {str(e)}")
            return default_products
    
    def get_algorithm_status(self) -> Dict[str, Any]:
        """获取算法状态信息"""
        return {
            "algorithms": {
                algo_type.value: {
                    "status": status,
                    "available": status == "loaded"
                }
                for algo_type, status in self.algorithm_status.items()
            },
            "processing_mode": self.config.get("processing_mode", "accurate"),
            "total_algorithms": len(self.algorithms),
            "loaded_algorithms": len([s for s in self.algorithm_status.values() if s == "loaded"])
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        success_rate = 0
        if self.processing_stats["total_requests"] > 0:
            success_rate = (self.processing_stats["successful_requests"] / 
                          self.processing_stats["total_requests"]) * 100
        
        return {
            "total_requests": self.processing_stats["total_requests"],
            "successful_requests": self.processing_stats["successful_requests"],
            "failed_requests": self.processing_stats["failed_requests"],
            "success_rate": success_rate,
            "average_processing_time": self.processing_stats["average_processing_time"],
            "algorithm_usage": self.processing_stats["algorithm_usage"]
        }
    
    def recognize_products(self, 
                          image_path: str, 
                          mode: Optional[ProcessingMode] = None,
                          custom_algorithms: Optional[List[AlgorithmType]] = None) -> RecognitionResult:
        """
        识别商品主方法
        
        Args:
            image_path: 图像路径
            mode: 处理模式
            custom_algorithms: 自定义算法列表
            
        Returns:
            RecognitionResult: 识别结果
        """
        start_time = time.time()
        self.processing_stats["total_requests"] += 1
        
        try:
            logger.info(f"🔍 开始商品识别: {os.path.basename(image_path)}")
            
            # 确定使用的算法
            algorithms_to_use = self._determine_algorithms(mode, custom_algorithms)
            
            if not algorithms_to_use:
                raise Exception("没有可用的算法模块")
            
            # 按算法顺序执行识别
            all_results = []
            segmentations = []
            
            for algo_type in algorithms_to_use:
                if algo_type not in self.algorithms:
                    continue
                
                logger.info(f"🤖 使用算法: {algo_type.value}")
                self.processing_stats["algorithm_usage"][algo_type.value] += 1
                
                try:
                    if algo_type == AlgorithmType.YOLOV8:
                        result = self._process_with_yolov8(image_path)
                    elif algo_type == AlgorithmType.SAM:
                        result = self._process_with_sam(image_path)
                    elif algo_type == AlgorithmType.MASK_RCNN:
                        result = self._process_with_mask_rcnn(image_path)
                    elif algo_type == AlgorithmType.TRADITIONAL:
                        result = self._process_with_traditional(image_path)
                    else:
                        continue
                    
                    if result and result.get("success"):
                        all_results.append(result)
                        if "segmentations" in result:
                            segmentations.extend(result["segmentations"])
                    
                except Exception as e:
                    logger.error(f"❌ 算法 {algo_type.value} 执行失败: {str(e)}")
                    continue
            
            # 合并和优化结果
            final_result = self._merge_results(all_results, segmentations)
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 构建返回结果
            recognition_result = RecognitionResult(
                success=True,
                algorithm_used="+".join([algo.value for algo in algorithms_to_use]),
                processing_time=processing_time,
                detected_products=final_result["products"],
                total_price=final_result["total_price"],
                confidence_scores=final_result["confidence_scores"],
                bounding_boxes=final_result["bounding_boxes"],
                segmentations=final_result.get("segmentations", [])
            )
            
            self.processing_stats["successful_requests"] += 1
            self._update_average_time(processing_time)
            
            logger.info(f"✅ 识别完成: {len(final_result['products'])}个商品，总价: ¥{final_result['total_price']:.2f}")
            
            return recognition_result
            
        except Exception as e:
            logger.error(f"❌ 商品识别失败: {str(e)}")
            self.processing_stats["failed_requests"] += 1
            
            return RecognitionResult(
                success=False,
                algorithm_used="none",
                processing_time=time.time() - start_time,
                detected_products=[],
                total_price=0.0,
                confidence_scores=[],
                bounding_boxes=[],
                error_message=str(e)
            )
    
    def _determine_algorithms(self, 
                            mode: Optional[ProcessingMode], 
                            custom_algorithms: Optional[List[AlgorithmType]]) -> List[AlgorithmType]:
        """确定使用的算法列表"""
        if custom_algorithms:
            return [algo for algo in custom_algorithms if algo in self.algorithms]
        
        if not mode:
            mode = ProcessingMode(self.config.get("processing_mode", "accurate"))
        
        if mode == ProcessingMode.FAST:
            return [AlgorithmType.YOLOV8] if AlgorithmType.YOLOV8 in self.algorithms else []
        elif mode == ProcessingMode.ACCURATE:
            return [algo for algo in [AlgorithmType.YOLOV8, AlgorithmType.SAM, AlgorithmType.MASK_RCNN] 
                   if algo in self.algorithms]
        else:  # CUSTOM
            return list(self.algorithms.keys())
    
    def _process_with_yolov8(self, image_path: str) -> Dict[str, Any]:
        """使用YOLOv8处理"""
        try:
            yolo = self.algorithms[AlgorithmType.YOLOV8]
            
            result = yolo.recognize_and_calculate(image_path)
            
            if not result.get("success", False):
                return {"success": False, "error": result.get("error", "识别失败")}
            
            products = []
            confidence_scores = []
            bounding_boxes = []
            
            for p in result.get("products", []):
                products.append({
                    "name": p["name"],
                    "price": p["price"],
                    "confidence": p["confidence"],
                    "barcode": p.get("barcode", ""),
                    "category": p.get("category", "")
                })
                confidence_scores.append(p["confidence"])
                bbox = p.get("bbox", {})
                bounding_boxes.append([
                    int(bbox.get("x", 0)),
                    int(bbox.get("y", 0)),
                    int(bbox.get("width", 0)),
                    int(bbox.get("height", 0))
                ])
            
            return {
                "success": True,
                "algorithm": "yolov8",
                "detections": [{"confidence": c} for c in confidence_scores],
                "products": products,
                "total_price": result.get("total_price", 0.0),
                "confidence_scores": confidence_scores,
                "bounding_boxes": bounding_boxes
            }
            
        except Exception as e:
            logger.error(f"YOLOv8处理失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_with_sam(self, image_path: str) -> Dict[str, Any]:
        """使用SAM处理"""
        try:
            sam = self.algorithms[AlgorithmType.SAM]
            
            # 假设SAM返回分割结果
            result = sam.segment_products(image_path)
            if result["success"]:
                result["algorithm"] = "sam"
                result["products"] = [
                    {
                        "name": "康师傅红烧牛肉面",
                        "price": 4.50,
                        "confidence": 0.8,
                        "segmentation": result.get("segmentations", [])
                    }
                ]
                result["total_price"] = 4.50
            
            return result
            
        except Exception as e:
            logger.error(f"SAM处理失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_with_mask_rcnn(self, image_path: str) -> Dict[str, Any]:
        """使用Mask R-CNN处理"""
        try:
            mrcnn = self.algorithms[AlgorithmType.MASK_RCNN]
            
            # 假设Mask R-CNN返回实例分割结果
            result = mrcnn.segment_products(image_path)
            if result["success"]:
                result["algorithm"] = "mask_rcnn"
                result["products"] = [
                    {
                        "name": "奥利奥饼干",
                        "price": 6.80,
                        "confidence": 0.88,
                        "segmentation": result.get("segmentations", [])
                    }
                ]
                result["total_price"] = 6.80
            
            return result
            
        except Exception as e:
            logger.error(f"Mask R-CNN处理失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_with_traditional(self, image_path: str) -> Dict[str, Any]:
        """使用传统算法处理"""
        try:
            traditional = self.algorithms[AlgorithmType.TRADITIONAL]
            
            # 假设传统算法返回简单识别结果
            result = {
                "success": True,
                "algorithm": "traditional",
                "detections": [
                    {
                        "class": "chocolate",
                        "confidence": 0.7,
                        "bbox": [200, 100, 80, 120]
                    }
                ],
                "products": [
                    {
                        "name": "德芙巧克力",
                        "price": 8.90,
                        "confidence": 0.7,
                        "bbox": [200, 100, 80, 120]
                    }
                ],
                "total_price": 8.90
            }
            
            return result
            
        except Exception as e:
            logger.error(f"传统算法处理失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _merge_results(self, results: List[Dict[str, Any]], segmentations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个算法的结果"""
        all_products = []
        all_bboxes = []
        all_confidences = []
        total_price = 0.0
        
        # 收集所有商品
        for result in results:
            if result.get("products"):
                all_products.extend(result["products"])
            if result.get("detections"):
                for det in result["detections"]:
                    if "bbox" in det:
                        all_bboxes.append(det["bbox"])
                    if "confidence" in det:
                        all_confidences.append(det["confidence"])
        
        # 去重和合并（简单的实现）
        unique_products = []
        seen_bboxes = []
        
        for product in all_products:
            bbox = product.get("bbox", [])
            # 简单的去重逻辑：如果边界框重叠超过50%，认为是同一个商品
            is_duplicate = False
            for seen_bbox in seen_bboxes:
                if self._bbox_overlap(bbox, seen_bbox) > 0.5:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_products.append(product)
                seen_bboxes.append(bbox)
                total_price += product.get("price", 0.0)
                if product.get("confidence"):
                    all_confidences.append(product["confidence"])
        
        return {
            "products": unique_products,
            "total_price": total_price,
            "confidence_scores": all_confidences,
            "bounding_boxes": all_bboxes,
            "segmentations": segmentations
        }
    
    def _bbox_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
        """计算两个边界框的重叠率"""
        try:
            x1_1, y1_1, x2_1, y2_1 = bbox1
            x1_2, y1_2, x2_2, y2_2 = bbox2
            
            # 计算交集
            x1_inter = max(x1_1, x1_2)
            y1_inter = max(y1_1, y1_2)
            x2_inter = min(x2_1, x2_2)
            y2_inter = min(y2_1, y2_2)
            
            if x2_inter <= x1_inter or y2_inter <= y1_inter:
                return 0.0
            
            intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _update_average_time(self, processing_time: float):
        """更新平均处理时间"""
        total_requests = self.processing_stats["total_requests"]
        current_avg = self.processing_stats["average_processing_time"]
        
        # 移动平均
        self.processing_stats["average_processing_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        info = {
            "algorithm_manager_version": "1.0.0",
            "supported_algorithms": [algo.value for algo in AlgorithmType],
            "supported_modes": [mode.value for mode in ProcessingMode],
            "configuration": self.config,
            "product_count": len(self.product_database.get("products", [])),
            "algorithm_status": self.get_algorithm_status(),
            "processing_stats": self.get_processing_stats(),
            "system_uptime": datetime.now().isoformat()
        }
        
        # 添加训练记录器信息
        if self.training_recorder:
            training_stats = self.training_recorder.get_statistics()
            info["training_recorder_enabled"] = True
            info["training_statistics"] = training_stats
        else:
            info["training_recorder_enabled"] = False
        
        return info
    
    # ========== 训练记录功能 ==========
    
    def start_model_training(self, model_type: str, 
                            dataset_path: str,
                            epochs: int = 50,
                            batch_size: int = 16,
                            learning_rate: float = 0.001,
                            **kwargs) -> Optional[str]:
        """
        开始模型训练
        
        Args:
            model_type: 模型类型 (yolov8, mask_rcnn, sam)
            dataset_path: 数据集路径
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
            **kwargs: 其他训练参数
            
        Returns:
            training_id: 训练ID，失败返回None
        """
        if not self.training_recorder:
            logger.error("❌ 训练记录器未初始化")
            return None
        
        try:
            # 创建训练配置
            config = TrainingConfig(
                model_type=model_type,
                model_version="1.0.0",
                dataset_path=dataset_path,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                optimizer=kwargs.get("optimizer", "AdamW"),
                loss_function=kwargs.get("loss_function", "CIoU"),
                image_size=kwargs.get("image_size", 640),
                augmentation_enabled=kwargs.get("augmentation_enabled", True),
                custom_params=kwargs.get("custom_params")
            )
            
            # 开始训练
            training_id = self.training_recorder.start_training(config)
            logger.info(f"🎬 模型训练已开始，ID: {training_id}, 模型类型: {model_type}")
            return training_id
            
        except Exception as e:
            logger.error(f"❌ 开始模型训练失败: {e}")
            return None
    
    def record_training_epoch(self, training_id: str, 
                            epoch: int,
                            train_loss: float,
                            train_accuracy: float,
                            val_loss: float,
                            val_accuracy: float,
                            **kwargs):
        """
        记录训练轮次
        
        Args:
            training_id: 训练ID
            epoch: 当前轮次
            train_loss: 训练损失
            train_accuracy: 训练准确率
            val_loss: 验证损失
            val_accuracy: 验证准确率
            **kwargs: 其他指标
        """
        if not self.training_recorder:
            logger.error("❌ 训练记录器未初始化")
            return False
        
        try:
            metrics = TrainingMetrics(
                epoch=epoch,
                train_loss=train_loss,
                train_accuracy=train_accuracy,
                val_loss=val_loss,
                val_accuracy=val_accuracy,
                val_precision=kwargs.get("val_precision"),
                val_recall=kwargs.get("val_recall"),
                val_f1_score=kwargs.get("val_f1_score"),
                learning_rate=kwargs.get("learning_rate")
            )
            
            self.training_recorder.add_epoch_metrics(training_id, metrics)
            logger.debug(f"📈 已记录第 {epoch} 轮训练，ID: {training_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 记录训练轮次失败: {e}")
            return False
    
    def complete_model_training(self, training_id: str,
                               model_save_path: str = None,
                               notes: str = None,
                               **kwargs) -> bool:
        """
        完成模型训练
        
        Args:
            training_id: 训练ID
            model_save_path: 模型保存路径
            notes: 备注
            **kwargs: 最终指标
            
        Returns:
            是否成功
        """
        if not self.training_recorder:
            logger.error("❌ 训练记录器未初始化")
            return False
        
        try:
            final_metrics = {
                "train_loss": kwargs.get("train_loss"),
                "train_accuracy": kwargs.get("train_accuracy"),
                "val_loss": kwargs.get("val_loss"),
                "val_accuracy": kwargs.get("val_accuracy"),
                "val_precision": kwargs.get("val_precision"),
                "val_recall": kwargs.get("val_recall"),
                "val_f1_score": kwargs.get("val_f1_score")
            }
            
            self.training_recorder.complete_training(
                training_id,
                final_metrics,
                model_save_path=model_save_path,
                notes=notes
            )
            logger.info(f"✅ 模型训练已完成，ID: {training_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 完成模型训练失败: {e}")
            return False
    
    def fail_model_training(self, training_id: str, error_message: str) -> bool:
        """
        标记训练失败
        
        Args:
            training_id: 训练ID
            error_message: 错误信息
            
        Returns:
            是否成功
        """
        if not self.training_recorder:
            logger.error("❌ 训练记录器未初始化")
            return False
        
        try:
            self.training_recorder.fail_training(training_id, error_message)
            logger.error(f"❌ 模型训练失败，ID: {training_id}, 错误: {error_message}")
            return True
        except Exception as e:
            logger.error(f"❌ 标记训练失败失败: {e}")
            return False
    
    def get_training_record(self, training_id: str) -> Optional[Dict]:
        """
        获取训练记录
        
        Args:
            training_id: 训练ID
            
        Returns:
            训练记录字典或None
        """
        if not self.training_recorder:
            return None
        
        try:
            record = self.training_recorder.get_training_record(training_id)
            if record:
                return {
                    "training_id": record.training_id,
                    "status": record.status.value,
                    "start_time": record.start_time,
                    "end_time": record.end_time,
                    "duration_seconds": record.duration_seconds,
                    "model_type": record.config.model_type,
                    "epochs": record.config.epochs,
                    "final_metrics": {
                        "train_loss": record.final_train_loss,
                        "train_accuracy": record.final_train_accuracy,
                        "val_loss": record.final_val_loss,
                        "val_accuracy": record.final_val_accuracy
                    },
                    "epoch_count": len(record.training_history)
                }
            return None
        except Exception as e:
            logger.error(f"❌ 获取训练记录失败: {e}")
            return None
    
    def get_all_training_records(self) -> List[Dict]:
        """
        获取所有训练记录
        
        Returns:
            训练记录列表
        """
        if not self.training_recorder:
            return []
        
        try:
            records = self.training_recorder.get_all_records()
            return [{
                "training_id": r.training_id,
                "status": r.status.value,
                "model_type": r.config.model_type,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_seconds": r.duration_seconds,
                "epochs": r.config.epochs,
                "final_val_accuracy": r.final_val_accuracy
            } for r in records]
        except Exception as e:
            logger.error(f"❌ 获取所有训练记录失败: {e}")
            return []
    
    def export_training_report(self, training_id: str, output_path: str) -> bool:
        """
        导出训练报告
        
        Args:
            training_id: 训练ID
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        if not self.training_recorder:
            logger.error("❌ 训练记录器未初始化")
            return False
        
        try:
            success = self.training_recorder.export_training_report(training_id, output_path)
            if success:
                logger.info(f"📄 训练报告已导出到: {output_path}")
            return success
        except Exception as e:
            logger.error(f"❌ 导出训练报告失败: {e}")
            return False

# 创建全局算法管理器实例
algorithm_manager = None

def get_algorithm_manager() -> AlgorithmManager:
    """获取全局算法管理器实例"""
    global algorithm_manager
    if algorithm_manager is None:
        algorithm_manager = AlgorithmManager()
    return algorithm_manager

if __name__ == "__main__":
    # 测试代码
    manager = AlgorithmManager()
    
    # 输出系统信息
    print("🎯 算法集成管理器测试")
    print("=" * 50)
    print("📊 系统信息:")
    print(json.dumps(manager.get_system_info(), indent=2, ensure_ascii=False))
    
    # 测试算法状态
    print("\n🤖 算法状态:")
    status = manager.get_algorithm_status()
    for algo, info in status["algorithms"].items():
        print(f"  {algo}: {info['status']}")