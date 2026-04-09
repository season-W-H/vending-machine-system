from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderDetailSerializer
from products.models import Product, VisualRecognitionRecord
from products.services.vision_client import VisionServiceClient
from inventory.services import InventoryService

class OrderViewSet(viewsets.ModelViewSet):
    """订单管理视图集"""
    permission_classes = [AllowAny]  # 允许匿名访问，方便测试
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    
    def get_queryset(self):
        # 如果是测试模式，返回所有订单
        return Order.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'list']:
            return OrderDetailSerializer
        return OrderSerializer
    
    def list(self, request):
        """获取订单列表"""
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data})
    
    @action(detail=False, methods=['post'])
    def create_test_order(self, request):
        """创建测试订单"""
        items = request.data.get('items', [])
        if not items:
            return Response({'error': '订单项不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # 计算总金额
            total_amount = 0
            product_items = []
            
            for item in items:
                try:
                    product = Product.objects.get(name=item.get('product_name'))
                except Product.DoesNotExist:
                    product = None
                
                if product:
                    item_total = product.price * item.get('quantity', 1)
                    total_amount += item_total
                    product_items.append({
                        'product': product,
                        'quantity': item.get('quantity', 1),
                        'price': product.price
                    })
                else:
                    # 如果商品不存在，使用请求中的价格
                    item_total = item.get('price', 0) * item.get('quantity', 1)
                    total_amount += item_total
                    product_items.append({
                        'product': None,
                        'quantity': item.get('quantity', 1),
                        'price': item.get('price', 0),
                        'product_name': item.get('product_name', '未知商品')
                    })
            
            # 创建订单
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                total_amount=total_amount,
                status=Order.Status.CONFIRMED,
                confirmed_at=timezone.now()
            )
            
            # 创建订单项
            order_items = []
            for item in product_items:
                order_items.append(OrderItem(
                    order=order,
                    product=item.get('product'),
                    product_name=item.get('product_name') or (item['product'].name if item['product'] else '未知商品'),
                    price=item['price'],
                    quantity=item['quantity']
                ))
            OrderItem.objects.bulk_create(order_items)
            
            # 扣减库存
            for item in product_items:
                if item['product']:
                    item['product'].stock -= item['quantity']
                    item['product'].save()
        
        return Response({
            'status': 'success',
            'order_id': order.id,
            'order_no': order.order_no,
            'total_amount': float(order.total_amount)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """支付订单"""
        order = self.get_object()
        
        if order.status not in [Order.Status.PENDING, Order.Status.CONFIRMED]:
            return Response({'error': '订单状态不正确'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 更新订单状态
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save()
        
        return Response({
            'status': 'success',
            'message': '支付成功',
            'order_id': order.id,
            'order_no': order.order_no
        })
    
    @action(detail=False, methods=['post'])
    async def create_from_recognition(self, request):
        """基于视觉识别结果创建订单"""
        recognition_id = request.data.get('recognition_id')
        if not recognition_id:
            return Response(
                {'error': '缺少识别记录ID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取识别记录
        try:
            record = VisualRecognitionRecord.objects.get(
                record_id=recognition_id,
                status=VisualRecognitionRecord.Status.SUCCESS
            )
        except VisualRecognitionRecord.DoesNotExist:
            return Response(
                {'error': '无效的识别记录或识别未完成'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 解析识别结果
        recognition_result = record.recognition_result
        if not recognition_result:
            return Response(
                {'error': '识别结果为空'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 锁定库存
        lock_result = InventoryService.lock_inventory(recognition_result)
        if not lock_result['success']:
            return Response(
                {'error': lock_result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建订单
        with transaction.atomic():
            # 计算总金额
            total_amount = 0
            product_items = []
            
            for item in recognition_result:
                product = Product.objects.get(id=item['product_id'])
                item_total = product.price * item['quantity']
                total_amount += item_total
                product_items.append({
                    'product': product,
                    'quantity': item['quantity'],
                    'price': product.price
                })
            
            # 创建订单
            order = Order.objects.create(
                user=request.user,
                recognition_record=record,
                total_amount=total_amount,
                status=Order.Status.CONFIRMED,
                confirmed_at=timezone.now()
            )
            
            # 创建订单项
            order_items = [
                OrderItem(
                    order=order,
                    product=item['product'],
                    product_name=item['product'].name,
                    price=item['price'],
                    quantity=item['quantity']
                ) for item in product_items
            ]
            OrderItem.objects.bulk_create(order_items)
        
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消订单并释放库存"""
        order = self.get_object()
        
        if order.status not in [Order.Status.PENDING, Order.Status.CONFIRMED]:
            return Response(
                {'error': '只有待确认或已确认的订单可以取消'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 释放库存
        product_items = [
            {'product_id': item.product.id, 'quantity': item.quantity}
            for item in order.items.all() if item.product
        ]
        InventoryService.release_inventory(product_items)
        
        # 更新订单状态
        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save()
        
        return Response({'status': '订单已取消'})


class StatisticsViewSet(viewsets.ViewSet):
    """统计数据视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """获取仪表板统计数据"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 今日订单统计
        today_orders = Order.objects.filter(
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        today_order_count = today_orders.count()
        today_sales = today_orders.filter(
            status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 昨日订单统计
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_end - timedelta(days=1)
        yesterday_orders = Order.objects.filter(
            created_at__gte=yesterday_start,
            created_at__lte=yesterday_end
        )
        yesterday_order_count = yesterday_orders.count()
        yesterday_sales = yesterday_orders.filter(
            status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 本月订单统计
        month_orders = Order.objects.filter(
            created_at__gte=month_start
        )
        month_order_count = month_orders.count()
        month_sales = month_orders.filter(
            status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 上月订单统计
        last_month_start = (now - timedelta(days=30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = month_start - timedelta(seconds=1)
        last_month_orders = Order.objects.filter(
            created_at__gte=last_month_start,
            created_at__lte=last_month_end
        )
        last_month_order_count = last_month_orders.count()
        last_month_sales = last_month_orders.filter(
            status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 总订单统计
        total_orders = Order.objects.count()
        total_sales = Order.objects.filter(
            status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 计算增长率
        def calculate_growth(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 2)
        
        data = {
            'today': {
                'order_count': today_order_count,
                'sales': float(today_sales),
                'order_growth': calculate_growth(today_order_count, yesterday_order_count),
                'sales_growth': calculate_growth(float(today_sales), float(yesterday_sales))
            },
            'month': {
                'order_count': month_order_count,
                'sales': float(month_sales),
                'order_growth': calculate_growth(month_order_count, last_month_order_count),
                'sales_growth': calculate_growth(float(month_sales), float(last_month_sales))
            },
            'total': {
                'order_count': total_orders,
                'sales': float(total_sales)
            }
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        """获取销售趋势数据（最近7天）"""
        today = timezone.now().date()
        labels = []
        values = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            labels.append(date.strftime('%m-%d'))
            
            daily_sales = Order.objects.filter(
                created_at__date=date,
                status__in=[Order.Status.PAID, Order.Status.COMPLETED]
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            values.append(float(daily_sales))
        
        return Response({
            'labels': labels,
            'values': values
        })
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """获取热销商品排行（前5名）"""
        from django.db.models import Count
        
        # 通过 OrderItem 统计销量
        top_items = OrderItem.objects.filter(
            order__status__in=[Order.Status.PAID, Order.Status.COMPLETED]
        ).values('product__name').annotate(
            total_sales=Count('id')
        ).order_by('-total_sales')[:5]
        
        labels = []
        values = []
        
        for item in top_items:
            labels.append(item['product__name'] or '未知商品')
            values.append(item['total_sales'])
        
        return Response({
            'labels': labels,
            'values': values
        })
    
    @action(detail=False, methods=['get'])
    def current_transaction(self, request):
        """获取当前正在进行的交易"""
        # 查找最近的未完成订单（待确认、已确认、已支付状态）
        current_order = Order.objects.filter(
            status__in=[Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PAID]
        ).order_by('-created_at').first()
        
        if current_order:
            data = {
                'status': current_order.get_status_display(),
                'order_no': current_order.order_no,
                'total_amount': float(current_order.total_amount),
                'created_at': current_order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            data = {
                'status': '暂无交易',
                'order_no': None,
                'total_amount': 0,
                'created_at': None
            }
        
        return Response(data)
