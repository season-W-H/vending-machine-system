#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法集成API视图
提供统一的商品识别和分割API接口
"""

import os
import sys
import json
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any

from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import cv2
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from products.algorithm_manager import AlgorithmManager, AlgorithmType, ProcessingMode, get_algorithm_manager

logger = logging.getLogger(__name__)

class AlgorithmAPIView:
    """算法集成API视图类"""
    
    def __init__(self):
        """初始化API视图"""
        self.manager = get_algorithm_manager()
        logger.info("🚀 算法API视图初始化完成")
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["GET"])
    def system_status(request) -> JsonResponse:
        """
        获取系统状态API
        
        GET /api/algorithms/status/
        """
        try:
            manager = get_algorithm_manager()
            
            # 获取算法状态
            algorithm_status = manager.get_algorithm_status()
            processing_stats = manager.get_processing_stats()
            system_info = manager.get_system_info()
            
            response_data = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "algorithm_status": algorithm_status,
                    "processing_stats": processing_stats,
                    "system_info": system_info
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def recognize_products(request) -> JsonResponse:
        """
        商品识别API
        
        POST /api/algorithms/recognize/
        
        参数:
        - image: 图像文件或base64编码的图像
        - mode: 处理模式 (fast/accurate/custom)
        - algorithms: 自定义算法列表 (可选)
        - save_result: 是否保存结果 (可选)
        """
        try:
            manager = get_algorithm_manager()
            
            # 解析请求数据
            request_data = json.loads(request.body) if request.body else {}
            image_data = request_data.get('image')
            mode_str = request_data.get('mode', 'accurate')
            algorithms_str = request_data.get('algorithms', [])
            save_result = request_data.get('save_result', False)
            
            # 解析图像数据
            image_path = None
            if image_data:
                # 如果是base64编码的图像
                if image_data.startswith('data:image'):
                    # 提取base64数据
                    format, imgstr = image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    
                    # 保存临时图像文件
                    image_filename = f"temp_recognition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    image_path = os.path.join(settings.MEDIA_ROOT, 'temp', image_filename)
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    
                    # 解码并保存图像
                    image_data = base64.b64decode(imgstr)
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                        
                elif os.path.exists(image_data):
                    # 如果是文件路径
                    image_path = image_data
                else:
                    return JsonResponse({
                        "success": False,
                        "error": "无效的图像数据",
                        "timestamp": datetime.now().isoformat()
                    }, status=400)
            else:
                return JsonResponse({
                    "success": False,
                    "error": "缺少图像数据",
                    "timestamp": datetime.now().isoformat()
                }, status=400)
            
            # 解析处理模式
            try:
                mode = ProcessingMode(mode_str)
            except ValueError:
                mode = ProcessingMode.ACCURATE
            
            # 解析自定义算法
            custom_algorithms = None
            if algorithms_str:
                custom_algorithms = []
                for algo_str in algorithms_str:
                    try:
                        custom_algorithms.append(AlgorithmType(algo_str))
                    except ValueError:
                        continue
            
            # 执行识别
            logger.info(f"开始商品识别: {os.path.basename(image_path)}")
            result = manager.recognize_products(
                image_path=image_path,
                mode=mode,
                custom_algorithms=custom_algorithms
            )
            
            # 构建响应数据
            response_data = {
                "success": result.success,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "algorithm_used": result.algorithm_used,
                    "processing_time": result.processing_time,
                    "detected_products": result.detected_products,
                    "total_price": result.total_price,
                    "confidence_scores": result.confidence_scores,
                    "bounding_boxes": result.bounding_boxes,
                    "segmentations": result.segmentations or []
                }
            }
            
            if not result.success:
                response_data["error"] = result.error_message
            
            # 保存结果（如果需要）
            if save_result and result.success:
                result_filename = f"recognition_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                result_path = os.path.join(settings.MEDIA_ROOT, 'results', result_filename)
                
                os.makedirs(os.path.dirname(result_path), exist_ok=True)
                
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
                
                response_data["result_saved"] = True
                response_data["result_path"] = f"/media/results/{result_filename}"
            
            # 清理临时文件
            if image_path and 'temp_recognition_' in image_path:
                try:
                    os.remove(image_path)
                except:
                    pass
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"商品识别API失败: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def segment_image(request) -> JsonResponse:
        """
        图像分割API
        
        POST /api/algorithms/segment/
        
        参数:
        - image: 图像文件或base64编码的图像
        - algorithm: 分割算法 (sam/mask_rcnn/auto)
        - save_result: 是否保存结果
        """
        try:
            manager = get_algorithm_manager()
            
            # 解析请求数据
            request_data = json.loads(request.body) if request.body else {}
            image_data = request_data.get('image')
            algorithm_str = request_data.get('algorithm', 'auto')
            save_result = request_data.get('save_result', False)
            
            # 解析图像数据（与recognize_products相同逻辑）
            image_path = None
            if image_data:
                if image_data.startswith('data:image'):
                    format, imgstr = image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    
                    image_filename = f"temp_segmentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    image_path = os.path.join(settings.MEDIA_ROOT, 'temp', image_filename)
                    
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    
                    image_data_decoded = base64.b64decode(imgstr)
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                        
                elif os.path.exists(image_data):
                    image_path = image_data
                else:
                    return JsonResponse({
                        "success": False,
                        "error": "无效的图像数据"
                    }, status=400)
            else:
                return JsonResponse({
                    "success": False,
                    "error": "缺少图像数据"
                }, status=400)
            
            # 执行分割
            logger.info(f"开始图像分割: {os.path.basename(image_path)}")
            
            if algorithm_str == 'sam' and AlgorithmType.SAM in manager.algorithms:
                result = manager.algorithms[AlgorithmType.SAM].segment_products(image_path)
            elif algorithm_str == 'mask_rcnn' and AlgorithmType.MASK_RCNN in manager.algorithms:
                result = manager.algorithms[AlgorithmType.MASK_RCNN].segment_products(image_path)
            else:
                # 使用所有可用的分割算法
                segmentations = []
                
                if AlgorithmType.SAM in manager.algorithms:
                    sam_result = manager.algorithms[AlgorithmType.SAM].segment_products(image_path)
                    if sam_result["success"]:
                        segmentations.append({
                            "algorithm": "sam",
                            "data": sam_result
                        })
                
                if AlgorithmType.MASK_RCNN in manager.algorithms:
                    mrcnn_result = manager.algorithms[AlgorithmType.MASK_RCNN].segment_products(image_path)
                    if mrcnn_result["success"]:
                        segmentations.append({
                            "algorithm": "mask_rcnn",
                            "data": mrcnn_result
                        })
                
                result = {
                    "success": len(segmentations) > 0,
                    "segmentations": segmentations,
                    "backend": "multi_algorithm"
                }
            
            # 构建响应
            response_data = {
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "algorithm_used": algorithm_str,
                    "segmentation_count": result.get("segmentation_count", 0),
                    "backend": result.get("backend", "unknown"),
                    "segmentations": result.get("segmentations", [])
                }
            }
            
            # 保存结果
            if save_result and result.get("success"):
                result_filename = f"segmentation_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                result_path = os.path.join(settings.MEDIA_ROOT, 'results', result_filename)
                
                os.makedirs(os.path.dirname(result_path), exist_ok=True)
                
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
                
                response_data["result_saved"] = True
                response_data["result_path"] = f"/media/results/{result_filename}"
            
            # 清理临时文件
            if image_path and 'temp_segmentation_' in image_path:
                try:
                    os.remove(image_path)
                except:
                    pass
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"图像分割API失败: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["GET"])
    def algorithm_comparison(request) -> JsonResponse:
        """
        算法对比API
        
        GET /api/algorithms/compare/?image_path=/path/to/image&algorithms=yolov8,sam
        """
        try:
            manager = get_algorithm_manager()
            
            image_path = request.GET.get('image_path')
            algorithms_str = request.GET.get('algorithms', '')
            
            if not image_path or not os.path.exists(image_path):
                return JsonResponse({
                    "success": False,
                    "error": "图像文件不存在"
                }, status=400)
            
            # 解析算法列表
            algorithm_types = []
            if algorithms_str:
                for algo_str in algorithms_str.split(','):
                    try:
                        algorithm_types.append(AlgorithmType(algo_str.strip()))
                    except ValueError:
                        continue
            
            if not algorithm_types:
                algorithm_types = list(manager.algorithms.keys())
            
            # 执行算法对比
            comparison_results = {}
            processing_times = {}
            
            for algo_type in algorithm_types:
                if algo_type not in manager.algorithms:
                    continue
                
                import time
                start_time = time.time()
                
                try:
                    if algo_type == AlgorithmType.YOLOV8:
                        result = manager._process_with_yolov8(image_path)
                    elif algo_type == AlgorithmType.SAM:
                        result = manager._process_with_sam(image_path)
                    elif algo_type == AlgorithmType.MASK_RCNN:
                        result = manager._process_with_mask_rcnn(image_path)
                    elif algo_type == AlgorithmType.TRADITIONAL:
                        result = manager._process_with_traditional(image_path)
                    else:
                        continue
                    
                    processing_times[algo_type.value] = time.time() - start_time
                    comparison_results[algo_type.value] = {
                        "success": result.get("success", False),
                        "processing_time": processing_times[algo_type.value],
                        "detection_count": len(result.get("detections", [])),
                        "algorithm_backend": result.get("algorithm", algo_type.value)
                    }
                    
                except Exception as e:
                    comparison_results[algo_type.value] = {
                        "success": False,
                        "error": str(e),
                        "processing_time": time.time() - start_time
                    }
            
            response_data = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "image_path": image_path,
                    "algorithms_tested": [algo.value for algo in algorithm_types],
                    "comparison_results": comparison_results,
                    "processing_times": processing_times
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"算法对比API失败: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def batch_process(request) -> JsonResponse:
        """
        批量处理API
        
        POST /api/algorithms/batch/
        
        参数:
        - images: 图像路径列表
        - mode: 处理模式
        - algorithms: 自定义算法列表
        """
        try:
            manager = get_algorithm_manager()
            
            request_data = json.loads(request.body) if request.body else {}
            image_paths = request_data.get('images', [])
            mode_str = request_data.get('mode', 'fast')
            algorithms_str = request_data.get('algorithms', [])
            
            if not image_paths:
                return JsonResponse({
                    "success": False,
                    "error": "没有提供图像列表"
                }, status=400)
            
            # 解析处理模式
            try:
                mode = ProcessingMode(mode_str)
            except ValueError:
                mode = ProcessingMode.FAST
            
            # 解析算法列表
            custom_algorithms = None
            if algorithms_str:
                custom_algorithms = []
                for algo_str in algorithms_str:
                    try:
                        custom_algorithms.append(AlgorithmType(algo_str))
                    except ValueError:
                        continue
            
            # 批量处理
            results = []
            total_processing_time = 0
            
            for i, image_path in enumerate(image_paths):
                if not os.path.exists(image_path):
                    results.append({
                        "image_index": i,
                        "image_path": image_path,
                        "success": False,
                        "error": "图像文件不存在"
                    })
                    continue
                
                try:
                    import time
                    start_time = time.time()
                    
                    result = manager.recognize_products(
                        image_path=image_path,
                        mode=mode,
                        custom_algorithms=custom_algorithms
                    )
                    
                    processing_time = time.time() - start_time
                    total_processing_time += processing_time
                    
                    results.append({
                        "image_index": i,
                        "image_path": image_path,
                        "success": result.success,
                        "processing_time": processing_time,
                        "algorithm_used": result.algorithm_used,
                        "detected_products": result.detected_products,
                        "total_price": result.total_price,
                        "confidence_scores": result.confidence_scores
                    })
                    
                except Exception as e:
                    results.append({
                        "image_index": i,
                        "image_path": image_path,
                        "success": False,
                        "error": str(e)
                    })
            
            # 计算统计信息
            successful_count = sum(1 for r in results if r.get("success", False))
            success_rate = (successful_count / len(results)) * 100 if results else 0
            
            response_data = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "total_images": len(image_paths),
                    "successful_processed": successful_count,
                    "success_rate": success_rate,
                    "total_processing_time": total_processing_time,
                    "average_processing_time": total_processing_time / len(results) if results else 0,
                    "mode_used": mode_str,
                    "results": results
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"批量处理API失败: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)

# 创建API视图实例
algorithm_api = AlgorithmAPIView()

# Django视图函数
def system_status_view(request):
    """系统状态视图"""
    return AlgorithmAPIView.system_status(request)

def recognize_products_view(request):
    """商品识别视图"""
    return AlgorithmAPIView.recognize_products(request)

def segment_image_view(request):
    """图像分割视图"""
    return AlgorithmAPIView.segment_image(request)

def algorithm_comparison_view(request):
    """算法对比视图"""
    return AlgorithmAPIView.algorithm_comparison(request)

def batch_process_view(request):
    """批量处理视图"""
    return AlgorithmAPIView.batch_process(request)