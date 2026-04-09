# products.views.__init__.py

# Django REST Framework imports
from rest_framework.viewsets import ModelViewSet

# 导入本地的ViewSet
from .product_views import ProductViewSet, StockOperationViewSet

# 导入所有视图函数
from .recognition_views import (
    RecognitionViews,
    # 实际的Django视图函数
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
)

# 导入识别测试视图
from .recognition_test_views import recognition_test_view

# 导入YOLOv8测试视图
from .recognition_views import test_yolov8_page, test_recognize_view

# 定义所有可用的视图函数列表
__all__ = [
    'ProductViewSet',
    'StockOperationViewSet',
    'RecognitionViews',
    'index_view',
    'optimization_showcase_view',
    'recognition_page_view',
    'product_list_view',
    'product_api_view',
    'product_detail_view',
    'recognition_test_view',
    'start_camera_view',
    'stop_camera_view',
    'get_camera_status_view',
    'get_frame_view',
    'get_frame_with_detections_view',
    'get_recognition_result_view',
    'recognize_from_image_view',
    'capture_and_recognize_view',
    'get_recognition_history_view',
    'get_dataset_info_view',
    'train_model_view',
    'update_recognition_settings_view',
    'reset_statistics_view',
    'start_auto_flow_view',
    'stop_auto_flow_view',
    'get_auto_flow_status_view',
    'get_recognition_status_view',
    'get_performance_metrics_view',
    'test_yolov8_page',
    'test_recognize_view',
]