from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, RefundViewSet, PaymentArchiveViewSet, alipay_callback, wechat_callback

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'archives', PaymentArchiveViewSet, basename='archive')

urlpatterns = [
    path('', include(router.urls)),
    path('alipay/notify/', alipay_callback, name='alipay_callback'),
    path('wechat/notify/', wechat_callback, name='wechat_callback'),
]