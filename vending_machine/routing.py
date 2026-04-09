# -*- coding: utf-8 -*-
"""
ASGI配置文件 - Channels路由配置

该文件定义了ASGI应用的路由配置，包括HTTP和WebSocket路由。
"""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from products.routing import websocket_urlpatterns

# 定义应用程序
application = ProtocolTypeRouter({
    # WebSocket连接
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})