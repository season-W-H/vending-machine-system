from django.urls import path, include
from rest_framework.routers import DefaultRouter

# 导入视图函数
from products.views import (
    ProductViewSet,
    StockOperationViewSet,
    # 识别相关视图
    RecognitionViews,
    # Django视图函数
    index_view,
    optimization_showcase_view,
    recognition_page_view,
    product_list_view,
    product_api_view,
    product_detail_view,
    # 摄像头控制视图
    start_camera_view,
    stop_camera_view,
    get_camera_status_view,
    get_frame_view,
    get_frame_with_detections_view,
    get_recognition_result_view,
    # 识别相关视图
    recognize_from_image_view,
    capture_and_recognize_view,
    get_recognition_history_view,
    get_dataset_info_view,
    train_model_view,
    update_recognition_settings_view,
    reset_statistics_view,
    # 自动流程视图
    start_auto_flow_view,
    stop_auto_flow_view,
    get_auto_flow_status_view,
    get_recognition_status_view,
    get_performance_metrics_view,
    # 识别测试视图
    recognition_test_view,
    # YOLOv8测试视图
    test_yolov8_page,
    test_recognize_view,
)

# 创建DRF路由器
router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'stock-operations', StockOperationViewSet)

# API URL配置
urlpatterns = [
    # 主页
    path('', index_view, name='home'),
    
    # 系统优化展示页面
    path('optimization/', optimization_showcase_view, name='optimization_showcase'),
    
    # DRF路由
    path('api/', include(router.urls)),
    
    # 页面路由
    path('recognition/', recognition_page_view, name='recognition_view'),
    path('inventory/', RecognitionViews.inventory_page, name='inventory_view'),
    path('orders/', RecognitionViews.orders_page, name='orders_view'),
    
    # 摄像头控制API
    path('camera/', include([
        path('start/', start_camera_view, name='start_camera'),
        path('stop/', stop_camera_view, name='stop_camera'),
        path('status/', get_camera_status_view, name='get_camera_status'),
        path('frame/', get_frame_view, name='get_frame'),
        path('frame-with-detections/', get_frame_with_detections_view, name='get_frame_with_detections'),
        path('recognition-result/', get_recognition_result_view, name='get_recognition_result'),
    ])),
    
    # 识别相关API
    path('recognition/start-auto-flow/', start_auto_flow_view, name='start_auto_flow'),
    path('recognition/stop-auto-flow/', stop_auto_flow_view, name='stop_auto_flow'),
    path('recognition/auto-flow-status/', get_auto_flow_status_view, name='get_auto_flow_status'),
    path('recognition/status/', get_recognition_status_view, name='get_recognition_status'),
    path('recognition/performance/', get_performance_metrics_view, name='get_performance_metrics'),
    path('recognition/history/', get_recognition_history_view, name='get_recognition_history'),
    path('recognition/recognize-image/', recognize_from_image_view, name='recognize_from_image'),
    path('recognition/capture-and-recognize/', capture_and_recognize_view, name='capture_and_recognize'),
    path('recognition/dataset-info/', get_dataset_info_view, name='get_dataset_info'),
    path('recognition/train/', train_model_view, name='train_model'),
    path('recognition/settings/', update_recognition_settings_view, name='update_recognition_settings'),
    path('recognition/reset-stats/', reset_statistics_view, name='reset_statistics'),
    
    # 管理页面API
    path('admin/', include([
        path('', RecognitionViews.admin_dashboard, name='admin_dashboard'),
        path('performance/', RecognitionViews.performance_monitor, name='performance_monitor'),
        path('recognition-monitor/', RecognitionViews.recognition_monitor, name='recognition_monitor'),
    ])),
    
    # 识别测试API
    path('test/', include([
        path('recognition/', recognition_test_view, name='recognition_test'),
    ])),
]