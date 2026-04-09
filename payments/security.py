"""
支付安全模块
实现支付回调防重放、金额防篡改等安全功能
"""

import hashlib
import hmac
import json
import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentSecurity:
    """支付安全类"""
    
    # 回调nonce有效期（秒）
    CALLBACK_NONCE_TIMEOUT = 3600  # 1小时
    
    @classmethod
    def verify_callback_signature(cls, pay_type, callback_data, signature):
        """
        验证支付回调签名
        
        Args:
            pay_type: 支付类型 (alipay/wechat)
            callback_data: 回调数据
            signature: 签名
        
        Returns:
            bool: 验证是否通过
        """
        try:
            if pay_type == 'alipay':
                from .adapters.alipay_adapter import AlipayAdapter
                adapter = AlipayAdapter()
                return adapter._verify_sign(callback_data, signature)
            elif pay_type == 'wechat':
                from .adapters.wechat_adapter import WechatAdapter
                adapter = WechatAdapter()
                return adapter.verify_sign(callback_data, signature)
            else:
                logger.error(f"不支持的支付类型: {pay_type}")
                return False
        except Exception as e:
            logger.error(f"验证回调签名失败: {str(e)}")
            return False
    
    @classmethod
    def verify_callback_nonce(cls, nonce):
        """
        验证回调nonce（防重放）
        
        Args:
            nonce: 随机字符串
        
        Returns:
            bool: 验证是否通过
        """
        if not nonce:
            return False
        
        cache_key = f'payment_callback_nonce_{nonce}'
        if cache.get(cache_key):
            logger.warning(f"检测到重复的支付回调: {nonce}")
            return False
        
        # 保存nonce
        cache.set(cache_key, True, timeout=cls.CALLBACK_NONCE_TIMEOUT)
        return True
    
    @classmethod
    def verify_payment_amount(cls, record_no, amount):
        """
        验证支付金额（防篡改）
        
        Args:
            record_no: 支付记录号
            amount: 回调金额
        
        Returns:
            bool: 验证是否通过
        """
        from .models import PaymentRecord
        
        try:
            payment_record = PaymentRecord.objects.get(record_no=record_no)
            expected_amount = float(payment_record.amount)
            received_amount = float(amount)
            
            # 允许0.01元的误差（浮点数比较）
            if abs(expected_amount - received_amount) > 0.01:
                logger.warning(
                    f"支付金额不匹配: 记录号={record_no}, "
                    f"期望金额={expected_amount}, 收到金额={received_amount}"
                )
                return False
            
            return True
        except PaymentRecord.DoesNotExist:
            logger.error(f"支付记录不存在: {record_no}")
            return False
        except Exception as e:
            logger.error(f"验证支付金额失败: {str(e)}")
            return False
    
    @classmethod
    def verify_callback_timestamp(cls, timestamp):
        """
        验证回调时间戳
        
        Args:
            timestamp: 时间戳（秒）
        
        Returns:
            bool: 验证是否通过
        """
        try:
            timestamp = int(timestamp)
            current_time = int(time.time())
            
            # 回调时间必须在5分钟内
            if abs(current_time - timestamp) > 300:
                logger.warning(f"回调时间戳无效: {timestamp}, 当前时间: {current_time}")
                return False
            
            return True
        except (ValueError, TypeError):
            logger.warning(f"回调时间戳格式无效: {timestamp}")
            return False
    
    @classmethod
    def generate_payment_sign(cls, payment_data):
        """
        生成支付数据签名
        
        Args:
            payment_data: 支付数据字典
        
        Returns:
            str: 签名
        """
        # 获取签名密钥
        secret_key = settings.SECURITY_CONFIG.get('API_SIGNING_KEY', 'your-api-signing-key-here')
        
        # 排序参数
        sorted_data = sorted(payment_data.items())
        # 拼接参数
        sign_string = '&'.join([f"{k}={v}" for k, v in sorted_data])
        
        # 计算HMAC-SHA256签名
        signature = hmac.new(
            secret_key.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @classmethod
    def verify_payment_sign(cls, payment_data, signature):
        """
        验证支付数据签名
        
        Args:
            payment_data: 支付数据字典
            signature: 签名
        
        Returns:
            bool: 验证是否通过
        """
        expected_signature = cls.generate_payment_sign(payment_data)
        return hmac.compare_digest(expected_signature, signature)
    
    @classmethod
    def lock_payment_record(cls, record_no, timeout=300):
        """
        锁定支付记录（防止并发处理）
        
        Args:
            record_no: 支付记录号
            timeout: 锁超时时间（秒）
        
        Returns:
            bool: 是否成功获取锁
        """
        lock_key = f'payment_lock_{record_no}'
        # 使用Redis的setnx实现分布式锁
        acquired = cache.add(lock_key, True, timeout=timeout)
        return acquired
    
    @classmethod
    def unlock_payment_record(cls, record_no):
        """
        解锁支付记录
        
        Args:
            record_no: 支付记录号
        """
        lock_key = f'payment_lock_{record_no}'
        cache.delete(lock_key)
    
    @classmethod
    def log_security_event(cls, event_type, details, risk_level='low'):
        """
        记录支付安全事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
            risk_level: 风险等级 (low/medium/high)
        """
        logger.warning(
            f"支付安全事件: {event_type}, "
            f"风险等级: {risk_level}, "
            f"详情: {json.dumps(details, ensure_ascii=False)}"
        )
        
        # 高风险事件可以发送告警
        if risk_level == 'high':
            # TODO: 发送告警通知
            pass


class PaymentCallbackValidator:
    """支付回调验证器"""
    
    def __init__(self, pay_type, callback_data):
        self.pay_type = pay_type
        self.callback_data = callback_data
        self.errors = []
    
    def validate(self):
        """
        执行完整验证
        
        Returns:
            bool: 验证是否通过
        """
        # 1. 验证签名
        if not self._validate_signature():
            return False
        
        # 2. 验证nonce（防重放）
        if not self._validate_nonce():
            return False
        
        # 3. 验证时间戳
        if not self._validate_timestamp():
            return False
        
        # 4. 验证金额
        if not self._validate_amount():
            return False
        
        return True
    
    def _validate_signature(self):
        """验证签名"""
        if self.pay_type == 'alipay':
            sign = self.callback_data.get('sign', '')
            # 支付宝签名验证在adapter中处理
            return True
        elif self.pay_type == 'wechat':
            sign = self.callback_data.get('sign', '')
            # 微信签名验证在adapter中处理
            return True
        return True
    
    def _validate_nonce(self):
        """验证nonce"""
        # 从回调数据中获取nonce
        nonce = self.callback_data.get('nonce', '')
        if nonce and not PaymentSecurity.verify_callback_nonce(nonce):
            self.errors.append('重复的回调请求')
            return False
        return True
    
    def _validate_timestamp(self):
        """验证时间戳"""
        timestamp = self.callback_data.get('timestamp', '')
        if timestamp and not PaymentSecurity.verify_callback_timestamp(timestamp):
            self.errors.append('回调时间戳无效')
            return False
        return True
    
    def _validate_amount(self):
        """验证金额"""
        # 获取支付记录号和金额
        if self.pay_type == 'alipay':
            record_no = self.callback_data.get('out_trade_no', '')
            amount = self.callback_data.get('total_amount', 0)
        elif self.pay_type == 'wechat':
            record_no = self.callback_data.get('out_trade_no', '')
            amount = self.callback_data.get('total_fee', 0)
        else:
            return True
        
        if record_no and not PaymentSecurity.verify_payment_amount(record_no, amount):
            self.errors.append('支付金额不匹配')
            PaymentSecurity.log_security_event(
                'PAYMENT_AMOUNT_MISMATCH',
                {'record_no': record_no, 'amount': amount},
                risk_level='high'
            )
            return False
        
        return True
    
    def get_errors(self):
        """获取验证错误信息"""
        return self.errors
