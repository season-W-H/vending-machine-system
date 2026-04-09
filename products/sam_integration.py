"""
SAM分割模型集成模块 - 优化版
集成Segment Anything Model (SAM)，实现自动图像分割功能
优化点：
- 延迟加载模型
- 更好的错误处理
- 批量分割支持
- 内存优化
"""

import cv2
import numpy as np
import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
import torch
from PIL import Image

# 配置日志记录
logger = logging.getLogger(__name__)

class SAMProductSegmentation:
    """基于SAM的商品分割类 - 优化版"""
    
    # 单例模式
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_type: str = "vit_b", device: str = "auto", 
                 auto_load: bool = False):
        """
        初始化SAM分割器
        
        Args:
            model_type: SAM模型类型 ("vit_b", "vit_l", "vit_h")
            device: 计算设备 ("auto", "cpu", "cuda")
            auto_load: 是否自动加载模型
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        logger.info("🚀 初始化SAM商品分割器（优化版）")
        
        # 初始化模型
        self.predictor = None
        self.model_type = model_type
        self.device = device
        self.model_loaded = False
        self._initialized = False
        
        # 确定设备
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"💻 使用设备: {self.device}")
        
        # 可选：延迟加载模型
        if auto_load:
            self._load_model()
        
        self._initialized = True
    
    def _load_model(self, force_reload: bool = False) -> bool:
        """加载SAM模型 - 优化版
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            模型是否加载成功
        """
        if self.model_loaded and not force_reload:
            logger.info("✅ SAM模型已加载")
            return True
            
        try:
            from segment_anything import SamPredictor, sam_model_registry
            
            logger.info(f"📦 加载SAM模型类型: {self.model_type}")
            
            # 模型文件路径
            model_paths = {
                "vit_b": "sam_vit_b_01ec64.pth",
                "vit_l": "sam_vit_l_0b3195.pth", 
                "vit_h": "sam_vit_h_4b8939.pth"
            }
            
            model_path = model_paths.get(self.model_type, "sam_vit_b_01ec64.pth")
            
            # 检查模型文件是否存在
            if not os.path.exists(model_path):
                logger.warning(f"⚠️ 模型文件不存在: {model_path}")
                logger.info("💡 尝试从默认路径加载...")
                
                # 尝试检查常用路径
                common_paths = [
                    os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", model_path),
                    os.path.join("models", model_path),
                    os.path.join("checkpoints", model_path)
                ]
                
                found = False
                for path in common_paths:
                    if os.path.exists(path):
                        model_path = path
                        found = True
                        break
                
                if not found:
                    logger.warning(f"❌ 所有路径都找不到模型文件")
                    logger.info("📝 请下载模型文件或设置SAM_CHECKPOINT环境变量")
                    self.model_loaded = False
                    return False
            
            # 注册并加载模型
            sam = sam_model_registry[self.model_type](checkpoint=model_path)
            
            # 优化：使用半精度
            if self.device == "cuda":
                sam = sam.half()
                logger.info("⚡ 已启用半精度模式")
            
            sam.to(device=self.device)
            
            # 创建预测器
            self.predictor = SamPredictor(sam)
            self.model_loaded = True
            
            logger.info(f"✅ SAM模型加载成功，使用设备: {self.device}")
            return True
            
        except ImportError as e:
            logger.error("❌ SAM未安装，请运行: pip install segment-anything")
            self.predictor = None
            self.model_loaded = False
            return False
        except FileNotFoundError as e:
            logger.warning(f"⚠️ 模型文件未找到: {e}")
            logger.info("💡 将使用备用分割算法")
            self.predictor = None
            self.model_loaded = False
            return False
        except Exception as e:
            logger.error(f"❌ SAM模型加载失败: {e}")
            self.predictor = None
            self.model_loaded = False
            return False
    
    def _ensure_model_loaded(self):
        """确保模型已加载，如未加载则使用备用算法"""
        if not self.model_loaded or self.predictor is None:
            logger.info("🔄 使用备用分割算法")
            return False
        return True
    
    def preprocess_image(self, image_data: Any) -> Optional[np.ndarray]:
        """
        预处理图像
        
        Args:
            image_data: 图像数据
            
        Returns:
            预处理后的图像
        """
        try:
            # 处理不同类型的输入
            if isinstance(image_data, str):
                if image_data.startswith(('http://', 'https://')):
                    import requests
                    response = requests.get(image_data)
                    image_array = np.frombuffer(response.content, np.uint8)
                    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                else:
                    image = cv2.imread(image_data)
            elif isinstance(image_data, np.ndarray):
                image = image_data
            else:
                logger.error("不支持的图像数据类型")
                return None
            
            if image is None:
                logger.error("无法读取图像")
                return None
            
            # 确保图像格式正确
            if len(image.shape) == 3 and image.shape[2] == 3:
                # PIL图像可能是RGB格式
                if isinstance(image_data, Image.Image):
                    image = cv2.cvtColor(np.array(image_data), cv2.COLOR_RGB2BGR)
            
            logger.info(f"图像预处理完成，尺寸: {image.shape}")
            return image
            
        except Exception as e:
            logger.error(f"图像预处理失败: {str(e)}")
            return None
    
    def generate_prompts_from_detections(self, yolov8_results: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        基于YOLOv8检测结果生成SAM提示点
        
        Args:
            yolov8_results: YOLOv8检测结果
            
        Returns:
            提示点列表 (x, y)
        """
        try:
            prompts = []
            
            for detection in yolov8_results:
                bbox = detection.get("bbox", {})
                x = bbox.get("x", 0) + bbox.get("width", 0) / 2
                y = bbox.get("y", 0) + bbox.get("height", 0) / 2
                
                # 添加中心点作为提示
                prompts.append((int(x), int(y)))
                
                # 也可以添加四个角点作为额外提示
                x1, y1 = int(bbox.get("x", 0)), int(bbox.get("y", 0))
                x2, y2 = int(bbox.get("x", 0) + bbox.get("width", 0)), int(bbox.get("y", 0) + bbox.get("height", 0))
                
                prompts.extend([
                    (x1, y1),      # 左上角
                    (x2, y1),      # 右上角  
                    (x1, y2),      # 左下角
                    (x2, y2)       # 右下角
                ])
            
            logger.info(f"生成了 {len(prompts)} 个提示点")
            return prompts
            
        except Exception as e:
            logger.error(f"生成提示点失败: {str(e)}")
            return []
    
    def segment_products_with_sam(self, image_data: Any, 
                                yolov8_results: Optional[List[Dict[str, Any]]] = None,
                                confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        使用SAM分割商品
        
        Args:
            image_data: 图像数据
            yolov8_results: YOLOv8检测结果，用于生成提示点
            confidence_threshold: 置信度阈值
            
        Returns:
            分割结果
        """
        try:
            logger.info("🧪 开始SAM商品分割")
            
            # 预处理图像
            image = self.preprocess_image(image_data)
            if image is None:
                return self._create_empty_result("图像预处理失败")
            
            # 如果有YOLOv8结果，优先使用
            if yolov8_results:
                # 过滤低置信度的检测结果
                filtered_results = [
                    result for result in yolov8_results 
                    if result.get("confidence", 0) >= confidence_threshold
                ]
                
                if not filtered_results:
                    logger.warning("没有符合置信度要求的检测结果")
                    return self._fallback_segmentation(image, "没有有效的YOLOv8检测结果")
                
                prompts = self.generate_prompts_from_detections(filtered_results)
                
                if self._ensure_model_loaded():
                    # 使用SAM进行分割
                    return self._segment_with_sam(image, prompts, filtered_results)
                else:
                    # 使用备用分割算法
                    return self._fallback_segmentation(image, "SAM模型未加载，使用备用算法")
            else:
                # 没有YOLOv8结果，使用自动分割模式
                if self._ensure_model_loaded():
                    return self._auto_segment_with_sam(image)
                else:
                    return self._fallback_segmentation(image, "SAM模型未加载，使用备用算法")
                    
        except Exception as e:
            logger.error(f"SAM分割失败: {str(e)}")
            return self._create_empty_result(f"SAM分割失败: {str(e)}")
    
    def _segment_with_sam(self, image: np.ndarray, prompts: List[Tuple[int, int]], 
                         detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用SAM进行分割"""
        try:
            # 设置图像
            self.predictor.set_image(image)
            
            segmentation_results = []
            
            for i, (prompt_x, prompt_y) in enumerate(prompts):
                try:
                    # 预测分割掩码
                    masks, scores, logits = self.predictor.predict(
                        point_coords=np.array([[prompt_x, prompt_y]]),
                        point_labels=np.array([1]),
                        multimask_output=True
                    )
                    
                    # 选择最佳掩码
                    best_mask_idx = np.argmax(scores)
                    mask = masks[best_mask_idx]
                    score = scores[best_mask_idx]
                    
                    # 计算掩码面积
                    mask_area = np.sum(mask)
                    
                    # 获取对应的检测结果（如果存在）
                    detection_info = detections[i // 5] if i // 5 < len(detections) else {}
                    
                    segmentation_result = {
                        "mask_id": i,
                        "mask_area": int(mask_area),
                        "confidence": float(score),
                        "mask": mask.tolist(),  # 转换为列表以便JSON序列化
                        "bbox": detection_info.get("bbox", {}),
                        "product_info": detection_info
                    }
                    
                    segmentation_results.append(segmentation_result)
                    
                except Exception as e:
                    logger.warning(f"分割第 {i} 个提示点失败: {str(e)}")
                    continue
            
            # 计算统计信息
            total_mask_area = sum(r["mask_area"] for r in segmentation_results)
            avg_confidence = np.mean([r["confidence"] for r in segmentation_results]) if segmentation_results else 0
            
            result = {
                "success": True,
                "algorithm": "SAM",
                "model_type": self.model_type,
                "device": self.device,
                "segmentation_count": len(segmentation_results),
                "total_mask_area": total_mask_area,
                "average_confidence": round(avg_confidence, 3),
                "segmentations": segmentation_results,
                "image_info": {
                    "height": image.shape[0],
                    "width": image.shape[1],
                    "channels": image.shape[2] if len(image.shape) > 2 else 1
                }
            }
            
            logger.info(f"✅ SAM分割完成: {len(segmentation_results)} 个掩码")
            return result
            
        except Exception as e:
            logger.error(f"SAM分割执行失败: {str(e)}")
            return self._fallback_segmentation(image, f"SAM分割失败: {str(e)}")
    
    def _auto_segment_with_sam(self, image: np.ndarray) -> Dict[str, Any]:
        """使用SAM进行自动分割"""
        try:
            # 设置图像
            self.predictor.set_image(image)
            
            # 生成网格提示点
            height, width = image.shape[:2]
            grid_size = 8  # 网格大小
            
            prompts = []
            for y in range(grid_size, height - grid_size, grid_size):
                for x in range(grid_size, width - grid_size, grid_size):
                    prompts.append((x, y))
            
            logger.info(f"自动分割模式，生成 {len(prompts)} 个提示点")
            
            # 批量预测
            masks, scores, logits = self.predictor.predict(
                point_coords=np.array(prompts),
                point_labels=np.array([1] * len(prompts)),
                multimask_output=True
            )
            
            # 选择最佳掩码组合
            segmentation_results = []
            for i, (mask, score) in enumerate(zip(masks, scores)):
                if score > 0.7:  # 只保留高置信度的掩码
                    mask_area = np.sum(mask)
                    
                    segmentation_result = {
                        "mask_id": i,
                        "mask_area": int(mask_area),
                        "confidence": float(score),
                        "mask": mask.tolist()
                    }
                    segmentation_results.append(segmentation_result)
            
            # 过滤重叠的掩码
            filtered_results = self._filter_overlapping_masks(segmentation_results)
            
            result = {
                "success": True,
                "algorithm": "SAM-Auto",
                "model_type": self.model_type,
                "device": self.device,
                "segmentation_count": len(filtered_results),
                "segmentations": filtered_results,
                "image_info": {
                    "height": image.shape[0],
                    "width": image.shape[1]
                }
            }
            
            logger.info(f"✅ SAM自动分割完成: {len(filtered_results)} 个掩码")
            return result
            
        except Exception as e:
            logger.error(f"SAM自动分割失败: {str(e)}")
            return self._fallback_segmentation(image, f"SAM自动分割失败: {str(e)}")
    
    def _fallback_segmentation(self, image: np.ndarray, reason: str) -> Dict[str, Any]:
        """备用分割算法（传统图像处理）"""
        try:
            logger.info("🔄 使用备用分割算法")
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 应用高斯模糊
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 边缘检测
            edges = cv2.Canny(blurred, 50, 150)
            
            # 查找轮廓
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            segmentation_results = []
            
            for i, contour in enumerate(contours):
                # 计算边界框
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # 过滤小区域
                if area < 1000:
                    continue
                
                # 创建掩码
                mask = np.zeros(gray.shape, np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                
                segmentation_result = {
                    "mask_id": i,
                    "mask_area": int(area),
                    "confidence": 0.5,  # 备用算法的置信度
                    "mask": mask.tolist(),
                    "bbox": {"x": x, "y": y, "width": w, "height": h},
                    "algorithm_note": reason
                }
                
                segmentation_results.append(segmentation_result)
            
            result = {
                "success": True,
                "algorithm": "Fallback-Contour",
                "segmentation_count": len(segmentation_results),
                "total_mask_area": sum(r["mask_area"] for r in segmentation_results),
                "segmentations": segmentation_results,
                "fallback_reason": reason
            }
            
            logger.info(f"✅ 备用分割完成: {len(segmentation_results)} 个掩码")
            return result
            
        except Exception as e:
            logger.error(f"备用分割失败: {str(e)}")
            return self._create_empty_result(f"备用分割失败: {str(e)}")
    
    def _filter_overlapping_masks(self, masks: List[Dict[str, Any]], iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """过滤重叠的掩码"""
        try:
            if len(masks) <= 1:
                return masks
            
            filtered_masks = []
            
            for i, mask_info in enumerate(masks):
                mask1 = np.array(mask_info["mask"])
                
                # 检查是否与已选择的掩码重叠
                overlap = False
                for selected_mask in filtered_masks:
                    mask2 = np.array(selected_mask["mask"])
                    
                    # 计算IoU
                    intersection = np.logical_and(mask1, mask2).sum()
                    union = np.logical_or(mask1, mask2).sum()
                    
                    if union > 0:
                        iou = intersection / union
                        if iou > iou_threshold:
                            overlap = True
                            break
                
                if not overlap:
                    filtered_masks.append(mask_info)
            
            return filtered_masks
            
        except Exception as e:
            logger.error(f"过滤重叠掩码失败: {str(e)}")
            return masks
    
    def _create_empty_result(self, error_message: str) -> Dict[str, Any]:
        """创建空结果"""
        return {
            "success": False,
            "error": error_message,
            "algorithm": "SAM",
            "segmentation_count": 0,
            "segmentations": []
        }
    
    def visualize_segmentation(self, image_data: Any, segmentation_result: Dict[str, Any],
                             output_path: Optional[str] = None) -> Optional[np.ndarray]:
        """
        可视化分割结果
        
        Args:
            image_data: 原始图像
            segmentation_result: 分割结果
            output_path: 输出路径
            
        Returns:
            可视化后的图像
        """
        try:
            # 获取原始图像
            image = self.preprocess_image(image_data)
            if image is None:
                return None
            
            # 创建彩色掩码
            colored_mask = np.zeros_like(image)
            
            # 为每个分割结果分配不同颜色
            colors = [
                (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0)
            ]
            
            for i, segmentation in enumerate(segmentation_result.get("segmentations", [])):
                color = colors[i % len(colors)]
                mask = np.array(segmentation["mask"])
                
                # 应用颜色
                colored_mask[mask > 0] = color
                
                # 绘制边界框（如果有）
                bbox = segmentation.get("bbox", {})
                if bbox:
                    x, y, w, h = int(bbox["x"]), int(bbox["y"]), int(bbox["width"]), int(bbox["height"])
                    cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            
            # 混合原始图像和彩色掩码
            alpha = 0.5
            result_image = cv2.addWeighted(image, 1 - alpha, colored_mask, alpha, 0)
            
            # 添加信息文本
            info_text = f"分割数量: {segmentation_result.get('segmentation_count', 0)}"
            cv2.putText(result_image, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 保存图像
            if output_path:
                cv2.imwrite(output_path, result_image)
                logger.info(f"可视化结果已保存到: {output_path}")
            
            return result_image
            
        except Exception as e:
            logger.error(f"可视化分割结果失败: {str(e)}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_type": "SAM",
            "model_variant": self.model_type,
            "device": self.device,
            "model_loaded": self.model_loaded,
            "predictor_available": self.predictor is not None
        }

# 创建全局实例
sam_segmentation = SAMProductSegmentation()