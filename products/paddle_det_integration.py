"""
PaddleDetection 商品识别模块
使用 Paddle Inference 进行推理
"""

import cv2
import numpy as np
import os
import logging
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

CLASS_NAMES = [
    "百岁山", "芬达", "加多宝", "康师傅红茶", "维他命水",
    "脉动", "美汁源", "统一阿萨姆（绿茶）", "统一阿萨姆（原味）", "营养快线"
]

CATEGORY_MAPPING = {
    "百岁山": "bss",
    "芬达": "fd",
    "加多宝": "jdb",
    "康师傅红茶": "ksfh",
    "维他命水": "llds",
    "脉动": "md",
    "美汁源": "mzy",
    "统一阿萨姆（绿茶）": "tycl",
    "统一阿萨姆（原味）": "tyyc",
    "营养快线": "yykx"
}

PRODUCTS_DATABASE = [
    {"name": "百岁山", "price": 3.50, "barcode": "6901028155102", "category": "bss"},
    {"name": "芬达", "price": 3.50, "barcode": "6901028155103", "category": "fd"},
    {"name": "加多宝", "price": 4.50, "barcode": "6901028155104", "category": "jdb"},
    {"name": "康师傅红茶", "price": 4.00, "barcode": "6901028155105", "category": "ksfh"},
    {"name": "维他命水", "price": 5.50, "barcode": "6901028155106", "category": "llds"},
    {"name": "脉动", "price": 5.00, "barcode": "6901028155107", "category": "md"},
    {"name": "美汁源", "price": 4.80, "barcode": "6901028155108", "category": "mzy"},
    {"name": "统一阿萨姆（绿茶）", "price": 3.80, "barcode": "6901028155109", "category": "tycl"},
    {"name": "统一阿萨姆（原味）", "price": 3.80, "barcode": "6901028155110", "category": "tyyc"},
    {"name": "营养快线", "price": 5.50, "barcode": "6901028155111", "category": "yykx"},
]


class PaddleDetProductRecognition:
    """基于 PaddleDetection 的商品识别类"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_dir: Optional[str] = None, 
                 conf_threshold: float = 0.5, auto_load: bool = False):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        logger.info("初始化 PaddleDetection 商品识别器")
        
        self.predictor = None
        self.model_loaded = False
        self.conf_threshold = conf_threshold
        self.target_size = 640
        
        base_dir = Path(__file__).parent.parent
        self.model_dir = model_dir or str(base_dir / "onnx_model_legacy")
        
        self.pdmodel_path = os.path.join(self.model_dir, "model.pdmodel")
        self.pdiparams_path = os.path.join(self.model_dir, "model.pdiparams")
        self.json_path = os.path.join(self.model_dir, "model.json")
        
        self.products_database = PRODUCTS_DATABASE
        self.class_names = CLASS_NAMES
        
        if auto_load:
            self._load_model()
        
        self._initialized = True
    
    def _load_model(self, force_reload: bool = False) -> bool:
        if self.model_loaded and not force_reload:
            return True
        
        try:
            import paddle
            paddle.set_device('cpu')
            
            logger.info(f"加载推理模型: {self.model_dir}")
            
            if os.path.exists(self.json_path) and not os.path.exists(self.pdmodel_path):
                logger.info("检测到 PIR 格式模型，转换为 pdmodel 格式...")
                import shutil
                shutil.copy(self.json_path, self.pdmodel_path)
                logger.info(f"已创建: {self.pdmodel_path}")
            
            if not os.path.exists(self.pdmodel_path):
                logger.error(f"模型文件不存在: {self.pdmodel_path}")
                return False
            
            if not os.path.exists(self.pdiparams_path):
                logger.error(f"参数文件不存在: {self.pdiparams_path}")
                return False
            
            logger.info("创建推理配置...")
            config = paddle.inference.Config(self.pdmodel_path, self.pdiparams_path)
            config.disable_gpu()
            config.switch_ir_optim(False)
            config.enable_memory_optim()
            config.switch_use_feed_fetch_ops(False)
            
            logger.info("创建推理引擎...")
            self.predictor = paddle.inference.create_predictor(config)
            
            self.input_names = self.predictor.get_input_names()
            self.output_names = self.predictor.get_output_names()
            
            logger.info(f"模型加载成功")
            logger.info(f"输入: {self.input_names}")
            logger.info(f"输出: {self.output_names}")
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            self.model_loaded = False
            return False
    
    def _preprocess(self, image: np.ndarray):
        """预处理图像"""
        self.orig_shape = image.shape[:2]
        
        h, w = image.shape[:2]
        self.scale_x = self.target_size / w
        self.scale_y = self.target_size / h
        
        resized = cv2.resize(image, (self.target_size, self.target_size))
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        resized = resized.astype(np.float32) / 255.0
        resized = np.transpose(resized, (2, 0, 1))
        resized = np.expand_dims(resized, axis=0)
        
        scale_factor = np.array([[self.scale_y, self.scale_x]], dtype=np.float32)
        
        return resized, scale_factor
    
    def _postprocess(self, outputs: List[np.ndarray]) -> List[Dict]:
        """后处理检测结果"""
        results = []
        
        try:
            if len(outputs) < 2:
                logger.warning(f"输出数量不足: {len(outputs)}")
                return results
            
            bbox = outputs[0]
            bbox_num = outputs[1]
            
            logger.info(f"bbox shape: {bbox.shape}")
            logger.info(f"bbox_num shape: {bbox_num.shape}")
            
            num_boxes = int(bbox_num[0]) if len(bbox_num) > 0 else 0
            if num_boxes == 0:
                return results
            
            boxes = bbox[:num_boxes]
            
            for i in range(num_boxes):
                box = boxes[i]
                
                class_id = int(box[0])
                score = float(box[1])
                x1, y1, x2, y2 = box[2:6]
                
                if score < self.conf_threshold:
                    continue
                
                orig_h, orig_w = self.orig_shape
                
                x1 = int(x1 / self.scale_x)
                y1 = int(y1 / self.scale_y)
                x2 = int(x2 / self.scale_x)
                y2 = int(y2 / self.scale_y)
                
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))
                
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f'class_{class_id}'
                
                results.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': score,
                    'bbox': [x1, y1, x2, y2]
                })
        except Exception as e:
            logger.error(f"后处理失败: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def detect_products(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测图像中的商品"""
        if not self.model_loaded:
            if not self._load_model():
                return []
        
        try:
            input_image, scale_factor = self._preprocess(image)
            
            input_tensor = self.predictor.get_input_handle(self.input_names[0])
            input_tensor.copy_from_cpu(input_image)
            
            if len(self.input_names) > 1:
                scale_tensor = self.predictor.get_input_handle(self.input_names[1])
                scale_tensor.copy_from_cpu(scale_factor)
            
            self.predictor.run()
            
            outputs = []
            for name in self.output_names:
                output_tensor = self.predictor.get_output_handle(name)
                outputs.append(output_tensor.copy_to_cpu())
            
            detections = self._postprocess(outputs)
            
            results = []
            for det in detections:
                class_name = det['class_name']
                category = CATEGORY_MAPPING.get(class_name, "unknown")
                
                product_info = next(
                    (p for p in self.products_database if p['category'] == category),
                    {"name": class_name, "price": 0.0, "barcode": "", "category": category}
                )
                
                results.append({
                    'product_name': product_info['name'],
                    'confidence': det['confidence'],
                    'bbox': det['bbox'],
                    'price': product_info['price'],
                    'barcode': product_info['barcode'],
                    'category': category,
                    'class_id': det['class_id']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"检测失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            'model_type': 'PaddleDetection PP-YOLOE+',
            'model_dir': self.model_dir,
            'model_loaded': self.model_loaded,
            'num_classes': len(self.class_names),
            'classes': self.class_names,
            'confidence_threshold': self.conf_threshold,
            'input_size': self.target_size
        }


paddle_det_recognition = PaddleDetProductRecognition()
