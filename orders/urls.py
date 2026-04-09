from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, StatisticsViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet)
router.register(r'statistics', StatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls)),
]