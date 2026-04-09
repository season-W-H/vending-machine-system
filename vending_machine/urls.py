from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.routers import DefaultRouter

# 直接导入ViewSet
from products.views import ProductViewSet, StockOperationViewSet
from products.views.recognition_views import test_yolov8_page, test_recognize_view

# 创建专门的API路由器
api_router = DefaultRouter()
api_router.register(r'', ProductViewSet, basename='product')
api_router.register(r'stock-operations', StockOperationViewSet)

# 简单的根路径视图
def home(request):
    html_content = """<h1>智能售卖机系统</h1>
    
    <h2>主要页面</h2>
    <ul>
        <li><strong><a href='/admin-dashboard/'>后台管理页面</a></strong> - 商品管理、订单管理、销售统计、库存管理</li>
        <li><strong><a href='/workspace/'>工作界面</a></strong> - 摄像头监控、商品识别、支付流程</li>
        <li><a href='/dashboard/'>旧版管理页面</a> - （保留中）</li>
        <li><a href='/admin/'>Django管理后台</a></li>
    </ul>
    
    <h2>API端点列表:</h2>
    <ul>
        <li><a href='/api/users/'>用户API</a></li>
        <li><a href='/api/products/'>产品API</a></li>
        <li><a href='/api/orders/'>订单API</a></li>
        <li><a href='/api/payments/'>支付API</a></li>
        <li><a href='/api/inventory/'>库存API</a></li>
    </ul>
    
    <h2>API使用说明</h2>
    <p>系统使用JWT (JSON Web Token) 进行身份认证。要访问受保护的API，请按照以下步骤操作：</p>
    
    <ol>
        <li>使用管理员账户登录 <a href='/admin/'>管理后台</a></li>
        <li>获取JWT令牌：
            <ul>
                <li>访问 <a href='/api/users/token/'>/api/users/token/</a></li>
                <li>使用以下JSON格式提交POST请求：
                    <pre>{"username": "your_username", "password": "your_password"}</pre>
                </li>
                <li>成功后将获得access_token和refresh_token</li>
            </ul>
        </li>
        <li>访问受保护的API：
            <ul>
                <li>在HTTP请求头中添加Authorization: Bearer &lt;access_token&gt;</li>
                <li>例如：Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...</li>
            </ul>
        </li>
        <li>当access_token过期时，可以使用refresh_token获取新令牌：
            <ul>
                <li>访问 <a href='/api/users/token/refresh/'>/api/users/token/refresh/</a></li>
                <li>提交POST请求：<pre>{"refresh": "your_refresh_token"}</pre></li>
            </ul>
        </li>
    </ol>
    
    <p>提示：在浏览器中测试API时，建议使用Postman等工具添加认证头。</p>
    
    <h2>快速测试工具</h2>
    <p>为了方便测试，我们提供了简单的API测试工具：</p>
    <ul>
        <li><a href='/api-test/'>API测试工具</a> - 可以直接在浏览器中获取令牌和访问API</li>
    </ul>"""
    return HttpResponse(html_content)

def api_test_tool(request):
    return render(request, 'api_demo.html')

# 自动售卖机后台视图
def vending_machine_dashboard(request):
    return render(request, 'vending_dashboard.html')

# 新的后台管理页面
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

# 工作界面页面
def workspace(request):
    return render(request, 'workspace.html')

# 识别页面视图
def recognition_page_view(request):
    try:
        return render(request, 'products/recognition.html')
    except:
        return HttpResponse("<h1>Recognition Page</h1><p>Template file not found</p>")

urlpatterns = [
    path('', home, name='home'),
    path('api-test/', api_test_tool, name='api_test_tool'),
    
    # 新的管理页面
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('workspace/', workspace, name='workspace'),
    
    # 旧的页面（保留一段时间）
    path('dashboard/', vending_machine_dashboard, name='vending_machine_dashboard'),
    
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/products/', include(api_router.urls)),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/inventory/', include('inventory.urls')),
    # Products页面URL
    path('products/recognition/', recognition_page_view, name='recognition_page'),
    # YOLOv8测试页面
    path('test-yolov8/', test_yolov8_page, name='test_yolov8'),
    path('test-recognize/', test_recognize_view, name='test_recognize'),
    # 系统优化展示页面（根路径）
    path('optimization/', include('products.urls')),
]

# 静态文件和媒体文件的URL配置
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)