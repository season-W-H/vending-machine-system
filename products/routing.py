# -*- coding: utf-8 -*-
"""
WebSocket URL配置

该模块定义了WebSocket连接的路由配置。
"""

from django.urls import re_path
from products.services.websocket_consumer import RecognitionConsumer

websocket_urlpatterns = [
    re_path(r'ws/recognition/$', RecognitionConsumer.as_asgi()),
]