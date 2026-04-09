import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import PaymentRecord, RefundRecord, PaymentArchive
from .serializers import (
    PaymentRecordSerializer, RefundRecordSerializer, PaymentArchiveSerializer,
    CreatePaymentSerializer, RefundSerializer, PaymentStatusQuerySerializer, ArchiveQuerySerializer
)
from .services.payment_service import payment_service

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ModelViewSet):
    """支付记录视图集"""
    queryset = PaymentRecord.objects.all()
    serializer_class = PaymentRecordSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """
        创建支付订单
        
        POST /api/payments/create_payment/
        {
            "order_id": 1,
            "pay_type": "alipay"  # 或 "wechat"
        }
        """
        try:
            serializer = CreatePaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': '参数验证失败',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order = serializer.validated_data['order_id']
            pay_type = serializer.validated_data['pay_type']
            
            # 创建支付订单
            payment_record, payment_params = payment_service.create_payment_order(order, pay_type)
            
            return Response({
                'success': True,
                'message': '支付订单创建成功',
                'data': {
                    'record_no': payment_record.record_no,
                    'amount': float(payment_record.amount),
                    'pay_type': pay_type,
                    'payment_params': payment_params
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'创建支付订单失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def query_status(self, request):
        """
        查询支付状态
        
        POST /api/payments/query_status/
        {
            "record_no": "PAY1234567890ABCDEF"
        }
        """
        try:
            serializer = PaymentStatusQuerySerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': '参数验证失败',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            record_no = serializer.validated_data['record_no']
            
            # 查询支付记录
            try:
                payment_record = PaymentRecord.objects.get(record_no=record_no)
            except PaymentRecord.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '支付记录不存在'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 查询支付状态
            result = payment_service.query_payment_status(payment_record)
            
            return Response({
                'success': True,
                'message': '查询成功',
                'data': {
                    'record_no': payment_record.record_no,
                    'status': payment_record.status,
                    'status_display': payment_record.get_status_display(),
                    'pay_type': payment_record.pay_type,
                    'pay_type_display': payment_record.get_pay_type_display(),
                    'amount': float(payment_record.amount),
                    'platform_trade_no': payment_record.platform_trade_no,
                    'pay_time': payment_record.pay_time
                }
            })
            
        except Exception as e:
            logger.error(f"查询支付状态失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'查询支付状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def refund(self, request):
        """
        处理退款
        
        POST /api/payments/refund/
        {
            "payment_id": 1,
            "refund_amount": 10.00,  // 可选，不填则全额退款
            "reason": "用户申请退款"
        }
        """
        try:
            serializer = RefundSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': '参数验证失败',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payment = serializer.validated_data['payment_id']
            refund_amount = serializer.validated_data.get('refund_amount')
            reason = serializer.validated_data.get('reason', '')
            
            # 处理退款
            result = payment_service.process_refund(payment, refund_amount, reason)
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': '退款申请成功',
                    'data': result
                })
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', '退款失败')
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"处理退款失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'处理退款失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def archive(self, request):
        """
        归档支付记录
        
        POST /api/payments/archive/
        {
            "days": 90  // 可选，默认90天
        }
        """
        try:
            days = request.data.get('days', 90)
            result = payment_service.archive_payment_records(days)
            
            return Response({
                'success': result['success'],
                'message': result['message'],
                'data': {
                    'count': result.get('count', 0)
                }
            })
            
        except Exception as e:
            logger.error(f"归档支付记录失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'归档支付记录失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def archived_payments(self, request):
        """
        获取已归档的支付记录
        
        GET /api/payments/archived_payments/?start_date=2024-01-01&end_date=2024-12-31&page=1&page_size=20
        """
        try:
            serializer = ArchiveQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': '参数验证失败',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            page = serializer.validated_data.get('page', 1)
            page_size = serializer.validated_data.get('page_size', 20)
            
            # 获取归档记录
            result = payment_service.get_archived_payments(start_date, end_date, page, page_size)
            
            # 序列化数据
            archive_serializer = PaymentArchiveSerializer(result['records'], many=True)
            
            return Response({
                'success': True,
                'message': '查询成功',
                'data': {
                    'records': archive_serializer.data,
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'total_pages': result['total_pages']
                }
            })
            
        except Exception as e:
            logger.error(f"获取归档记录失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'获取归档记录失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RefundViewSet(viewsets.ModelViewSet):
    """退款记录视图集"""
    queryset = RefundRecord.objects.all()
    serializer_class = RefundRecordSerializer
    permission_classes = [AllowAny]


class PaymentArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """支付归档记录视图集"""
    queryset = PaymentArchive.objects.all()
    serializer_class = PaymentArchiveSerializer
    permission_classes = [AllowAny]


# ==================== 支付回调处理视图 ====================

@csrf_exempt
@require_http_methods(["POST"])
def alipay_callback(request):
    """
    支付宝支付回调处理
    
    POST /api/payments/alipay/notify/
    """
    try:
        # 获取回调数据
        callback_data = request.POST.dict()
        
        logger.info(f"收到支付宝回调: {callback_data}")
        
        # 处理回调
        success, message = payment_service.handle_callback('alipay', callback_data)
        
        if success:
            return HttpResponse('success')
        else:
            return HttpResponse('fail')
            
    except Exception as e:
        logger.error(f"处理支付宝回调失败: {str(e)}", exc_info=True)
        return HttpResponse('fail')


@csrf_exempt
@require_http_methods(["POST"])
def wechat_callback(request):
    """
    微信支付回调处理
    
    POST /api/payments/wechat/notify/
    """
    try:
        # 获取回调数据（XML格式）
        import xml.etree.ElementTree as ET
        xml_data = request.body.decode('utf-8')
        root = ET.fromstring(xml_data)
        callback_data = {child.tag: child.text for child in root}
        
        logger.info(f"收到微信支付回调: {callback_data}")
        
        # 处理回调
        success, message = payment_service.handle_callback('wechat', callback_data)
        
        if success:
            # 返回微信要求的XML格式
            return HttpResponse('<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>')
        else:
            return HttpResponse('<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[FAIL]]></return_msg></xml>')
            
    except Exception as e:
        logger.error(f"处理微信支付回调失败: {str(e)}", exc_info=True)
        return HttpResponse('<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[FAIL]]></return_msg></xml>')