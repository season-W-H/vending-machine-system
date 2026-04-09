// 库存管理页面JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面功能
    initInventoryPage();
});

// 初始化库存页面
function initInventoryPage() {
    console.log('初始化库存管理页面...');
    
    // 加载库存数据
    loadInventoryData();
    
    // 加载商品类别
    loadProductCategories();
    
    // 加载最近操作
    loadRecentOperations();
    
    // 加载库存预警
    loadInventoryAlerts();
    
    // 加载库存统计
    loadInventoryStatistics();
    
    // 绑定事件监听器
    bindEventListeners();
    
    console.log('库存管理页面初始化完成');
}

// 加载库存统计数据
function loadInventoryStatistics() {
    console.log('加载库存统计数据...');
    
    fetch('/optimization/api/products/?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
            // DRF分页返回的是对象，包含results字段
            const products = data.results || data;
            if (!Array.isArray(products)) {
                console.error('商品数据格式错误:', products);
                return;
            }
            
            // 计算统计数据
            const totalProducts = products.length;
            const totalItems = products.reduce((sum, p) => sum + parseInt(p.stock || p.quantity || 0), 0);
            const lowStock = products.filter(p => {
                const qty = parseInt(p.stock || p.quantity || 0);
                const threshold = parseInt(p.low_stock_threshold || 10);
                return qty > 0 && qty <= threshold;
            }).length;
            const outOfStock = products.filter(p => {
                const qty = parseInt(p.stock || p.quantity || 0);
                return qty <= 0;
            }).length;
            
            // 更新页面显示
            document.getElementById('total-products-count').textContent = totalProducts;
            document.getElementById('total-items-count').textContent = totalItems;
            document.getElementById('low-stock-count').textContent = lowStock;
            document.getElementById('out-of-stock-count').textContent = outOfStock;
            
            console.log('库存统计数据加载成功:', { totalProducts, totalItems, lowStock, outOfStock });
        })
        .catch(error => {
            console.error('加载库存统计数据失败:', error);
        });
}

// 绑定事件监听器
function bindEventListeners() {
    // 应用筛选按钮
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // 重置筛选按钮
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // 添加库存按钮
    const addStockBtn = document.getElementById('add-stock-btn');
    if (addStockBtn) {
        addStockBtn.addEventListener('click', () => openStockOperationModal('add'));
    }
    
    // 调整库存按钮
    const adjustStockBtn = document.getElementById('adjust-stock-btn');
    if (adjustStockBtn) {
        adjustStockBtn.addEventListener('click', () => openStockOperationModal('set'));
    }
    
    // 设置预警阈值按钮
    const setThresholdBtn = document.getElementById('set-threshold-btn');
    if (setThresholdBtn) {
        setThresholdBtn.addEventListener('click', openSetThresholdModal);
    }
    
    // 刷新数据按钮
    const refreshBtn = document.getElementById('refresh-inventory-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshAllData);
    }
    
    // 库存状态筛选器
    const statusFilter = document.getElementById('inventory-status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }
    
    // 类别筛选器
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', applyFilters);
    }
    
    // 提交库存操作表单
    const stockForm = document.getElementById('stock-operation-form');
    if (stockForm) {
        stockForm.addEventListener('submit', handleStockOperation);
    }
}

// 加载库存数据
function loadInventoryData(filters = {}) {
    console.log('加载库存数据...', filters);
    
    const inventoryContainer = document.getElementById('inventory-container');
    if (!inventoryContainer) {
        console.error('未找到库存容器');
        return;
    }
    
    // 显示加载状态
    inventoryContainer.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在加载库存数据...</p>
        </div>
    `;
    
    // 构建API URL（添加时间戳防止缓存）
    let url = '/optimization/api/products/';
    const params = new URLSearchParams();
    params.append('t', Date.now()); // 添加时间戳防止缓存
    
    if (filters.status) {
        params.append('status', filters.status);
    }
    if (filters.category) {
        params.append('category', filters.category);
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    // 发起API请求
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('库存数据加载成功:', data);
            // DRF分页返回的是对象，包含results字段
            const products = data.results || data;
            displayInventoryData(Array.isArray(products) ? products : []);
        })
        .catch(error => {
            console.error('加载库存数据失败:', error);
            inventoryContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    加载库存数据失败: ${error.message}
                </div>
            `;
        });
}

// 显示库存数据
function displayInventoryData(products) {
    const inventoryContainer = document.getElementById('inventory-container');
    
    if (!products || products.length === 0) {
        inventoryContainer.innerHTML = `
            <div class="alert alert-info" role="alert">
                <i class="bi bi-info-circle-fill me-2"></i>
                暂无库存数据
            </div>
        `;
        return;
    }
    
    // 按类别分组
    const groupedProducts = {};
    products.forEach(product => {
        const category = product.category || '未分类';
        if (!groupedProducts[category]) {
            groupedProducts[category] = [];
        }
        groupedProducts[category].push(product);
    });
    
    let html = '';
    
    for (const [category, categoryProducts] of Object.entries(groupedProducts)) {
        html += `
            <div class="mb-4">
                <h4 class="mb-3">${category}</h4>
                <div class="row">
        `;
        
        categoryProducts.forEach(product => {
            const stockStatus = getStockStatus(product);
            const stockClass = stockStatus.class;
            const stockText = stockStatus.text;
            const stockLevel = stockStatus.level;
            
            html += `
                <div class="col-lg-4 col-md-6 mb-3">
                    <div class="inventory-card ${stockClass}" data-product-id="${product.id}">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="mb-1">${product.name}</h5>
                            <span class="badge ${getStockBadgeClass(stockLevel)}">${stockText}</span>
                        </div>
                        
                        <p class="text-muted mb-2">
                            <small>SKU: ${product.sku || 'N/A'}</small>
                        </p>
                        
                        <div class="mb-2">
                            <div class="d-flex justify-content-between mb-1">
                                <span class="fw-bold">当前库存:</span>
                                <span>${product.stock || 0}</span>
                            </div>
                            <div class="d-flex justify-content-between mb-1">
                                <span class="fw-bold">预警阈值:</span>
                                <span>${product.low_stock_threshold || 10}</span>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span class="fw-bold">单价:</span>
                                <span>¥${parseFloat(product.price || 0).toFixed(2)}</span>
                            </div>
                        </div>
                        
                        <div class="stock-indicator">
                            <div class="stock-level ${stockLevel}" 
                                 style="width: ${getStockLevelPercentage(product)}%"></div>
                        </div>
                        
                        <div class="mt-3">
                            <button class="btn btn-sm btn-outline-primary w-100 view-details-btn"
                                    data-product-id="${product.id}">
                                <i class="bi bi-eye me-1"></i>查看详情
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    inventoryContainer.innerHTML = html;
    
    // 绑定查看详情按钮事件
    bindViewDetailsEvents();
}

// 获取库存状态
function getStockStatus(product) {
    const quantity = parseInt(product.stock || 0);
    const threshold = parseInt(product.low_stock_threshold || 10);
    
    if (quantity <= 0) {
        return { class: 'out-of-stock', text: '缺货', level: 'low' };
    } else if (quantity <= threshold) {
        return { class: 'low-stock', text: '库存不足', level: 'medium' };
    } else {
        return { class: '', text: '库存充足', level: 'high' };
    }
}

// 获取库存徽章样式
function getStockBadgeClass(level) {
    const classes = {
        'high': 'bg-success',
        'medium': 'bg-warning',
        'low': 'bg-danger'
    };
    return classes[level] || 'bg-secondary';
}

// 获取库存指示器样式
function getStockIndicatorClass(level) {
    const classes = {
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    };
    return classes[level] || 'medium';
}

// 获取库存水平百分比
function getStockLevelPercentage(product) {
    const quantity = parseInt(product.stock || 0);
    const threshold = parseInt(product.low_stock_threshold || 10);
    const maxStock = threshold * 3;
    
    if (quantity >= maxStock) return 100;
    if (quantity <= 0) return 0;
    
    return Math.min((quantity / maxStock) * 100, 100);
}

// 绑定查看详情事件
function bindViewDetailsEvents() {
    const viewDetailsBtns = document.querySelectorAll('.view-details-btn');
    viewDetailsBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            viewProductDetails(productId);
        });
    });
}

// 查看商品详情
function viewProductDetails(productId) {
    console.log('查看商品详情:', productId);
    
    fetch(`/optimization/api/products/${productId}/?t=` + Date.now())
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(product => {
            console.log('商品详情:', product);
            displayProductDetails(product);
            $('#inventoryDetailModal').modal('show');
        })
        .catch(error => {
            console.error('加载商品详情失败:', error);
            showAlert('加载商品详情失败: ' + error.message, 'danger');
        });
}

// 显示商品详情
function displayProductDetails(product) {
    const contentContainer = document.getElementById('inventory-detail-content');
    
    const stockStatus = getStockStatus(product);
    
    contentContainer.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h5>${product.name}</h5>
                <p class="text-muted">SKU: ${product.sku || 'N/A'}</p>
                
                <div class="mb-3">
                    <h6>库存信息</h6>
                    <ul class="list-unstyled">
                        <li><strong>当前库存:</strong> ${product.stock || 0}</li>
                        <li><strong>预警阈值:</strong> ${product.low_stock_threshold || 10}</li>
                        <li><strong>状态:</strong> <span class="badge ${getStockBadgeClass(stockStatus.level)}">${stockStatus.text}</span></li>
                    </ul>
                </div>
                
                <div class="mb-3">
                    <h6>商品信息</h6>
                    <ul class="list-unstyled">
                        <li><strong>单价:</strong> ¥${parseFloat(product.price || 0).toFixed(2)}</li>
                        <li><strong>类别:</strong> ${product.category || '未分类'}</li>
                        <li><strong>品牌:</strong> ${product.brand || 'N/A'}</li>
                    </ul>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="mb-3">
                    <h6>库存操作</h6>
                    <div class="d-grid gap-2">
                        <button class="btn btn-sm btn-primary" onclick="openStockOperationModal('add', ${product.id})">
                            <i class="bi bi-plus-lg me-1"></i>添加库存
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="openStockOperationModal('subtract', ${product.id})">
                            <i class="bi bi-dash-lg me-1"></i>减少库存
                        </button>
                        <button class="btn btn-sm btn-info" onclick="openSetThresholdModal(${product.id})">
                            <i class="bi bi-sliders me-1"></i>设置阈值
                        </button>
                    </div>
                </div>
                
                <div class="mb-3">
                    <h6>最近更新</h6>
                    <p class="text-muted small">
                        ${product.updated_at ? new Date(product.updated_at).toLocaleString('zh-CN') : 'N/A'}
                    </p>
                </div>
            </div>
        </div>
    `;
}

// 加载商品类别
function loadProductCategories() {
    console.log('加载商品类别...');
    
    const categoryFilter = document.getElementById('category-filter');
    if (!categoryFilter) return;
    
    fetch('/optimization/api/products/?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
            // DRF分页返回的是对象，包含results字段
            const products = data.results || data;
            if (!Array.isArray(products)) {
                console.error('商品数据格式错误:', products);
                return;
            }
            
            const categories = [...new Set(products.map(p => p.category).filter(c => c))].sort();
            
            let options = '<option value="">全部类别</option>';
            categories.forEach(category => {
                options += `<option value="${category}">${category}</option>`;
            });
            
            categoryFilter.innerHTML = options;
            console.log('商品类别加载成功:', categories);
        })
        .catch(error => {
            console.error('加载商品类别失败:', error);
        });
}

// 加载最近操作
function loadRecentOperations() {
    console.log('加载最近操作...');
    
    const container = document.getElementById('recent-operations-container');
    if (!container) return;
    
    fetch('/optimization/api/stock-operations/?limit=5&t=' + Date.now())
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // DRF分页返回的是对象，包含results字段
            const operations = data.results || data;
            console.log('最近操作加载成功:', operations);
            displayRecentOperations(Array.isArray(operations) ? operations : []);
        })
        .catch(error => {
            console.error('加载最近操作失败:', error);
            container.innerHTML = `
                <div class="alert alert-warning" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    无法加载最近操作
                </div>
            `;
        });
}

// 显示最近操作
function displayRecentOperations(operations) {
    const container = document.getElementById('recent-operations-container');
    
    if (!operations || operations.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">暂无操作记录</p>';
        return;
    }
    
    let html = '<ul class="list-group">';
    operations.forEach(op => {
        const icon = getOperationIcon(op.operation_type);
        const className = getOperationClass(op.operation_type);
        
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi ${icon} me-2 ${className}"></i>
                    <strong>${op.product_name}</strong>
                    <span class="text-muted ms-2">${getOperationText(op)}</span>
                </div>
                <small class="text-muted">${new Date(op.created_at).toLocaleString('zh-CN')}</small>
            </li>
        `;
    });
    html += '</ul>';
    
    container.innerHTML = html;
}

// 获取操作图标
function getOperationIcon(type) {
    const icons = {
        'add': 'bi-plus-circle',
        'subtract': 'bi-dash-circle',
        'set': 'bi-gear'
    };
    return icons[type] || 'bi-circle';
}

// 获取操作样式
function getOperationClass(type) {
    const classes = {
        'add': 'text-success',
        'subtract': 'text-danger',
        'set': 'text-info'
    };
    return classes[type] || 'text-secondary';
}

// 获取操作文本
function getOperationText(op) {
    const texts = {
        'add': `+${op.quantity}`,
        'subtract': `-${op.quantity}`,
        'set': `设置为 ${op.quantity}`
    };
    return texts[op.operation_type] || op.operation_type;
}

// 加载库存预警
function loadInventoryAlerts() {
    console.log('加载库存预警...');
    
    const container = document.getElementById('inventory-alerts-container');
    if (!container) return;
    
    fetch('/optimization/api/products/?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
            // DRF分页返回的是对象，包含results字段
            const products = data.results || data;
            if (!Array.isArray(products)) {
                console.error('商品数据格式错误:', products);
                return;
            }
            
            const alerts = products.filter(p => {
                const qty = parseInt(p.quantity || p.stock || 0);
                const threshold = parseInt(p.low_stock_threshold || 10);
                return qty <= threshold;
            });
            
            console.log('库存预警加载成功:', alerts);
            displayInventoryAlerts(alerts);
        })
        .catch(error => {
            console.error('加载库存预警失败:', error);
        });
}

// 显示库存预警
function displayInventoryAlerts(alerts) {
    const container = document.getElementById('inventory-alerts-container');
    
    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="alert alert-success" role="alert">
                <i class="bi bi-check-circle-fill me-2"></i>
                所有商品库存正常
            </div>
        `;
        return;
    }
    
    let html = '';
    alerts.forEach(product => {
        const qty = product.stock || 0;
        const threshold = product.low_stock_threshold || 10;
        const isCritical = qty <= 0;
        
        html += `
            <div class="alert ${isCritical ? 'alert-danger' : 'alert-warning'} alert-dismissible fade show" role="alert">
                <i class="bi ${isCritical ? 'bi-exclamation-triangle-fill' : 'bi-exclamation-circle-fill'} me-2"></i>
                <strong>${product.name}</strong> - ${isCritical ? '已缺货' : '库存不足'}
                <br>
                <small>当前库存: ${qty}，预警阈值: ${threshold}</small>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 应用筛选
function applyFilters() {
    console.log('应用筛选...');
    
    const statusFilter = document.getElementById('inventory-status-filter');
    const categoryFilter = document.getElementById('category-filter');
    
    const filters = {
        status: statusFilter ? statusFilter.value : '',
        category: categoryFilter ? categoryFilter.value : ''
    };
    
    loadInventoryData(filters);
}

// 重置筛选
function resetFilters() {
    console.log('重置筛选...');
    
    const statusFilter = document.getElementById('inventory-status-filter');
    const categoryFilter = document.getElementById('category-filter');
    
    if (statusFilter) statusFilter.value = '';
    if (categoryFilter) categoryFilter.value = '';
    
    loadInventoryData();
}

// 打开库存操作模态框
function openStockOperationModal(operationType, productId = null) {
    console.log('打开库存操作模态框:', operationType, productId);
    
    const form = document.getElementById('stock-operation-form');
    const operationTypeSelect = document.getElementById('operation-type');
    const productSelect = document.getElementById('operation-product');
    const quantityInput = document.getElementById('operation-quantity');
    const reasonInput = document.getElementById('operation-reason');
    
    // 重置表单
    form.reset();
    
    // 设置操作类型
    if (operationTypeSelect) {
        operationTypeSelect.value = operationType;
    }
    
    // 加载商品列表
    loadProductsForSelect(productSelect, productId);
    
    // 设置数量默认值
    if (quantityInput) {
        quantityInput.value = operationType === 'add' ? '10' : '1';
    }
    
    // 显示模态框
    modal.show();
}

// 加载商品到下拉选择框
function loadProductsForSelect(selectElement, selectedProductId = null) {
    if (!selectElement) return;
    
    fetch('/optimization/api/products/?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
            // DRF分页返回的是对象，包含results字段
            const products = data.results || data;
            if (!Array.isArray(products)) {
                console.error('商品数据格式错误:', products);
                selectElement.innerHTML = '<option value="">加载失败</option>';
                return;
            }
            
            let options = '<option value="">请选择商品</option>';
            products.forEach(product => {
                const selected = product.id === selectedProductId ? 'selected' : '';
                options += `<option value="${product.id}" ${selected}>${product.name}</option>`;
            });
            selectElement.innerHTML = options;
        })
        .catch(error => {
            console.error('加载商品列表失败:', error);
            selectElement.innerHTML = '<option value="">加载失败</option>';
        });
}

// 处理库存操作
function handleStockOperation(event) {
    event.preventDefault();
    
    console.log('处理库存操作...');
    
    const formData = new FormData(this);
    const productId = formData.get('operation-product');
    const operationType = formData.get('operation-type');
    const quantity = parseInt(formData.get('operation-quantity'));
    const reason = formData.get('operation-reason');
    
    if (!productId || !operationType || isNaN(quantity) || quantity <= 0) {
        showAlert('请填写完整信息', 'warning');
        return;
    }
    
    const data = {
        product: parseInt(productId),
        operation_type: operationType,
        quantity: quantity,
        reason: reason || ''
    };
    
    fetch('/optimization/api/stock-operations/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        console.log('库存操作成功:', result);
        showAlert('库存操作成功', 'success');
        
        // 关闭模态框
        $('#stockOperationModal').modal('hide');
        
        // 刷新数据
        refreshAllData();
    })
    .catch(error => {
        console.error('库存操作失败:', error);
        showAlert('库存操作失败: ' + error.message, 'danger');
    });
}

// 打开设置阈值模态框
function openSetThresholdModal(productId = null) {
    console.log('打开设置阈值模态框:', productId);
    
    // 这里可以实现设置阈值的功能
    showAlert('设置阈值功能开发中...', 'info');
}

// 刷新所有数据
function refreshAllData() {
    console.log('刷新所有数据...');
    
    loadInventoryData();
    loadRecentOperations();
    loadInventoryAlerts();
    loadInventoryStatistics();
    
    showAlert('数据已刷新', 'success');
}

// 显示提示信息
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="bi bi-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动关闭
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

// 获取提示图标
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle-fill',
        'danger': 'exclamation-triangle-fill',
        'warning': 'exclamation-circle-fill',
        'info': 'info-circle-fill'
    };
    return icons[type] || 'info-circle-fill';
}

// 获取Cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 全局函数，供HTML调用
window.openStockOperationModal = openStockOperationModal;
window.openSetThresholdModal = openSetThresholdModal;