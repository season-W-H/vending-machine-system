#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法识别视图
提供Web界面和API接口
"""

import os
import sys
import json
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from products.algorithm_manager import get_algorithm_manager
from products.views.algorithm_api_views import AlgorithmAPIView

logger = logging.getLogger(__name__)

class AlgorithmViews:
    """算法识别视图类"""
    
    def __init__(self):
        """初始化视图"""
        self.manager = get_algorithm_manager()
        self.api_view = AlgorithmAPIView()
        logger.info("🚀 算法识别视图初始化完成")
    
    @staticmethod
    def recognition_api(request: HttpRequest) -> JsonResponse:
        """
        识别API接口
        
        GET: 返回API使用说明
        POST: 执行商品识别
        """
        if request.method == 'GET':
            return JsonResponse({
                "success": True,
                "message": "商品识别API",
                "usage": {
                    "method": "POST",
                    "endpoint": "/products/api/recognition/",
                    "parameters": {
                        "image": "图像文件或base64编码",
                        "mode": "处理模式 (fast/accurate/custom)",
                        "algorithms": "自定义算法列表",
                        "save_result": "是否保存结果"
                    },
                    "response": {
                        "success": "操作是否成功",
                        "data": "识别结果数据",
                        "timestamp": "处理时间戳"
                    }
                }
            })
        
        elif request.method == 'POST':
            return AlgorithmAPIView.recognize_products(request)
    
    @staticmethod
    def recognition_status(request: HttpRequest) -> JsonResponse:
        """识别状态API"""
        return AlgorithmAPIView.system_status(request)
    
    @staticmethod
    def algorithm_comparison(request: HttpRequest) -> JsonResponse:
        """算法对比API"""
        return AlgorithmAPIView.algorithm_comparison(request)
    
    @staticmethod
    def batch_recognition(request: HttpRequest) -> JsonResponse:
        """批量识别API"""
        return AlgorithmAPIView.batch_process(request)
    
    @staticmethod
    def segmentation_api(request: HttpRequest) -> JsonResponse:
        """
        分割API接口
        
        GET: 返回API使用说明
        POST: 执行图像分割
        """
        if request.method == 'GET':
            return JsonResponse({
                "success": True,
                "message": "图像分割API",
                "usage": {
                    "method": "POST",
                    "endpoint": "/products/api/segmentation/",
                    "parameters": {
                        "image": "图像文件或base64编码",
                        "algorithm": "分割算法 (sam/mask_rcnn/auto)",
                        "save_result": "是否保存结果"
                    },
                    "response": {
                        "success": "操作是否成功",
                        "data": "分割结果数据",
                        "timestamp": "处理时间戳"
                    }
                }
            })
        
        elif request.method == 'POST':
            return AlgorithmAPIView.segment_image(request)
    
    @staticmethod
    def segmentation_status(request: HttpRequest) -> JsonResponse:
        """分割状态API"""
        return AlgorithmAPIView.system_status(request)

# 创建视图实例
algorithm_views = AlgorithmViews()

# Django视图函数
def recognition_api_view(request):
    """识别API视图"""
    return AlgorithmViews.recognition_api(request)

def recognition_status_view(request):
    """识别状态视图"""
    return AlgorithmViews.recognition_status(request)

def algorithm_comparison_view(request):
    """算法对比视图"""
    return AlgorithmViews.algorithm_comparison(request)

def batch_recognition_view(request):
    """批量识别视图"""
    return AlgorithmViews.batch_recognition(request)

def segmentation_api_view(request):
    """分割API视图"""
    return AlgorithmViews.segmentation_api(request)

def segmentation_status_view(request):
    """分割状态视图"""
    return AlgorithmViews.segmentation_status(request)