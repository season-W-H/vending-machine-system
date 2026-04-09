"""
支付配置文件
配置微信支付和支付宝支付的相关参数
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== 支付宝配置 ====================
ALIPAY_CONFIG = {
    'app_id': os.getenv('ALIPAY_APP_ID', 'your_alipay_app_id'),
    'app_private_key_path': os.path.join(BASE_DIR, 'keys', 'alipay_private_key.pem'),
    'alipay_public_key_path': os.getenv('ALIPAY_PUBLIC_KEY_PATH', os.path.join(BASE_DIR, 'keys', 'alipay_public_key.pem')),
    'gateway_url': 'https://openapi.alipay.com/gateway.do',
    'notify_url': os.getenv('ALIPAY_NOTIFY_URL', 'http://localhost:8000/api/payments/alipay/notify/'),
    'return_url': os.getenv('ALIPAY_RETURN_URL', 'http://localhost:8000/api/payments/alipay/return/'),
    'sign_type': 'RSA2',
    'charset': 'utf-8',
    'version': '1.0',
}

# ==================== 微信支付配置 ====================
WECHAT_PAY_CONFIG = {
    'app_id': os.getenv('WECHAT_APP_ID', 'your_wechat_app_id'),
    'mch_id': os.getenv('WECHAT_MCH_ID', 'your_wechat_mch_id'),
    'api_key': os.getenv('WECHAT_API_KEY', 'your_wechat_api_key'),
    'api_v3_key': os.getenv('WECHAT_API_V3_KEY', 'your_wechat_api_v3_key'),
    'cert_path': os.path.join(BASE_DIR, 'keys', 'wechat_cert.pem'),
    'key_path': os.getenv('WECHAT_KEY_PATH', os.path.join(BASE_DIR, 'keys', 'wechat_key.pem')),
    'notify_url': os.getenv('WECHAT_NOTIFY_URL', 'http://localhost:8000/api/payments/wechat/notify/'),
    'trade_type': 'NATIVE',  # 扫码支付
    'sandbox': os.getenv('WECHAT_SANDBOX', 'False') == 'True',  # 沙箱环境
}

# ==================== 支付通用配置 ====================
PAYMENT_CONFIG = {
    'timeout': 300,  # 支付超时时间（秒）
    'query_interval': 60,  # 支付状态查询间隔（秒）
    'max_query_times': 5,  # 最大查询次数
    'refund_timeout': 7,  # 退款有效期（天）
    'archive_days': 90,  # 支付记录归档天数
    'auto_archive': True,  # 自动归档
}

# ==================== 支付回调白名单 ====================
CALLBACK_IP_WHITELIST = [
    '127.0.0.1',
    'localhost',
    # 添加支付宝和微信支付的服务器IP
]

# ==================== 支付日志配置 ====================
PAYMENT_LOGGING = {
    'enabled': True,
    'log_dir': os.path.join(BASE_DIR, 'logs', 'payments'),
    'max_log_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}