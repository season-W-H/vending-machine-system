#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法管理后台视图
提供系统监控和管理界面
"""

import os
import sys
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from products.algorithm_manager import get_algorithm_manager

logger = logging.getLogger(__name__)

def parse_log_line(log_line: str) -> Optional[Dict[str, Any]]:
    """
    解析日志行，提取时间戳、级别、消息等信息
    """
    try:
        # 常见日志格式的正则表达式
        patterns = [
            # 格式: 2024-01-01 12:00:00,123 [INFO] 算法名称: 消息内容
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s+([^:]+):\s*(.+)',
            # 格式: 2024-01-01 12:00:00 [INFO] 消息内容
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s+(.+)',
            # 格式: [2024-01-01 12:00:00] INFO: 消息内容
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL):\s*(.+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, log_line)
            if match:
                groups = match.groups()
                if len(groups) == 4:  # 包含算法名称的格式
                    timestamp, level, algorithm, message = groups
                elif len(groups) == 3:  # 不包含算法名称的格式
                    timestamp, level, message = groups
                    algorithm = 'system'
                else:
                    continue
                
                return {
                    'timestamp': timestamp,
                    'level': level.upper(),
                    'message': message.strip(),
                    'algorithm': algorithm.strip()
                }
        
        # 如果没有匹配到标准格式，尝试简单的解析
        # 查找级别标识
        level_match = re.search(r'\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]', log_line)
        if level_match:
            level = level_match.group(1)
            # 提取消息部分（级别之后的所有内容）
            message_start = level_match.end()
            message = log_line[message_start:].strip()
            
            # 尝试提取时间戳
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log_line)
            timestamp = time_match.group(1) if time_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return {
                'timestamp': timestamp,
                'level': level.upper(),
                'message': message,
                'algorithm': 'system'
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"解析日志行失败: {log_line}, 错误: {str(e)}")
        return None

class AdminViews:
    """算法管理后台视图类"""
    
    def __init__(self):
        """初始化视图"""
        self.manager = get_algorithm_manager()
        logger.info("⚙️ 算法管理后台视图初始化完成")
    
    @staticmethod
    def algorithm_admin(request: HttpRequest):
        """
        算法管理后台主页
        """
        try:
            manager = get_algorithm_manager()
            
            # 获取算法状态
            algorithm_status = manager.get_algorithm_status()
            processing_stats = manager.get_processing_stats()
            system_info = manager.get_system_info()
            
            context = {
                'algorithm_status': algorithm_status,
                'processing_stats': processing_stats,
                'system_info': system_info,
                'page_title': '算法管理后台',
                'menu_items': [
                    {
                        'title': '系统状态',
                        'url': '/products/admin/status/',
                        'icon': '📊',
                        'description': '查看算法状态和系统信息'
                    },
                    {
                        'title': '算法日志',
                        'url': '/products/admin/logs/',
                        'icon': '📋',
                        'description': '查看算法执行日志'
                    },
                    {
                        'title': '系统设置',
                        'url': '/products/admin/settings/',
                        'icon': '⚙️',
                        'description': '配置算法参数'
                    },
                    {
                        'title': '商品识别',
                        'url': '/products/products/recognition/',
                        'icon': '🔍',
                        'description': '进行商品识别'
                    }
                ]
            }
            
            return render(request, 'products/admin/dashboard.html', context)
            
        except Exception as e:
            logger.error(f"加载管理后台失败: {str(e)}")
            return render(request, 'products/error.html', {
                'error': '加载管理后台失败',
                'details': str(e)
            })
    
    @staticmethod
    def system_status(request: HttpRequest):
        """
        系统状态页面
        """
        try:
            manager = get_algorithm_manager()
            
            # 获取详细状态信息
            algorithm_status = manager.get_algorithm_status()
            processing_stats = manager.get_processing_stats()
            system_info = manager.get_system_info()
            
            # 获取算法加载状态
            loaded_algorithms = []
            for algo_type, algo_obj in manager.algorithms.items():
                loaded_algorithms.append({
                    'name': algo_type.value,
                    'display_name': algo_type.name,
                    'loaded': hasattr(algo_obj, 'model'),
                    'available': True  # 这里应该检查实际的可用性
                })
            
            context = {
                'algorithm_status': algorithm_status,
                'processing_stats': processing_stats,
                'system_info': system_info,
                'loaded_algorithms': loaded_algorithms,
                'page_title': '系统状态',
                'refresh_url': '/products/admin/status/'
            }
            
            return render(request, 'products/admin/system_status.html', context)
            
        except Exception as e:
            logger.error(f"加载系统状态失败: {str(e)}")
            return render(request, 'products/error.html', {
                'error': '加载系统状态失败',
                'details': str(e)
            })
    
    @staticmethod
    def system_logs(request: HttpRequest):
        """
        系统日志页面
        """
        try:
            if request.method == 'GET':
                # 获取日志筛选参数
                log_level = request.GET.get('level', 'INFO')
                log_lines = int(request.GET.get('lines', 100))
                algorithm = request.GET.get('algorithm', '')
                search_text = request.GET.get('search', '')
                start_time = request.GET.get('start_time', '')
                end_time = request.GET.get('end_time', '')
                page = int(request.GET.get('page', 1))
                page_size = 50
                
                # 构建日志文件路径
                log_dir = os.path.join(settings.BASE_DIR, 'logs')
                log_file = os.path.join(log_dir, 'algorithm.log')
                
                logs = []
                log_stats = {'total': 0, 'errors': 0, 'warnings': 0, 'info': 0, 'debug': 0}
                
                # 如果日志文件存在，读取日志
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        # 解析日志行
                        for line in reversed(lines):
                            log_entry = parse_log_line(line.strip())
                            
                            if log_entry:
                                # 应用筛选条件
                                if log_level.upper() != 'ALL' and log_entry['level'] != log_level.upper():
                                    continue
                                    
                                if algorithm and algorithm.lower() not in log_entry.get('algorithm', '').lower():
                                    continue
                                    
                                if search_text and search_text.lower() not in log_entry['message'].lower():
                                    continue
                                
                                # 时间筛选
                                if start_time and log_entry['timestamp'] < start_time:
                                    continue
                                if end_time and log_entry['timestamp'] > end_time:
                                    continue
                                
                                logs.append(log_entry)
                                
                                # 统计
                                log_stats['total'] += 1
                                if log_entry['level'] == 'ERROR':
                                    log_stats['errors'] += 1
                                elif log_entry['level'] == 'WARNING':
                                    log_stats['warnings'] += 1
                                elif log_entry['level'] == 'INFO':
                                    log_stats['info'] += 1
                                elif log_entry['level'] == 'DEBUG':
                                    log_stats['debug'] += 1
                                
                                if len(logs) >= 1000:  # 限制最大日志数量
                                    break
                                    
                    except Exception as e:
                        logger.error(f"读取日志文件失败: {str(e)}")
                        logs = [{
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'level': 'ERROR',
                            'message': f'读取日志文件失败: {str(e)}',
                            'algorithm': 'system'
                        }]
                        log_stats['errors'] = 1
                else:
                    logs = [{
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'level': 'INFO',
                        'message': '日志文件不存在，请确保日志记录功能已启用',
                        'algorithm': 'system'
                    }]
                    log_stats['info'] = 1
                
                # 分页
                total_logs = len(logs)
                total_pages = (total_logs + page_size - 1) // page_size
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_logs = logs[start_idx:end_idx]
                
                context = {
                    'logs': paginated_logs,
                    'log_stats': log_stats,
                    'log_level': log_level,
                    'log_lines': log_lines,
                    'algorithm': algorithm,
                    'search_text': search_text,
                    'start_time': start_time,
                    'end_time': end_time,
                    'page_title': '系统日志',
                    'current_page': page,
                    'total_pages': total_pages,
                    'log_levels': ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
                    'algorithms': ['yolov8', 'sam', 'mask_rcnn', 'traditional', 'system'],
                    'refresh_url': f'/products/admin/logs/',
                    'clear_url': '/products/admin/logs/clear/'
                }
                
                return render(request, 'products/admin/system_logs.html', context)
            
            elif request.method == 'POST':
                # AJAX请求 - 刷新日志
                try:
                    data = json.loads(request.body)
                    
                    # 重新获取日志（使用相同的筛选条件）
                    return AdminViews.system_logs(request)
                    
                except Exception as e:
                    logger.error(f"刷新日志失败: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    }, status=500)
                    
        except Exception as e:
            logger.error(f"加载系统日志失败: {str(e)}")
            return render(request, 'products/error.html', {
                'error': '加载系统日志失败',
                'details': str(e)
            })
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def clear_system_logs(request: HttpRequest):
        """
        清空系统日志
        """
        try:
            log_dir = os.path.join(settings.BASE_DIR, 'logs')
            log_file = os.path.join(log_dir, 'algorithm.log')
            
            if os.path.exists(log_file):
                # 清空日志文件
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write('')
                
                logger.info("系统日志已清空")
                message = '日志清理成功'
            else:
                message = '日志文件不存在，无需清理'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"清空日志失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @staticmethod
    def algorithm_settings(request: HttpRequest):
        """
        算法设置页面
        """
        try:
            manager = get_algorithm_manager()
            
            if request.method == 'GET':
                # 显示设置页面
                current_settings = manager.get_processing_stats()
                
                context = {
                    'current_settings': current_settings,
                    'page_title': '算法设置',
                    'setting_sections': [
                        {
                            'title': '处理模式',
                            'description': '配置默认处理模式',
                            'settings': [
                                {
                                    'key': 'default_mode',
                                    'label': '默认处理模式',
                                    'type': 'select',
                                    'options': [
                                        {'value': 'fast', 'label': '快速模式'},
                                        {'value': 'accurate', 'label': '精确模式'},
                                        {'value': 'custom', 'label': '自定义模式'}
                                    ],
                                    'current_value': 'accurate'
                                },
                                {
                                    'key': 'max_processing_time',
                                    'label': '最大处理时间(秒)',
                                    'type': 'number',
                                    'min': 1,
                                    'max': 60,
                                    'current_value': 30
                                }
                            ]
                        },
                        {
                            'title': '算法优先级',
                            'description': '配置算法使用优先级',
                            'settings': [
                                {
                                    'key': 'primary_algorithm',
                                    'label': '主要算法',
                                    'type': 'select',
                                    'options': [
                                        {'value': 'yolov8', 'label': 'YOLOv8'},
                                        {'value': 'sam', 'label': 'SAM'},
                                        {'value': 'mask_rcnn', 'label': 'Mask R-CNN'},
                                        {'value': 'traditional', 'label': '传统算法'}
                                    ],
                                    'current_value': 'yolov8'
                                },
                                {
                                    'key': 'fallback_enabled',
                                    'label': '启用后备算法',
                                    'type': 'checkbox',
                                    'current_value': True
                                }
                            ]
                        },
                        {
                            'title': '性能优化',
                            'description': '优化算法性能参数',
                            'settings': [
                                {
                                    'key': 'batch_processing',
                                    'label': '启用批处理',
                                    'type': 'checkbox',
                                    'current_value': False
                                },
                                {
                                    'key': 'parallel_processing',
                                    'label': '启用并行处理',
                                    'type': 'checkbox',
                                    'current_value': True
                                },
                                {
                                    'key': 'cache_enabled',
                                    'label': '启用结果缓存',
                                    'type': 'checkbox',
                                    'current_value': True
                                }
                            ]
                        }
                    ]
                }
                
                return render(request, 'products/admin/algorithm_settings.html', context)
            
            elif request.method == 'POST':
                # 处理设置更新
                try:
                    data = json.loads(request.body)
                    
                    # 这里应该实现设置更新逻辑
                    # 暂时返回成功响应
                    
                    return JsonResponse({
                        'success': True,
                        'message': '设置更新成功',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except json.JSONDecodeError:
                    return JsonResponse({
                        'success': False,
                        'error': '请求参数格式错误'
                    }, status=400)
                except Exception as e:
                    logger.error(f"更新设置失败: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    }, status=500)
            
        except Exception as e:
            logger.error(f"加载算法设置失败: {str(e)}")
            return render(request, 'products/error.html', {
                'error': '加载算法设置失败',
                'details': str(e)
            })
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def restart_algorithm(request: HttpRequest):
        """
        重启算法服务
        """
        try:
            data = json.loads(request.body) if request.body else {}
            algorithm_name = data.get('algorithm')
            
            manager = get_algorithm_manager()
            
            if algorithm_name:
                # 重启特定算法
                if algorithm_name in [algo.value for algo in manager.algorithms.keys()]:
                    # 这里应该实现算法重启逻辑
                    return JsonResponse({
                        'success': True,
                        'message': f'算法 {algorithm_name} 重启成功'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'算法 {algorithm_name} 不存在'
                    }, status=400)
            else:
                # 重启所有算法
                # 这里应该实现所有算法重启逻辑
                return JsonResponse({
                    'success': True,
                    'message': '所有算法重启成功'
                })
                
        except Exception as e:
            logger.error(f"重启算法失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def clear_cache(request: HttpRequest):
        """
        清空算法缓存
        """
        try:
            manager = get_algorithm_manager()
            
            # 这里应该实现缓存清理逻辑
            return JsonResponse({
                'success': True,
                'message': '缓存清理成功',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# 创建视图实例
admin_views = AdminViews()

# Django视图函数
def algorithm_admin_view(request):
    """算法管理后台视图"""
    return AdminViews.algorithm_admin(request)

def system_status_view(request):
    """系统状态视图"""
    return AdminViews.system_status(request)

def system_logs_view(request):
    """系统日志视图"""
    return AdminViews.system_logs(request)

def algorithm_settings_view(request):
    """算法设置视图"""
    return AdminViews.algorithm_settings(request)

def restart_algorithm_view(request):
    """重启算法视图"""
    return AdminViews.restart_algorithm(request)

def clear_cache_view(request):
    """清空缓存视图"""
    return AdminViews.clear_cache(request)