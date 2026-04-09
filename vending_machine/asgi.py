"""
ASGI config for vending_machine project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from products.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vending_machine.settings')

# 获取Django ASGI应用
django_application = get_asgi_application()

# 定义应用程序 - 支持HTTP和WebSocket
application = ProtocolTypeRouter({
    "http": django_application,
    # WebSocket连接
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})