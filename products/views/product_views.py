# -*- coding: utf-8 -*-
"""商品视图集"""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, F
from django.db.models.functions import Coalesce
from ..models import Product, StockOperation
from ..serializers import ProductSerializer, StockOperationSerializer

# 产品视图集
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 库存状态筛选
        status = self.request.query_params.get('status', None)
        if status:
            if status == 'low_stock':
                queryset = queryset.filter(stock__lte=F('low_stock_threshold'), stock__gt=0)
            elif status == 'out_of_stock':
                queryset = queryset.filter(stock=0)
            elif status == 'in_stock':
                queryset = queryset.filter(stock__gt=F('low_stock_threshold'))
        
        # 类别筛选
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset


# 库存操作视图集
class StockOperationViewSet(viewsets.ModelViewSet):
    queryset = StockOperation.objects.all()
    serializer_class = StockOperationSerializer
    permission_classes = [AllowAny]