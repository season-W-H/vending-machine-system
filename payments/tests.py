"""
支付系统测试用例
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache

from payments.models import PaymentRecord, RefundRecord, PaymentArchive
from payments.services.payment_service import payment_service
from orders.models import Order, OrderItem
from products.models import Product


class PaymentServiceTestCase(TestCase):
    """支付服务测试用例"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试产品
        self.product = Product.objects.create(
            name="测试商品",
            price=Decimal(100.00),
            stock=10
        )
        
        # 创建测试订单
        self.order = Order.objects.create(
            order_no="TEST202401010001",
            total_amount=Decimal(200.00),
            status=Order.Status.PENDING
        )
        
        # 添加订单项
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal(100.00)
        )
    
    def tearDown(self):
        """清理测试数据"""
        # 模拟cache.clear()，避免Redis连接错误
        with patch('django.core.cache.cache.clear') as mock_clear:
            mock_clear.return_value = None
    
    # ==================== 测试支付订单创建 ====================
    def test_create_payment_order_alipay(self):
        """测试创建支付宝支付订单"""
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter, \
             patch('django.core.cache.cache.set') as mock_set:
            mock_set.return_value = None
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.create_order.return_value = {
                'success': True,
                'params': {'test': 'params'},
                'gateway_url': 'https://openapi.alipay.com/gateway.do',
                'pay_url': 'https://openapi.alipay.com/gateway.do?test=params'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用创建支付订单方法
            payment_record, payment_params = payment_service.create_payment_order(
                self.order, PaymentRecord.PayType.ALIPAY
            )
            
            # 验证结果
            self.assertIsInstance(payment_record, PaymentRecord)
            self.assertEqual(payment_record.order, self.order)
            self.assertEqual(payment_record.pay_type, PaymentRecord.PayType.ALIPAY)
            self.assertEqual(payment_record.amount, self.order.total_amount)
            self.assertEqual(payment_record.status, PaymentRecord.Status.PENDING)
            self.assertTrue('success' in payment_params)
            self.assertTrue(payment_params['success'])
    
    def test_create_payment_order_wechat(self):
        """测试创建微信支付订单"""
        with patch('payments.adapters.wechat_adapter.WechatAdapter') as mock_adapter, \
             patch('django.core.cache.cache.set') as mock_set:
            mock_set.return_value = None
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.create_order.return_value = {
                'success': True,
                'params': {'test': 'params'},
                'pay_url': 'weixin://pay?test=params'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用创建支付订单方法
            payment_record, payment_params = payment_service.create_payment_order(
                self.order, PaymentRecord.PayType.WECHAT
            )
            
            # 验证结果
            self.assertIsInstance(payment_record, PaymentRecord)
            self.assertEqual(payment_record.order, self.order)
            self.assertEqual(payment_record.pay_type, PaymentRecord.PayType.WECHAT)
            self.assertEqual(payment_record.amount, self.order.total_amount)
            self.assertEqual(payment_record.status, PaymentRecord.Status.PENDING)
            self.assertTrue('success' in payment_params)
            self.assertTrue(payment_params['success'])
    
    # ==================== 测试支付回调处理 ====================
    def test_handle_callback_success(self):
        """测试处理支付成功回调"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0001",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.PENDING
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter, \
             patch('django.core.cache.cache.delete') as mock_delete:
            mock_delete.return_value = None
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.verify_callback.return_value = True
            mock_adapter.return_value = mock_instance
            
            # 模拟回调数据
            callback_data = {
                'out_trade_no': payment_record.record_no,
                'trade_status': 'TRADE_SUCCESS',
                'trade_no': 'ALIPAYTEST0001',
                'sign': 'test_sign'
            }
            
            # 调用处理回调方法
            success, message = payment_service.handle_callback(
                PaymentRecord.PayType.ALIPAY, callback_data
            )
            
            # 验证结果
            self.assertTrue(success)
            self.assertEqual(message, 'success')
            payment_record.refresh_from_db()
            self.assertEqual(payment_record.status, PaymentRecord.Status.SUCCESS)
            self.assertEqual(payment_record.platform_trade_no, 'ALIPAYTEST0001')
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, Order.Status.PAID)
    
    def test_handle_callback_failure(self):
        """测试处理支付失败回调"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0002",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.PENDING
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter:
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.verify_callback.return_value = True
            mock_adapter.return_value = mock_instance
            
            # 模拟回调数据
            callback_data = {
                'out_trade_no': payment_record.record_no,
                'trade_status': 'TRADE_CLOSED',
                'sign': 'test_sign'
            }
            
            # 调用处理回调方法
            success, message = payment_service.handle_callback(
                PaymentRecord.PayType.ALIPAY, callback_data
            )
            
            # 验证结果
            self.assertTrue(success)
            self.assertEqual(message, 'success')
            payment_record.refresh_from_db()
            self.assertEqual(payment_record.status, PaymentRecord.Status.FAILED)
    
    # ==================== 测试支付状态查询 ====================
    def test_query_payment_status_success(self):
        """测试查询支付状态（成功）"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0003",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.PENDING
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter:
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.query_status.return_value = {
                'status': 'SUCCESS',
                'trade_no': 'ALIPAYTEST0003',
                'message': '查询成功'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用查询支付状态方法
            result = payment_service.query_payment_status(payment_record)
            
            # 验证结果
            self.assertEqual(result['status'], 'SUCCESS')
            payment_record.refresh_from_db()
            self.assertEqual(payment_record.status, PaymentRecord.Status.SUCCESS)
            self.assertEqual(payment_record.platform_trade_no, 'ALIPAYTEST0003')
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, Order.Status.PAID)
    
    def test_query_payment_status_failure(self):
        """测试查询支付状态（失败）"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0004",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.PENDING
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter:
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.query_status.return_value = {
                'status': 'FAILED',
                'message': '查询成功'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用查询支付状态方法
            result = payment_service.query_payment_status(payment_record)
            
            # 验证结果
            self.assertEqual(result['status'], 'FAILED')
            payment_record.refresh_from_db()
            self.assertEqual(payment_record.status, PaymentRecord.Status.FAILED)
    
    # ==================== 测试退款处理 ====================
    def test_process_refund_success(self):
        """测试处理退款（成功）"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0005",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.SUCCESS,
            platform_trade_no='ALIPAYTEST0005',
            pay_time=timezone.now()
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter:
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.refund.return_value = {
                'success': True,
                'refund_no': 'ALIPAY_REFUND0005',
                'message': '退款成功'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用处理退款方法
            result = payment_service.process_refund(payment_record)
            
            # 验证结果
            self.assertTrue(result['success'])
            self.assertEqual(result['message'], '退款成功')
            # 验证退款记录是否创建
            self.assertEqual(RefundRecord.objects.filter(payment=payment_record).count(), 1)
    
    def test_process_refund_failure(self):
        """测试处理退款（失败）"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0006",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.SUCCESS,
            platform_trade_no='ALIPAYTEST0006',
            pay_time=timezone.now()
        )
        
        with patch('payments.adapters.alipay_adapter.AlipayAdapter') as mock_adapter:
            # 模拟适配器返回值
            mock_instance = Mock()
            mock_instance.refund.return_value = {
                'success': False,
                'message': '退款失败'
            }
            mock_adapter.return_value = mock_instance
            
            # 调用处理退款方法
            result = payment_service.process_refund(payment_record)
            
            # 验证结果
            self.assertFalse(result['success'])
            self.assertEqual(result['message'], '退款失败')
            # 验证退款记录是否创建
            self.assertEqual(RefundRecord.objects.filter(payment=payment_record).count(), 1)
    
    def test_process_refund_not_paid(self):
        """测试对未支付订单退款"""
        # 创建支付记录
        payment_record = PaymentRecord.objects.create(
            record_no="PAYTEST0007",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.PENDING
        )
        
        # 调用处理退款方法
        result = payment_service.process_refund(payment_record)
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '只能对已支付的订单进行退款')
    
    # ==================== 测试支付记录归档 ====================
    def test_archive_payment_records(self):
        """测试归档支付记录"""
        # 创建支付记录（超过归档天数）
        old_date = timezone.now() - timedelta(days=91)
        old_payment = PaymentRecord.objects.create(
            record_no="PAYTEST0008",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.SUCCESS
        )
        # 直接修改数据库中的时间
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE payments_paymentrecord SET created_at = %s WHERE id = %s",
                [old_date, old_payment.id]
            )
        old_payment.refresh_from_db()
        
        # 创建支付记录（未超过归档天数）
        recent_date = timezone.now() - timedelta(days=89)
        recent_payment = PaymentRecord.objects.create(
            record_no="PAYTEST0009",
            order=self.order,
            pay_type=PaymentRecord.PayType.ALIPAY,
            amount=Decimal(200.00),
            status=PaymentRecord.Status.SUCCESS
        )
        # 直接修改数据库中的时间
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE payments_paymentrecord SET created_at = %s WHERE id = %s",
                [recent_date, recent_payment.id]
            )
        recent_payment.refresh_from_db()
        

        
        # 调用归档方法
        result = payment_service.archive_payment_records(days=90)
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # 验证归档记录是否创建
        archive_count = PaymentArchive.objects.filter(original_record_id=old_payment.id).count()
        self.assertEqual(archive_count, 1)
        
        # 验证原记录是否被标记为已归档
        old_payment.refresh_from_db()
        self.assertTrue(old_payment.archived)
        
        # 验证未超过归档天数的记录是否未被归档
        recent_payment.refresh_from_db()
        self.assertFalse(recent_payment.archived)


if __name__ == '__main__':
    unittest.main()
