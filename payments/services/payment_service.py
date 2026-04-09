"""
支付服务层
实现支付订单创建、支付回调处理、支付状态查询、退款处理、支付记录归档五大核心功能
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from ..models import PaymentRecord, RefundRecord, PaymentArchive
from ..config import PAYMENT_CONFIG, PAYMENT_LOGGING
from orders.models import Order

logger = logging.getLogger(__name__)


class PaymentService:
    """支付服务类"""
    
    def __init__(self):
        self.timeout = PAYMENT_CONFIG['timeout']
        self.query_interval = PAYMENT_CONFIG['query_interval']
        self.max_query_times = PAYMENT_CONFIG['max_query_times']
    
    # ==================== 1. 支付订单创建 ====================
    def create_payment_order(self, order, pay_type):
        """
        创建支付订单
        
        Args:
            order: 订单对象
            pay_type: 支付类型 (alipay/wechat)
        
        Returns:
            PaymentRecord: 支付记录对象
            dict: 支付参数（用于调用第三方支付接口）
        """
        try:
            with transaction.atomic():
                # 创建支付记录
                payment_record = PaymentRecord.objects.create(
                    order=order,
                    pay_type=pay_type,
                    amount=order.total_amount,
                    status=PaymentRecord.Status.PENDING
                )
                
                logger.info(f"创建支付订单: {payment_record.record_no}, 订单号: {order.order_no}, 金额: {order.total_amount}")
                
                # 根据支付类型生成支付参数
                if pay_type == PaymentRecord.PayType.ALIPAY:
                    from ..adapters.alipay_adapter import AlipayAdapter
                    adapter = AlipayAdapter()
                    payment_params = adapter.create_order(payment_record, order)
                elif pay_type == PaymentRecord.PayType.WECHAT:
                    from ..adapters.wechat_adapter import WechatAdapter
                    adapter = WechatAdapter()
                    payment_params = adapter.create_order(payment_record, order)
                else:
                    raise ValueError(f"不支持的支付类型: {pay_type}")
                
                # 缓存支付信息，用于回调验证
                cache_key = f"payment_{payment_record.record_no}"
                cache.set(cache_key, {
                    'order_id': order.id,
                    'amount': str(order.total_amount),
                    'pay_type': pay_type,
                    'created_at': timezone.now().isoformat()
                }, timeout=self.timeout)
                
                return payment_record, payment_params
                
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}", exc_info=True)
            raise
    
    # ==================== 2. 支付回调处理 ====================
    def handle_callback(self, pay_type, callback_data):
        """
        处理支付回调（增强安全验证）
        
        Args:
            pay_type: 支付类型 (alipay/wechat)
            callback_data: 回调数据
        
        Returns:
            bool: 处理是否成功
            str: 返回给支付平台的消息
        """
        try:
            logger.info(f"收到支付回调: {pay_type}, 数据: {callback_data}")
            
            # 导入安全模块
            from ..security import PaymentSecurity, PaymentCallbackValidator
            
            # 1. 使用回调验证器进行完整验证
            validator = PaymentCallbackValidator(pay_type, callback_data)
            if not validator.validate():
                errors = validator.get_errors()
                logger.warning(f"支付回调验证失败: {errors}")
                return False, "fail"
            
            # 2. 验证回调签名
            if pay_type == PaymentRecord.PayType.ALIPAY:
                from ..adapters.alipay_adapter import AlipayAdapter
                adapter = AlipayAdapter()
                if not adapter.verify_callback(callback_data):
                    logger.warning("支付宝回调签名验证失败")
                    PaymentSecurity.log_security_event(
                        'ALIPAY_CALLBACK_SIGN_INVALID',
                        {'record_no': callback_data.get('out_trade_no')},
                        risk_level='high'
                    )
                    return False, "fail"
                
                record_no = callback_data.get('out_trade_no')
                trade_status = callback_data.get('trade_status')
                trade_no = callback_data.get('trade_no')
                amount = callback_data.get('total_amount', 0)
                
            elif pay_type == PaymentRecord.PayType.WECHAT:
                from ..adapters.wechat_adapter import WechatAdapter
                adapter = WechatAdapter()
                if not adapter.verify_callback(callback_data):
                    logger.warning("微信支付回调签名验证失败")
                    PaymentSecurity.log_security_event(
                        'WECHAT_CALLBACK_SIGN_INVALID',
                        {'record_no': callback_data.get('out_trade_no')},
                        risk_level='high'
                    )
                    return False, "fail"
                
                record_no = callback_data.get('out_trade_no')
                trade_status = callback_data.get('result_code')
                trade_no = callback_data.get('transaction_id')
                amount = callback_data.get('total_fee', 0)
            else:
                logger.error(f"不支持的支付类型: {pay_type}")
                return False, "fail"
            
            # 3. 验证支付金额（防篡改）
            if not PaymentSecurity.verify_payment_amount(record_no, amount):
                logger.error(f"支付金额验证失败: {record_no}")
                PaymentSecurity.log_security_event(
                    'PAYMENT_AMOUNT_TAMPERED',
                    {'record_no': record_no, 'amount': amount},
                    risk_level='high'
                )
                return False, "fail"
            
            # 4. 获取分布式锁（防止并发处理）
            if not PaymentSecurity.lock_payment_record(record_no, timeout=60):
                logger.warning(f"获取支付记录锁失败: {record_no}")
                return False, "fail"
            
            try:
                # 查找支付记录
                try:
                    payment_record = PaymentRecord.objects.get(record_no=record_no)
                except PaymentRecord.DoesNotExist:
                    logger.error(f"支付记录不存在: {record_no}")
                    PaymentSecurity.log_security_event(
                        'PAYMENT_RECORD_NOT_FOUND',
                        {'record_no': record_no},
                        risk_level='medium'
                    )
                    return False, "fail"
                
                # 检查是否已处理
                if payment_record.status == PaymentRecord.Status.SUCCESS:
                    logger.info(f"支付记录已处理: {record_no}")
                    return True, "success"
                
                # 处理支付结果
                with transaction.atomic():
                    if trade_status in ['TRADE_SUCCESS', 'SUCCESS']:
                        # 支付成功
                        payment_record.status = PaymentRecord.Status.SUCCESS
                        payment_record.platform_trade_no = trade_no
                        payment_record.pay_time = timezone.now()
                        payment_record.save()
                        
                        # 更新订单状态
                        order = payment_record.order
                        if order.status == Order.Status.PENDING:
                            order.status = Order.Status.PAID
                            order.paid_at = timezone.now()
                            order.save()
                            logger.info(f"订单支付成功: {order.order_no}")
                        
                        # 清除缓存
                        cache_key = f"payment_{record_no}"
                        cache.delete(cache_key)
                        
                        return True, "success"
                        
                    elif trade_status in ['TRADE_CLOSED', 'CLOSED', 'FAIL']:
                        # 支付失败
                        payment_record.status = PaymentRecord.Status.FAILED
                        payment_record.save()
                        logger.info(f"支付失败: {record_no}")
                        return True, "success"
                        
                    else:
                        logger.warning(f"未知的支付状态: {trade_status}")
                        return False, "fail"
            finally:
                # 释放锁
                PaymentSecurity.unlock_payment_record(record_no)
                    
        except Exception as e:
            logger.error(f"处理支付回调失败: {str(e)}", exc_info=True)
            return False, "fail"
    
    # ==================== 3. 支付状态查询 ====================
    def query_payment_status(self, payment_record):
        """
        查询支付状态
        
        Args:
            payment_record: 支付记录对象
        
        Returns:
            dict: 支付状态信息
        """
        try:
            logger.info(f"查询支付状态: {payment_record.record_no}")
            
            # 如果已经是最终状态，直接返回
            if payment_record.status in [PaymentRecord.Status.SUCCESS, PaymentRecord.Status.FAILED]:
                return {
                    'status': payment_record.status,
                    'message': '支付已完成'
                }
            
            # 调用第三方支付接口查询
            if payment_record.pay_type == PaymentRecord.PayType.ALIPAY:
                from ..adapters.alipay_adapter import AlipayAdapter
                adapter = AlipayAdapter()
                result = adapter.query_status(payment_record.record_no)
            elif payment_record.pay_type == PaymentRecord.PayType.WECHAT:
                from ..adapters.wechat_adapter import WechatAdapter
                adapter = WechatAdapter()
                result = adapter.query_status(payment_record.record_no)
            else:
                raise ValueError(f"不支持的支付类型: {payment_record.pay_type}")
            
            # 更新支付记录状态
            if result['status'] == 'SUCCESS':
                payment_record.status = PaymentRecord.Status.SUCCESS
                payment_record.platform_trade_no = result.get('trade_no')
                payment_record.pay_time = timezone.now()
                payment_record.save()
                
                # 更新订单状态
                order = payment_record.order
                if order.status == Order.Status.PENDING:
                    order.status = Order.Status.PAID
                    order.paid_at = timezone.now()
                    order.save()
                    
            elif result['status'] == 'FAILED':
                payment_record.status = PaymentRecord.Status.FAILED
                payment_record.save()
            
            return result
            
        except Exception as e:
            logger.error(f"查询支付状态失败: {str(e)}", exc_info=True)
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def sync_pending_payments(self):
        """同步所有待支付订单的状态"""
        try:
            # 查询超时的待支付订单
            timeout_time = timezone.now() - timedelta(seconds=self.timeout)
            pending_payments = PaymentRecord.objects.filter(
                status=PaymentRecord.Status.PENDING,
                created_at__lt=timeout_time
            )
            
            logger.info(f"开始同步 {pending_payments.count()} 个待支付订单")
            
            for payment in pending_payments:
                result = self.query_payment_status(payment)
                logger.info(f"支付 {payment.record_no} 状态: {result}")
                
        except Exception as e:
            logger.error(f"同步支付状态失败: {str(e)}", exc_info=True)
    
    # ==================== 4. 退款处理 ====================
    def process_refund(self, payment_record, refund_amount=None, reason=''):
        """
        处理退款
        
        Args:
            payment_record: 支付记录对象
            refund_amount: 退款金额（默认全额退款）
            reason: 退款原因
        
        Returns:
            dict: 退款结果
        """
        try:
            # 验证支付状态
            if payment_record.status != PaymentRecord.Status.SUCCESS:
                return {
                    'success': False,
                    'message': '只能对已支付的订单进行退款'
                }
            
            # 验证退款时效
            refund_timeout = timedelta(days=PAYMENT_CONFIG['refund_timeout'])
            if payment_record.pay_time + refund_timeout < timezone.now():
                return {
                    'success': False,
                    'message': '超过退款有效期'
                }
            
            # 确定退款金额
            if refund_amount is None:
                refund_amount = payment_record.amount
            elif refund_amount > payment_record.amount:
                return {
                    'success': False,
                    'message': '退款金额不能超过支付金额'
                }
            
            logger.info(f"开始退款: {payment_record.record_no}, 金额: {refund_amount}")
            
            # 调用第三方支付接口退款
            if payment_record.pay_type == PaymentRecord.PayType.ALIPAY:
                from ..adapters.alipay_adapter import AlipayAdapter
                adapter = AlipayAdapter()
                result = adapter.refund(payment_record, refund_amount, reason)
            elif payment_record.pay_type == PaymentRecord.PayType.WECHAT:
                from ..adapters.wechat_adapter import WechatAdapter
                adapter = WechatAdapter()
                result = adapter.refund(payment_record, refund_amount, reason)
            else:
                raise ValueError(f"不支持的支付类型: {payment_record.pay_type}")
            
            if result['success']:
                # 创建退款记录
                RefundRecord.objects.create(
                    payment=payment_record,
                    refund_no=f"REF{uuid.uuid4().hex[:16].upper()}",
                    amount=refund_amount,
                    reason=reason,
                    status='SUCCESS'
                )
                logger.info(f"退款成功: {payment_record.record_no}")
            else:
                # 创建退款记录（失败）
                RefundRecord.objects.create(
                    payment=payment_record,
                    refund_no=f"REF{uuid.uuid4().hex[:16].upper()}",
                    amount=refund_amount,
                    reason=reason,
                    status='FAILED',
                    error_message=result.get('message', '')
                )
                logger.error(f"退款失败: {payment_record.record_no}, 原因: {result.get('message')}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理退款失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== 5. 支付记录归档 ====================
    def archive_payment_records(self, days=None):
        """
        归档支付记录
        
        Args:
            days: 归档天数（默认使用配置中的天数）
        
        Returns:
            dict: 归档结果
        """
        try:
            if days is None:
                days = PAYMENT_CONFIG['archive_days']
            
            # 计算归档时间点
            archive_time = timezone.now() - timedelta(days=days)
            
            # 查询需要归档的支付记录
            records_to_archive = PaymentRecord.objects.filter(
                created_at__lt=archive_time,
                status__in=[PaymentRecord.Status.SUCCESS, PaymentRecord.Status.FAILED]
            )
            
            count = records_to_archive.count()
            logger.info(f"开始归档 {count} 条支付记录")
            
            if count == 0:
                return {
                    'success': True,
                    'message': '没有需要归档的记录',
                    'count': 0
                }
            
            # 创建归档记录
            for record in records_to_archive:
                PaymentArchive.objects.create(
                    original_record_id=record.id,
                    record_no=record.record_no,
                    order_no=record.order.order_no,
                    pay_type=record.pay_type,
                    amount=record.amount,
                    status=record.status,
                    platform_trade_no=record.platform_trade_no,
                    pay_time=record.pay_time,
                    created_at=record.created_at,
                    archived_at=timezone.now()
                )
            
            # 删除原记录（或标记为已归档）
            # 这里选择软删除，保留原记录但标记为已归档
            records_to_archive.update(archived=True)
            
            logger.info(f"归档完成: {count} 条记录")
            
            return {
                'success': True,
                'message': f'成功归档 {count} 条记录',
                'count': count
            }
            
        except Exception as e:
            logger.error(f"归档支付记录失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'count': 0
            }
    
    def get_archived_payments(self, start_date=None, end_date=None, page=1, page_size=20):
        """
        获取已归档的支付记录
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict: 归档记录列表
        """
        try:
            queryset = PaymentArchive.objects.all()
            
            if start_date:
                queryset = queryset.filter(archived_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(archived_at__lte=end_date)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            
            records = queryset.order_by('-archived_at')[start:end]
            total = queryset.count()
            
            return {
                'records': records,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"获取归档记录失败: {str(e)}", exc_info=True)
            return {
                'records': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }


# 创建支付服务实例
payment_service = PaymentService()