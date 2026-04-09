# 支付管理模块使用说明

## 概述

支付管理模块实现了完整的支付流程，支持微信支付和支付宝支付，包含五大核心功能：

1. **支付订单创建**：创建支付订单并对接第三方支付平台
2. **支付回调处理**：处理第三方支付平台的异步回调
3. **支付状态查询**：主动查询支付状态
4. **退款处理**：处理退款申请并对接第三方退款接口
5. **支付记录归档**：归档历史支付记录

## 目录结构

```
payments/
├── config.py                          # 支付配置文件
├── models.py                          # 数据模型
├── serializers.py                     # 序列化器
├── views.py                           # 视图
├── urls.py                            # 路由
├── services/
│   ├── __init__.py
│   └── payment_service.py            # 支付服务层
├── adapters/
│   ├── __init__.py
│   ├── alipay_adapter.py             # 支付宝适配器
│   └── wechat_adapter.py             # 微信支付适配器
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── payment_cron.py            # 定时任务
```

## 配置说明

### 1. 环境变量配置

在项目根目录创建 `.env` 文件，配置以下环境变量：

```bash
# 支付宝配置
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PUBLIC_KEY_PATH=/path/to/alipay_public_key.pem

# 微信支付配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_MCH_ID=your_wechat_mch_id
WECHAT_API_KEY=your_wechat_api_key
WECHAT_API_V3_KEY=your_wechat_api_v3_key
WECHAT_KEY_PATH=/path/to/wechat_key.pem
WECHAT_SANDBOX=False

# 支付回调URL（根据实际部署环境修改）
ALIPAY_NOTIFY_URL=https://yourdomain.com/api/payments/alipay/notify/
ALIPAY_RETURN_URL=https://yourdomain.com/api/payments/alipay/return/
WECHAT_NOTIFY_URL=https://yourdomain.com/api/payments/wechat/notify/
```

### 2. 密钥文件准备

#### 支付宝密钥

1. 下载支付宝开放平台密钥工具
2. 生成应用私钥和公钥
3. 将应用私钥保存到 `keys/alipay_private_key.pem`
4. 将支付宝公钥保存到 `keys/alipay_public_key.pem`

#### 微信支付密钥

1. 登录微信支付商户平台
2. 下载API证书和密钥
3. 将证书保存到 `keys/wechat_cert.pem`
4. 将密钥保存到 `keys/wechat_key.pem`

### 3. 数据库迁移

```bash
python manage.py makemigrations payments
python manage.py migrate payments
```

## API使用说明

### 1. 创建支付订单

**请求：**
```bash
POST /api/payments/create_payment/
Content-Type: application/json

{
    "order_id": 1,
    "pay_type": "alipay"
}
```

**响应：**
```json
{
    "success": true,
    "message": "支付订单创建成功",
    "data": {
        "record_no": "PAY1234567890ABCDEF",
        "amount": 10.00,
        "pay_type": "alipay",
        "payment_params": {
            "success": true,
            "params": {...},
            "gateway_url": "https://openapi.alipay.com/gateway.do",
            "pay_url": "..."
        }
    }
}
```

### 2. 查询支付状态

**请求：**
```bash
POST /api/payments/query_status/
Content-Type: application/json

{
    "record_no": "PAY1234567890ABCDEF"
}
```

**响应：**
```json
{
    "success": true,
    "message": "查询成功",
    "data": {
        "record_no": "PAY1234567890ABCDEF",
        "status": "success",
        "status_display": "支付成功",
        "pay_type": "alipay",
        "pay_type_display": "支付宝",
        "amount": 10.00,
        "platform_trade_no": "2024123100000000000000000000",
        "pay_time": "2024-12-31T12:00:00Z"
    }
}
```

### 3. 申请退款

**请求：**
```bash
POST /api/payments/refund/
Content-Type: application/json

{
    "payment_id": 1,
    "refund_amount": 10.00,
    "reason": "用户申请退款"
}
```

**响应：**
```json
{
    "success": true,
    "message": "退款申请成功",
    "data": {
        "success": true,
        "refund_no": "ALIPAY_REFUNDPAY1234567890ABCDEF",
        "message": "退款成功"
    }
}
```

### 4. 归档支付记录

**请求：**
```bash
POST /api/payments/archive/
Content-Type: application/json

{
    "days": 90
}
```

**响应：**
```json
{
    "success": true,
    "message": "成功归档 100 条记录",
    "data": {
        "count": 100
    }
}
```

### 5. 查询已归档记录

**请求：**
```bash
GET /api/payments/archived_payments/?start_date=2024-01-01&end_date=2024-12-31&page=1&page_size=20
```

**响应：**
```json
{
    "success": true,
    "message": "查询成功",
    "data": {
        "records": [...],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

## 定时任务

### 手动执行定时任务

```bash
# 执行所有任务
python manage.py payment_cron

# 只同步支付状态
python manage.py payment_cron --sync

# 只归档支付记录
python manage.py payment_cron --archive

# 归档指定天数前的记录
python manage.py payment_cron --archive --days=30
```

### 配置定时任务（Linux Cron）

编辑 crontab：
```bash
crontab -e
```

添加以下内容：
```bash
# 每5分钟同步一次支付状态
*/5 * * * * cd /path/to/project && python manage.py payment_cron --sync

# 每天凌晨2点归档支付记录
0 2 * * * cd /path/to/project && python manage.py payment_cron --archive
```

### 配置定时任务（Windows Task Scheduler）

1. 打开任务计划程序
2. 创建基本任务
3. 设置触发器（每5分钟或每天凌晨2点）
4. 设置操作：`python manage.py payment_cron --sync` 或 `python manage.py payment_cron --archive`

## 支付回调处理

### 支付宝回调

- **URL**: `/api/payments/alipay/notify/`
- **方法**: POST
- **格式**: application/x-www-form-urlencoded

### 微信支付回调

- **URL**: `/api/payments/wechat/notify/`
- **方法**: POST
- **格式**: application/xml

## 注意事项

1. **HTTPS要求**：生产环境必须使用HTTPS，否则支付回调可能失败
2. **IP白名单**：确保服务器IP在支付宝和微信支付的白名单中
3. **密钥安全**：妥善保管密钥文件，不要提交到版本控制系统
4. **日志记录**：所有支付操作都会记录日志，便于排查问题
5. **异常处理**：支付服务层包含完整的异常处理和日志记录
6. **事务处理**：关键操作使用数据库事务，确保数据一致性

## 测试

### 沙箱环境测试

微信支付支持沙箱环境，配置 `WECHAT_SANDBOX=True` 即可。

### 模拟回调

可以使用 Postman 或其他工具模拟支付回调进行测试。

## 故障排查

1. **支付回调失败**：检查回调URL是否正确，服务器是否可访问
2. **签名验证失败**：检查密钥文件是否正确，配置是否匹配
3. **支付状态不同步**：检查定时任务是否正常运行
4. **退款失败**：检查退款时效和金额是否正确

## 扩展

如需支持其他支付方式，可以：

1. 在 `adapters/` 目录下创建新的适配器
2. 在 `PaymentRecord.PayType` 中添加新的支付类型
3. 在 `payment_service.py` 中添加对应的处理逻辑

## 联系支持

如有问题，请查看日志文件或联系技术支持。