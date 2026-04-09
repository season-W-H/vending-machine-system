# -*- coding: utf-8 -*-
"""
识别系统视图 - 整合摄像头控制、识别算法和用户界面

该模块提供识别系统的完整API和页面视图，包括摄像头控制、
图像识别、识别结果展示、模型训练等核心功能。
"""

import sys
import base64
import json
import logging
import numpy as np  # 添加numpy导入
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone

# 导入服务模块
from products.services.camera_handler import CameraHandler
from products.services.object_recognition import get_recognizer
from products.services.auto_recognition_flow import auto_flow
from products.services.websocket_consumer import WebSocketManager

# 导入模型
from products.models import Product, VisualRecognitionRecord
from orders.models import Order, OrderItem
from inventory.models import Inventory

logger = logging.getLogger(__name__)


class RecognitionViews:
    """识别系统视图类"""
    
    @staticmethod
    def product_list(request):
        """商品列表页面"""
        products = Product.objects.all().order_by('created_at')
        
        # 搜索过滤
        search_query = request.GET.get('search', '')
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # 分页
        paginator = Paginator(products, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'total_products': products.count(),
        }
        return render(request, 'products/product_list.html', context)
    
    @staticmethod
    def index_page(request):
        """主页 - 系统首页"""
        # 获取统计数据
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        
        # 计算识别准确率
        recognition_records = VisualRecognitionRecord.objects.all()
        if recognition_records.count() > 0:
            successful_recognitions = recognition_records.filter(success=True).count()
            recognition_rate = round((successful_recognitions / recognition_records.count()) * 100, 1)
        else:
            recognition_rate = 0.0
        
        context = {
            'page_title': '智能商品识别系统',
            'total_products': total_products,
            'total_orders': total_orders,
            'recognition_rate': recognition_rate,
            'auto_flow_running': auto_flow.is_running,
        }
        return render(request, 'products/index.html', context)
    
    @staticmethod
    def recognition_page(request):
        """识别页面"""
        context = {
            'page_title': '商品识别',
            'auto_flow_running': auto_flow.is_running,
        }
        return render(request, 'products/recognition.html', context)
    
    @staticmethod
    def inventory_page(request):
        """库存管理页面"""
        inventories = Inventory.objects.all().order_by('product__name')
        
        # 搜索过滤
        search_query = request.GET.get('search', '')
        if search_query:
            inventories = inventories.filter(
                Q(product__name__icontains=search_query) |
                Q(product__description__icontains=search_query)
            )
        
        context = {
            'page_title': '库存管理',
            'inventories': inventories,
            'search_query': search_query,
        }
        return render(request, 'products/inventory.html', context)
    
    @staticmethod
    def orders_page(request):
        """订单管理页面"""
        orders = Order.objects.all().order_by('-created_at')
        
        # 状态过滤
        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # 搜索过滤
        search_query = request.GET.get('search', '')
        if search_query:
            orders = orders.filter(
                Q(id__icontains=search_query) |
                Q(customer_name__icontains=search_query)
            )
        
        # 分页
        paginator = Paginator(orders, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_title': '订单管理',
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
        }
        return render(request, 'products/orders.html', context)
    
    @staticmethod
    def optimization_showcase(request):
        """系统优化展示页面"""
        context = {
            'page_title': '系统优化展示中心',
        }
        return render(request, 'products/optimization_showcase.html', context)
    
    @staticmethod
    def product_api(request):
        """商品API - GET获取列表，POST创建"""
        if request.method == 'GET':
            products = Product.objects.all().values(
                'id', 'name', 'price', 'description', 'image_url', 'created_at'
            )
            return JsonResponse(list(products), safe=False)
        
        elif request.method == 'POST':
            try:
                data = json.loads(request.body)
                product = Product.objects.create(
                    name=data['name'],
                    price=data['price'],
                    description=data.get('description', ''),
                    image_url=data.get('image_url', '')
                )
                return JsonResponse({
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'message': '商品创建成功'
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
    
    @staticmethod
    def product_detail(request, product_id):
        """商品详情页面"""
        product = get_object_or_404(Product, id=product_id)
        
        # 获取商品识别记录
        recognition_records = VisualRecognitionRecord.objects.filter(
            product=product
        ).order_by('-created_at')[:10]
        
        # 获取库存信息
        inventory = getattr(product, 'inventory', None)
        
        context = {
            'product': product,
            'recognition_records': recognition_records,
            'inventory': inventory,
        }
        return render(request, 'products/product_detail.html', context)

    @staticmethod
    def admin_dashboard(request):
        """管理后台仪表板"""
        # 获取统计数据
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        total_recognition_records = VisualRecognitionRecord.objects.count()
        
        # 最近识别记录
        recent_recognitions = VisualRecognitionRecord.objects.order_by('-created_at')[:10]
        
        # 系统状态
        camera_status = 'unknown'
        try:
            camera_handler = CameraHandler()
            camera_status = camera_handler.get_camera_status()
        except:
            pass
        
        context = {
            'total_products': total_products,
            'total_orders': total_orders,
            'total_recognition_records': total_recognition_records,
            'recent_recognitions': recent_recognitions,
            'camera_status': camera_status,
        }
        return render(request, 'products/admin_dashboard.html', context)

    @staticmethod
    def performance_monitor(request):
        """性能监控页面"""
        # 获取性能数据
        performance_data = {
            'total_recognitions': VisualRecognitionRecord.objects.count(),
            'average_confidence': VisualRecognitionRecord.objects.aggregate(
                avg_confidence=Avg('confidence_score')
            )['avg_confidence'] or 0,
            'recent_activities': VisualRecognitionRecord.objects.order_by('-created_at')[:20],
        }
        
        context = {
            'performance_data': performance_data,
        }
        return render(request, 'products/performance_monitor.html', context)

    @staticmethod
    def recognition_monitor(request):
        """识别监控页面"""
        # 获取识别统计
        recognition_stats = VisualRecognitionRecord.objects.values(
            'predicted_label'
        ).annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence_score')
        ).order_by('-count')[:20]
        
        # 最近识别活动
        recent_activity = VisualRecognitionRecord.objects.order_by('-created_at')[:50]
        
        context = {
            'recognition_stats': recognition_stats,
            'recent_activity': recent_activity,
        }
        return render(request, 'products/recognition_monitor.html', context)


# Django视图函数
def index_view(request):
    """主页视图"""
    return RecognitionViews.index_page(request)


def optimization_showcase_view(request):
    """系统优化展示页面视图"""
    return RecognitionViews.optimization_showcase(request)


def product_list_view(request):
    """商品列表视图"""
    return RecognitionViews.product_list(request)


def recognition_page_view(request):
    """识别页面视图"""
    return RecognitionViews.recognition_page(request)


def product_api_view(request):
    """商品API视图"""
    return RecognitionViews.product_api(request)


def product_detail_view(request, product_id):
    """商品详情视图"""
    return RecognitionViews.product_detail(request, product_id)


# 摄像头控制视图
def start_camera_view(request):
    """启动摄像头"""
    try:
        camera_handler = CameraHandler()
        success = camera_handler.start()
        
        if success:
            return JsonResponse({
                'status': 'success',
                'message': '摄像头启动成功'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '摄像头启动失败'
            }, status=500)
            
    except Exception as e:
        logger.error(f"启动摄像头失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'摄像头启动失败: {str(e)}'
        }, status=500)


def stop_camera_view(request):
    """停止摄像头"""
    try:
        camera_handler = CameraHandler()
        camera_handler.stop()
        
        return JsonResponse({
            'status': 'success',
            'message': '摄像头已停止'
        })
        
    except Exception as e:
        logger.error(f"停止摄像头失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'停止摄像头失败: {str(e)}'
        }, status=500)


def get_camera_status_view(request):
    """获取摄像头状态"""
    try:
        camera_handler = CameraHandler()
        status = camera_handler.get_camera_status()
        
        return JsonResponse({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取摄像头状态失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取摄像头状态失败: {str(e)}'
        }, status=500)


def get_frame_view(request):
    """获取摄像头当前帧"""
    try:
        camera_handler = CameraHandler()
        frame = camera_handler.get_frame()
        
        if frame is not None:
            # 将图像数据转换为base64编码
            import io
            from PIL import Image
            
            # 转换numpy数组为PIL图像
            pil_image = Image.fromarray(frame)
            
            # 保存到内存中的字节流
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return JsonResponse({
                'status': 'success',
                'image_data': f'data:image/jpeg;base64,{image_base64}',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '无法获取摄像头帧'
            }, status=500)
            
    except Exception as e:
        logger.error(f"获取摄像头帧失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取摄像头帧失败: {str(e)}'
        }, status=500)


def get_frame_with_detections_view(request):
    """获取带有检测结果的摄像头帧"""
    try:
        camera_handler = CameraHandler()
        frame_with_detections = camera_handler.get_frame_with_detections()
        
        if frame_with_detections is not None:
            # 将图像数据转换为base64编码
            import io
            from PIL import Image
            
            # 转换numpy数组为PIL图像
            pil_image = Image.fromarray(frame_with_detections)
            
            # 保存到内存中的字节流
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return JsonResponse({
                'status': 'success',
                'image_data': f'data:image/jpeg;base64,{image_base64}',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '无法获取摄像头帧或识别结果'
            }, status=500)
            
    except Exception as e:
        logger.error(f"获取检测帧失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取检测帧失败: {str(e)}'
        }, status=500)


def get_recognition_result_view(request):
    """获取识别结果"""
    try:
        from products.services.camera_handler import get_camera_handler
        camera_handler = get_camera_handler()
        results = camera_handler.get_recognition_result()
        
        return JsonResponse({
            'status': 'success',
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取识别结果失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取识别结果失败: {str(e)}'
        }, status=500)


def recognize_from_image_view(request):
    """从上传的图像进行识别"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '仅支持POST请求'
        }, status=405)
    
    try:
        # 获取上传的图像
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({
                'status': 'error',
                'message': '未提供图像文件'
            }, status=400)
        
        # 读取图像并进行识别
        from io import BytesIO
        from PIL import Image
        
        # 打开图像
        pil_image = Image.open(image_file)
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # 使用识别器进行识别
        recognizer = get_recognizer()
        results = recognizer.recognize_objects(np.array(pil_image))
        
        return JsonResponse({
            'status': 'success',
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"图像识别失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'图像识别失败: {str(e)}'
        }, status=500)


def capture_and_recognize_view(request):
    """
    抓拍并识别 - 触发实时识别
    获取当前摄像头帧并进行识别
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '仅支持POST请求'
        }, status=405)
    
    try:
        # 获取摄像头处理器
        camera_handler = CameraHandler()
        
        # 获取当前帧
        frame = camera_handler.get_frame()
        if frame is None:
            return JsonResponse({
                'status': 'error',
                'message': '无法获取摄像头帧'
            }, status=400)
        
        # 触发识别
        camera_handler._recognize_objects()
        
        # 获取识别结果
        results = camera_handler.get_recognition_result()
        
        return JsonResponse({
            'status': 'success',
            'message': '抓拍识别完成',
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"抓拍识别失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'抓拍识别失败: {str(e)}'
        }, status=500)


def get_dataset_info_view(request):
    """获取数据集信息"""
    try:
        # 这里可以返回数据集的基本信息
        dataset_info = {
            'total_products': Product.objects.count(),
            'total_images': VisualRecognitionRecord.objects.count(),
            'last_updated': datetime.now().isoformat()
        }
        
        return JsonResponse({
            'status': 'success',
            'data': dataset_info
        })
        
    except Exception as e:
        logger.error(f"获取数据集信息失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取数据集信息失败: {str(e)}'
        }, status=500)


def train_model_view(request):
    """训练模型"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '仅支持POST请求'
        }, status=405)
    
    try:
        # 这里可以触发模型训练
        # 目前简单返回成功消息
        return JsonResponse({
            'status': 'success',
            'message': '模型训练功能暂未实现',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"模型训练失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'模型训练失败: {str(e)}'
        }, status=500)


def update_recognition_settings_view(request):
    """更新识别设置"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '仅支持POST请求'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        
        # 更新自动识别流程设置
        if hasattr(auto_flow, 'update_settings'):
            auto_flow.update_settings(data)
        
        return JsonResponse({
            'status': 'success',
            'message': '设置更新成功',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"更新设置失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'更新设置失败: {str(e)}'
        }, status=500)


def reset_statistics_view(request):
    """重置统计数据"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '仅支持POST请求'
        }, status=405)
    
    try:
        # 重置识别记录统计
        # 这里可以添加重置逻辑
        
        return JsonResponse({
            'status': 'success',
            'message': '统计数据已重置',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"重置统计失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'重置统计失败: {str(e)}'
        }, status=500)


def get_recognition_history_view(request):
    """获取识别历史"""
    try:
        # 获取识别记录
        history = VisualRecognitionRecord.objects.all().order_by('-created_at')[:50]
        
        history_data = []
        for record in history:
            history_data.append({
                'id': record.id,
                'label': record.predicted_label,
                'confidence': float(record.confidence_score),
                'timestamp': record.created_at.isoformat(),
                'processing_time': float(record.processing_time)
            })
        
        return JsonResponse({
            'status': 'success',
            'history': history_data
        })
        
    except Exception as e:
        logger.error(f"获取识别历史失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取识别历史失败: {str(e)}'
        }, status=500)


def start_auto_flow_view(request):
    """启动自动识别流程"""
    try:
        # 实际启动自动识别流程
        success = auto_flow.start_flow()
        
        if success:
            return JsonResponse({
                'status': 'success',
                'message': '自动识别流程已启动'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '自动识别流程启动失败，请检查摄像头是否可用'
            }, status=500)
        
    except Exception as e:
        logger.error(f"启动自动流程失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'启动自动流程失败: {str(e)}'
        }, status=500)


def stop_auto_flow_view(request):
    """停止自动识别流程"""
    try:
        # 实际停止自动识别流程
        auto_flow.stop_flow()
        
        return JsonResponse({
            'status': 'success',
            'message': '自动识别流程已停止'
        })
        
    except Exception as e:
        logger.error(f"停止自动流程失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'停止自动流程失败: {str(e)}'
        }, status=500)


def get_auto_flow_status_view(request):
    """获取自动识别流程状态"""
    try:
        return JsonResponse({
            'status': 'success',
            'data': {
                'active': getattr(auto_flow, 'is_running', False)
            }
        })
        
    except Exception as e:
        logger.error(f"获取自动流程状态失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取自动流程状态失败: {str(e)}'
        }, status=500)


def get_recognition_status_view(request):
    """获取识别系统整体状态"""
    try:
        # 获取摄像头状态
        camera_status = 'stopped'
        try:
            from products.services.camera_handler import get_camera_handler
            handler = get_camera_handler()
            if handler and hasattr(handler, 'is_active') and handler.is_active:
                camera_status = 'running'
        except Exception:
            pass
        
        # 获取自动流程状态
        auto_flow_status = 'stopped'
        if hasattr(auto_flow, 'is_running') and auto_flow.is_running:
            auto_flow_status = 'running'
        
        return JsonResponse({
            'status': 'success',
            'camera_status': camera_status,
            'auto_flow_status': auto_flow_status,
            'websocket_connected': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取识别状态失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取识别状态失败: {str(e)}'
        }, status=500)


def get_performance_metrics_view(request):
    """获取性能指标"""
    try:
        # 获取识别器的性能指标
        metrics = {}
        
        if hasattr(object_recognition, 'get_performance_metrics'):
            metrics.update(object_recognition.get_performance_metrics())
        
        if hasattr(deep_learning_recognizer, 'get_performance_metrics'):
            metrics.update(deep_learning_recognizer.get_performance_metrics())
        
        # 添加系统资源使用情况
        metrics.update({
            'cpu_usage': 0.0,  # 可以集成psutil获取真实CPU使用率
            'memory_usage': 0.0,  # 可以集成psutil获取真实内存使用率
            'disk_usage': 0.0,  # 可以集成psutil获取真实磁盘使用率
            'timestamp': datetime.now().isoformat()
        })
        
        return JsonResponse({
            'status': 'success',
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'获取性能指标失败: {str(e)}'
        }, status=500)


def test_yolov8_page(request):
    """YOLOv8测试页面"""
    return render(request, 'test_yolov8.html')


@csrf_exempt
@require_http_methods(["POST"])
def test_recognize_view(request):
    """YOLOv8识别API"""
    try:
        import base64
        import os
        import tempfile
        from PIL import Image
        from io import BytesIO
        
        data = json.loads(request.body) if request.body else {}
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({
                'success': False,
                'error': '缺少图像数据'
            }, status=400)
        
        if image_data.startswith('data:image'):
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
        else:
            return JsonResponse({
                'success': False,
                'error': '无效的图像格式'
            }, status=400)
        
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, f"temp_recognize.{ext}")
        
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        
        try:
            from products.yolov8_integration import yolov8_recognition
            
            result = yolov8_recognition.recognize_and_calculate(temp_path, confidence_threshold=0.7)
            
            if result.get('success'):
                products = result.get('products', [])
                
                # 智能过滤逻辑
                if len(products) > 1:
                    # 检查是否有多个不同的类别
                    unique_names = set()
                    for p in products:
                        unique_names.add(p.get('name', ''))
                    
                    # 如果有多个不同类别，全部清空
                    if len(unique_names) > 1:
                        products = []
                    else:
                        # 如果是同一类别，只保留置信度最高的一个
                        products = sorted(products, key=lambda x: x.get('confidence', 0), reverse=True)
                        products = products[:1]
                
                return JsonResponse({
                    'success': True,
                    'products': products,
                    'total_price': sum(p['price'] for p in products) if products else 0.0,
                    'detected_count': len(products)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', '识别失败')
                })
                
        finally:
            try:
                os.remove(temp_path)
                os.rmdir(temp_dir)
            except:
                pass
            
    except Exception as e:
        logger.error(f"YOLOv8识别API失败: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)