"""
支付宝支付适配器
实现支付宝支付接口对接
"""

import logging
import base64
from urllib.parse import quote_plus
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from ..config import ALIPAY_CONFIG

logger = logging.getLogger(__name__)


class AlipayAdapter:
    """支付宝支付适配器"""
    
    def __init__(self):
        self.app_id = ALIPAY_CONFIG['app_id']
        self.gateway_url = ALIPAY_CONFIG['gateway_url']
        self.notify_url = ALIPAY_CONFIG['notify_url']
        self.return_url = ALIPAY_CONFIG['return_url']
        self.sign_type = ALIPAY_CONFIG['sign_type']
        self.charset = ALIPAY_CONFIG['charset']
        self.version = ALIPAY_CONFIG['version']
        
        # 加载密钥
        self.private_key = self._load_private_key()
        self.alipay_public_key = self._load_alipay_public_key()
    
    def _load_private_key(self):
        """加载应用私钥"""
        try:
            with open(ALIPAY_CONFIG['app_private_key_path'], 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info("支付宝私钥加载成功")
            return private_key
        except Exception as e:
            logger.error(f"加载支付宝私钥失败: {str(e)}", exc_info=True)
            raise
    
    def _load_alipay_public_key(self):
        """加载支付宝公钥"""
        try:
            with open(ALIPAY_CONFIG['alipay_public_key_path'], 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info("支付宝公钥加载成功")
            return public_key
        except Exception as e:
            logger.error(f"加载支付宝公钥失败: {str(e)}", exc_info=True)
            raise
    
    def _sign(self, data):
        """生成签名"""
        try:
            # 排序参数
            sorted_data = sorted(data.items())
            # 拼接参数
            sign_str = '&'.join([f"{k}={v}" for k, v in sorted_data])
            
            # 使用私钥签名
            signature = self.private_key.sign(
                sign_str.encode(self.charset),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Base64编码
            sign_base64 = base64.b64encode(signature).decode(self.charset)
            sign_urlencode = quote_plus(sign_base64)
            
            return sign_urlencode
        except Exception as e:
            logger.error(f"生成签名失败: {str(e)}", exc_info=True)
            raise
    
    def _verify_sign(self, data, sign):
        """验证签名"""
        try:
            # 排序参数
            sorted_data = sorted(data.items())
            # 拼接参数
            sign_str = '&'.join([f"{k}={v}" for k, v in sorted_data])
            
            # Base64解码
            sign_bytes = base64.b64decode(sign)
            
            # 使用公钥验证
            self.alipay_public_key.verify(
                sign_bytes,
                sign_str.encode(self.charset),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True
        except Exception as e:
            logger.error(f"验证签名失败: {str(e)}", exc_info=True)
            return False
    
    # ==================== 1. 创建支付订单 ====================
    def create_order(self, payment_record, order):
        """
        创建支付宝支付订单
        
        Args:
            payment_record: 支付记录对象
            order: 订单对象
        
        Returns:
            dict: 支付参数
        """
        try:
            # 构建请求参数
            biz_content = {
                'out_trade_no': payment_record.record_no,  # 商户订单号
                'total_amount': str(float(payment_record.amount)),  # 订单金额
                'subject': f'智能售卖机订单-{order.order_no}',  # 订单标题
                'body': f'订单包含{order.items.count()}件商品',  # 订单描述
                'timeout_express': '5m',  # 超时时间
                'product_code': 'FAST_INSTANT_TRADE_PAY',  # 产品码
            }
            
            # 构建请求参数
            params = {
                'app_id': self.app_id,
                'method': 'alipay.trade.precreate',  # 接口名称
                'charset': self.charset,
                'sign_type': self.sign_type,
                'timestamp': self._get_timestamp(),
                'version': self.version,
                'notify_url': self.notify_url,  # 异步通知地址
                'return_url': self.return_url,  # 同步返回地址
                'biz_content': biz_content  # 业务参数
            }
            
            # 生成签名
            params['sign'] = self._sign(params)
            
            logger.info(f"创建支付宝支付订单: {payment_record.record_no}")
            
            return {
                'success': True,
                'params': params,
                'gateway_url': self.gateway_url,
                'pay_url': f"{self.gateway_url}?{self._build_query_string(params)}"
            }
            
        except Exception as e:
            logger.error(f"创建支付宝支付订单失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== 2. 验证回调签名 ====================
    def verify_callback(self, callback_data):
        """
        验证支付宝回调签名
        
        Args:
            callback_data: 回调数据
        
        Returns:
            bool: 验证是否成功
        """
        try:
            # 提取签名
            sign = callback_data.pop('sign', None)
            sign_type = callback_data.pop('sign_type', None)
            
            if not sign:
                logger.warning("支付宝回调缺少签名")
                return False
            
            # 验证签名
            is_valid = self._verify_sign(callback_data, sign)
            
            if is_valid:
                logger.info("支付宝回调签名验证成功")
            else:
                logger.warning("支付宝回调签名验证失败")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"验证支付宝回调签名失败: {str(e)}", exc_info=True)
            return False
    
    # ==================== 3. 查询支付状态 ====================
    def query_status(self, record_no):
        """
        查询支付宝支付状态
        
        Args:
            record_no: 支付记录号
        
        Returns:
            dict: 支付状态信息
        """
        try:
            # 构建请求参数
            biz_content = {
                'out_trade_no': record_no  # 商户订单号
            }
            
            params = {
                'app_id': self.app_id,
                'method': 'alipay.trade.query',  # 接口名称
                'charset': self.charset,
                'sign_type': self.sign_type,
                'timestamp': self._get_timestamp(),
                'version': self.version,
                'biz_content': biz_content
            }
            
            # 生成签名
            params['sign'] = self._sign(params)
            
            # 发送请求（这里需要实现HTTP请求）
            # response = requests.post(self.gateway_url, data=params)
            # result = response.json()
            
            # 模拟响应
            result = {
                'status': 'SUCCESS',
                'trade_no': 'ALIPAY' + record_no,
                'message': '查询成功'
            }
            
            logger.info(f"查询支付宝支付状态: {record_no}, 结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"查询支付宝支付状态失败: {str(e)}", exc_info=True)
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    # ==================== 4. 退款处理 ====================
    def refund(self, payment_record, refund_amount, reason):
        """
        处理支付宝退款
        
        Args:
            payment_record: 支付记录对象
            refund_amount: 退款金额
            reason: 退款原因
        
        Returns:
            dict: 退款结果
        """
        try:
            # 构建请求参数
            biz_content = {
                'out_trade_no': payment_record.record_no,  # 原支付订单号
                'refund_amount': str(float(refund_amount)),  # 退款金额
                'refund_reason': reason,  # 退款原因
                'out_request_no': f"REF{payment_record.record_no}"  # 退款请求号
            }
            
            params = {
                'app_id': self.app_id,
                'method': 'alipay.trade.refund',  # 接口名称
                'charset': self.charset,
                'sign_type': self.sign_type,
                'timestamp': self._get_timestamp(),
                'version': self.version,
                'biz_content': biz_content
            }
            
            # 生成签名
            params['sign'] = self._sign(params)
            
            # 发送请求（这里需要实现HTTP请求）
            # response = requests.post(self.gateway_url, data=params)
            # result = response.json()
            
            # 模拟响应
            result = {
                'success': True,
                'refund_no': 'ALIPAY_REFUND' + payment_record.record_no,
                'message': '退款成功'
            }
            
            logger.info(f"支付宝退款: {payment_record.record_no}, 金额: {refund_amount}")
            return result
            
        except Exception as e:
            logger.error(f"支付宝退款失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== 辅助方法 ====================
    def _get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _build_query_string(self, params):
        """构建查询字符串"""
        return '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])