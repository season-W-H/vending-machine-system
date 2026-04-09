"""
微信支付适配器
实现微信支付接口对接
"""

import logging
import hashlib
import xml.etree.ElementTree as ET
from ..config import WECHAT_PAY_CONFIG

logger = logging.getLogger(__name__)


class WechatAdapter:
    """微信支付适配器"""
    
    def __init__(self):
        self.app_id = WECHAT_PAY_CONFIG['app_id']
        self.mch_id = WECHAT_PAY_CONFIG['mch_id']
        self.api_key = WECHAT_PAY_CONFIG['api_key']
        self.api_v3_key = WECHAT_PAY_CONFIG['api_v3_key']
        self.notify_url = WECHAT_PAY_CONFIG['notify_url']
        self.trade_type = WECHAT_PAY_CONFIG['trade_type']
        self.sandbox = WECHAT_PAY_CONFIG['sandbox']
        
        # 设置API地址
        if self.sandbox:
            self.api_url = 'https://api.mch.weixin.qq.com/sandboxnew/pay/unifiedorder'
            self.refund_url = 'https://api.mch.weixin.qq.com/sandboxnew/secapi/pay/refund'
            self.query_url = 'https://api.mch.weixin.qq.com/sandboxnew/pay/orderquery'
        else:
            self.api_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
            self.refund_url = 'https://api.mch.weixin.qq.com/secapi/pay/refund'
            self.query_url = 'https://api.mch.weixin.qq.com/pay/orderquery'
        
        logger.info(f"微信支付适配器初始化完成，沙箱模式: {self.sandbox}")
    
    # ==================== 1. 创建支付订单 ====================
    def create_order(self, payment_record, order):
        """
        创建微信支付订单
        
        Args:
            payment_record: 支付记录对象
            order: 订单对象
        
        Returns:
            dict: 支付参数
        """
        try:
            # 构建请求参数
            params = {
                'appid': self.app_id,
                'mch_id': self.mch_id,
                'nonce_str': self._generate_nonce_str(),
                'body': f'智能售卖机订单-{order.order_no}',
                'out_trade_no': payment_record.record_no,
                'total_fee': int(float(payment_record.amount) * 100),  # 转换为分
                'spbill_create_ip': self._get_client_ip(),
                'notify_url': self.notify_url,
                'trade_type': self.trade_type,
                'product_id': str(order.id),  # 商品ID
            }
            
            # 生成签名
            params['sign'] = self._generate_sign(params)
            
            # 转换为XML
            xml_data = self._dict_to_xml(params)
            
            logger.info(f"创建微信支付订单: {payment_record.record_no}")
            
            # 发送请求（这里需要实现HTTP请求）
            # response = requests.post(self.api_url, data=xml_data.encode('utf-8'), headers={'Content-Type': 'application/xml'})
            # result = self._xml_to_dict(response.text)
            
            # 模拟响应
            result = {
                'success': True,
                'code_url': 'weixin://wxpay/bizpayurl?pr=模拟二维码',
                'prepay_id': 'wx' + payment_record.record_no,
                'message': '创建成功'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"创建微信支付订单失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== 2. 验证回调签名 ====================
    def verify_callback(self, callback_data):
        """
        验证微信支付回调签名
        
        Args:
            callback_data: 回调数据（字典或XML字符串）
        
        Returns:
            bool: 验证是否成功
        """
        try:
            # 如果是XML字符串，转换为字典
            if isinstance(callback_data, str):
                callback_data = self._xml_to_dict(callback_data)
            
            # 提取签名
            sign = callback_data.pop('sign', None)
            
            if not sign:
                logger.warning("微信支付回调缺少签名")
                return False
            
            # 生成签名进行验证
            generated_sign = self._generate_sign(callback_data)
            
            if sign == generated_sign:
                logger.info("微信支付回调签名验证成功")
                return True
            else:
                logger.warning(f"微信支付回调签名验证失败: 期望 {generated_sign}, 实际 {sign}")
                return False
                
        except Exception as e:
            logger.error(f"验证微信支付回调签名失败: {str(e)}", exc_info=True)
            return False
    
    # ==================== 3. 查询支付状态 ====================
    def query_status(self, record_no):
        """
        查询微信支付状态
        
        Args:
            record_no: 支付记录号
        
        Returns:
            dict: 支付状态信息
        """
        try:
            # 构建请求参数
            params = {
                'appid': self.app_id,
                'mch_id': self.mch_id,
                'out_trade_no': record_no,
                'nonce_str': self._generate_nonce_str(),
            }
            
            # 生成签名
            params['sign'] = self._generate_sign(params)
            
            # 转换为XML
            xml_data = self._dict_to_xml(params)
            
            # 发送请求（这里需要实现HTTP请求）
            # response = requests.post(self.query_url, data=xml_data.encode('utf-8'), headers={'Content-Type': 'application/xml'})
            # result = self._xml_to_dict(response.text)
            
            # 模拟响应
            result = {
                'status': 'SUCCESS',
                'trade_no': 'WX' + record_no,
                'message': '查询成功'
            }
            
            logger.info(f"查询微信支付状态: {record_no}, 结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"查询微信支付状态失败: {str(e)}", exc_info=True)
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    # ==================== 4. 退款处理 ====================
    def refund(self, payment_record, refund_amount, reason):
        """
        处理微信支付退款
        
        Args:
            payment_record: 支付记录对象
            refund_amount: 退款金额
            reason: 退款原因
        
        Returns:
            dict: 退款结果
        """
        try:
            # 构建请求参数
            params = {
                'appid': self.app_id,
                'mch_id': self.mch_id,
                'nonce_str': self._generate_nonce_str(),
                'out_trade_no': payment_record.record_no,
                'out_refund_no': f"REF{payment_record.record_no}",
                'total_fee': int(float(payment_record.amount) * 100),  # 原订单金额（分）
                'refund_fee': int(float(refund_amount) * 100),  # 退款金额（分）
                'refund_desc': reason,
            }
            
            # 生成签名
            params['sign'] = self._generate_sign(params)
            
            # 转换为XML
            xml_data = self._dict_to_xml(params)
            
            # 发送请求（这里需要实现HTTP请求）
            # response = requests.post(self.refund_url, data=xml_data.encode('utf-8'), headers={'Content-Type': 'application/xml'})
            # result = self._xml_to_dict(response.text)
            
            # 模拟响应
            result = {
                'success': True,
                'refund_no': 'WX_REFUND' + payment_record.record_no,
                'message': '退款成功'
            }
            
            logger.info(f"微信支付退款: {payment_record.record_no}, 金额: {refund_amount}")
            return result
            
        except Exception as e:
            logger.error(f"微信支付退款失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== 辅助方法 ====================
    def _generate_nonce_str(self):
        """生成随机字符串"""
        import random
        import string
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def _generate_sign(self, params):
        """生成签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        # 拼接参数
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        # 添加API密钥
        sign_str += '&key=' + self.api_key
        # MD5加密
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        return sign
    
    def _dict_to_xml(self, params):
        """字典转XML"""
        root = ET.Element('xml')
        for key, value in params.items():
            child = ET.SubElement(root, key)
            child.text = str(value)
        return ET.tostring(root, encoding='utf-8')
    
    def _xml_to_dict(self, xml_str):
        """XML转字典"""
        root = ET.fromstring(xml_str)
        return {child.tag: child.text for child in root}
    
    def _get_client_ip(self):
        """获取客户端IP"""
        import socket
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return '127.0.0.1'