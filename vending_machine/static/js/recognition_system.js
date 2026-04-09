// 识别系统前端功能

// 通知功能
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 自动消失
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 摄像头控制
class CameraSystem {
    constructor(videoElementId) {
        this.videoElement = document.getElementById(videoElementId);
        this.stream = null;
    }
    
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.videoElement.srcObject = this.stream;
            showNotification('摄像头已启动', 'success');
            return true;
        } catch (error) {
            console.error('启动摄像头失败:', error);
            showNotification('无法访问摄像头，请检查权限设置', 'error');
            return false;
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.videoElement.srcObject = null;
            this.stream = null;
            showNotification('摄像头已关闭', 'info');
        }
    }
    
    captureImage() {
        const canvas = document.createElement('canvas');
        canvas.width = this.videoElement.videoWidth;
        canvas.height = this.videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg');
    }
}

// 识别系统主类
class RecognitionSystem {
    constructor() {
        this.camera = null;
        this.isRecognizing = false;
        this.lastRecognitionTime = 0;
        this.recognitionInterval = null;
    }
    
    init() {
        // 初始化摄像头系统
        if (document.getElementById('videoElement')) {
            this.camera = new CameraSystem('videoElement');
        }
        
        // 绑定事件处理
        this.bindEvents();
        
        showNotification('识别系统已初始化', 'success');
    }
    
    bindEvents() {
        // 绑定开始识别按钮
        const startBtn = document.getElementById('startRecognition');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startRecognition());
        }
        
        // 绑定停止识别按钮
        const stopBtn = document.getElementById('stopRecognition');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopRecognition());
        }
        
        // 绑定手动识别按钮
        const captureBtn = document.getElementById('captureImage');
        if (captureBtn) {
            captureBtn.addEventListener('click', () => this.recognizeSingleImage());
        }
    }
    
    async startRecognition() {
        // 启动摄像头
        if (!this.camera || !await this.camera.startCamera()) {
            return;
        }
        
        this.isRecognizing = true;
        showNotification('开始自动识别...', 'info');
        
        // 设置定期识别
        this.recognitionInterval = setInterval(() => {
            const now = Date.now();
            // 限制识别频率，避免过于频繁的请求
            if (now - this.lastRecognitionTime > 2000) {
                this.recognizeSingleImage();
                this.lastRecognitionTime = now;
            }
        }, 1000);
    }
    
    stopRecognition() {
        this.isRecognizing = false;
        if (this.recognitionInterval) {
            clearInterval(this.recognitionInterval);
            this.recognitionInterval = null;
        }
        if (this.camera) {
            this.camera.stopCamera();
        }
        showNotification('已停止识别', 'info');
    }
    
    async recognizeSingleImage() {
        if (!this.camera) return;
        
        try {
            // 捕获图像
            const imageData = this.camera.captureImage();
            
            // 显示正在识别的状态
            if (document.getElementById('recognitionStatus')) {
                document.getElementById('recognitionStatus').textContent = '正在识别...';
            }
            
            // 发送到服务器进行识别（这里是模拟，实际需要替换为真实的API调用）
            // 由于是演示环境，使用模拟数据
            setTimeout(() => {
                this.handleRecognitionResult({
                    success: true,
                    products: [
                        { name: '示例商品1', confidence: 0.95 },
                        { name: '示例商品2', confidence: 0.87 }
                    ],
                    image_url: imageData
                });
            }, 500);
            
        } catch (error) {
            console.error('识别失败:', error);
            showNotification('识别过程中发生错误', 'error');
        }
    }
    
    handleRecognitionResult(result) {
        if (result.success) {
            // 更新识别状态
            if (document.getElementById('recognitionStatus')) {
                document.getElementById('recognitionStatus').textContent = '识别完成';
            }
            
            // 更新结果显示
            this.updateRecognitionResults(result.products);
            
            // 更新预览图像
            if (result.image_url && document.getElementById('previewImage')) {
                document.getElementById('previewImage').src = result.image_url;
            }
            
            // 显示识别成功通知
            showNotification(`成功识别到 ${result.products.length} 个商品`, 'success');
        } else {
            if (document.getElementById('recognitionStatus')) {
                document.getElementById('recognitionStatus').textContent = '识别失败';
            }
            showNotification('未识别到任何商品', 'warning');
        }
    }
    
    updateRecognitionResults(products) {
        const resultsContainer = document.getElementById('recognitionResults');
        if (!resultsContainer) return;
        
        // 清空之前的结果
        resultsContainer.innerHTML = '';
        
        if (products.length === 0) {
            resultsContainer.innerHTML = '<p class="no-results">未识别到任何商品</p>';
            return;
        }
        
        // 创建结果列表
        const resultList = document.createElement('div');
        resultList.className = 'recognition-results-list';
        
        products.forEach(product => {
            const productItem = document.createElement('div');
            productItem.className = 'recognition-result-item';
            
            productItem.innerHTML = `
                <div class="product-name">${product.name}</div>
                <div class="confidence-bar">
                    <div class="confidence-value" style="width: ${(product.confidence * 100).toFixed(0)}%"></div>
                </div>
                <div class="confidence-text">可信度: ${(product.confidence * 100).toFixed(1)}%</div>
            `;
            
            resultList.appendChild(productItem);
        });
        
        resultsContainer.appendChild(resultList);
    }
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', () => {
    // 创建识别系统实例
    window.recognitionSystem = new RecognitionSystem();
    window.recognitionSystem.init();
});

// 添加一些样式
const style = document.createElement('style');
style.textContent = `
    /* 通知样式 */
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: opacity 0.3s ease, transform 0.3s ease;
        transform: translateX(0);
    }
    
    .notification-info {
        background-color: #3498db;
    }
    
    .notification-success {
        background-color: #2ecc71;
    }
    
    .notification-warning {
        background-color: #f39c12;
    }
    
    .notification-error {
        background-color: #e74c3c;
    }
    
    .notification.fade-out {
        opacity: 0;
        transform: translateX(100%);
    }
    
    /* 识别结果样式 */
    .recognition-results-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .recognition-result-item {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 6px;
        background-color: #f9f9f9;
    }
    
    .product-name {
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .confidence-bar {
        height: 8px;
        background-color: #eee;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 5px;
    }
    
    .confidence-value {
        height: 100%;
        background-color: #2ecc71;
        transition: width 0.5s ease;
    }
    
    .confidence-text {
        font-size: 12px;
        color: #666;
    }
    
    .no-results {
        text-align: center;
        color: #999;
        padding: 20px;
        font-style: italic;
    }
`;
document.head.appendChild(style);

// 全局变量
let isCameraActive = false;
let videoStreamInterval = null;
let recognitionInterval = null;
let isRecognitionActive = false;
let currentRecognitionResults = [];
let cameraFeedElement = null;
let cameraPlaceholder = null;
let cameraToggleButton = null;
let cameraContainer = null;
let recognitionStatus = null;
let statusMessage = null;
let startRecognitionBtn = null;
let stopRecognitionBtn = null;
let recognitionProcessContainer = null;

/**
 * 初始化识别系统
 */
function initRecognitionSystem() {
    console.log('初始化识别系统');
    
    // 初始化DOM引用
    initializeCameraReferences();
    
    // 设置摄像头按钮
    setupCameraControls();
    
    // 检查摄像头状态
    checkCameraStatus();
}

/**
 * 初始化摄像头相关DOM引用
 */
function initializeCameraReferences() {
    cameraFeedElement = document.getElementById('camera-feed');
    cameraPlaceholder = document.getElementById('camera-placeholder');
    cameraToggleButton = document.getElementById('camera-toggle-btn');
    cameraContainer = document.querySelector('.bg-gray-900.rounded-lg');
    
    // 添加识别相关DOM引用
    recognitionStatus = document.getElementById('recognition-status');
    statusMessage = document.getElementById('status-message');
    startRecognitionBtn = document.getElementById('start-recognition-btn');
    stopRecognitionBtn = document.getElementById('stop-recognition-btn');
    recognitionProcessContainer = document.getElementById('recognition-process-container');
    
    console.log('摄像头DOM引用初始化完成:', {
        cameraFeedElement: !!cameraFeedElement,
        cameraPlaceholder: !!cameraPlaceholder,
        cameraToggleButton: !!cameraToggleButton,
        cameraContainer: !!cameraContainer,
        recognitionStatus: !!recognitionStatus,
        startRecognitionBtn: !!startRecognitionBtn,
        stopRecognitionBtn: !!stopRecognitionBtn,
        recognitionProcessContainer: !!recognitionProcessContainer
    });
}

/**
 * 设置摄像头控制按钮
 */
function setupCameraControls() {
    // 切换摄像头开关
    if (cameraToggleButton) {
        cameraToggleButton.addEventListener('click', function() {
            if (isCameraActive) {
                stopCamera();
            } else {
                startCamera();
            }
        });
    }
    
    // 刷新按钮
    const refreshButton = document.getElementById('refresh-camera-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshCamera);
    }
    
    // 捕获图像按钮
    const captureButton = document.getElementById('capture-image-btn');
    if (captureButton) {
        captureButton.addEventListener('click', captureCameraImage);
    }
    
    // 全屏按钮
    const fullscreenButton = document.getElementById('toggle-fullscreen-btn');
    if (fullscreenButton) {
        fullscreenButton.addEventListener('click', toggleFullscreen);
    }
    
    // 开始识别按钮
    if (startRecognitionBtn) {
        startRecognitionBtn.addEventListener('click', startRecognition);
        startRecognitionBtn.disabled = true;
        startRecognitionBtn.classList.add('opacity-50');
    }
    
    // 停止识别按钮
    if (stopRecognitionBtn) {
        stopRecognitionBtn.addEventListener('click', stopRecognition);
        stopRecognitionBtn.disabled = true;
        stopRecognitionBtn.classList.add('opacity-50');
    }
}

/**
 * 启动摄像头（使用后端API）
 */
function startCamera() {
    console.log('尝试启动摄像头（通过后端API）');
    
    // 重置video元素为img元素
    if (cameraFeedElement && cameraFeedElement.tagName.toLowerCase() === 'video') {
        const imgElement = document.createElement('img');
        imgElement.id = 'camera-feed';
        imgElement.className = 'w-full h-full object-cover';
        imgElement.alt = '摄像头画面';
        cameraFeedElement.parentNode.replaceChild(imgElement, cameraFeedElement);
        cameraFeedElement = imgElement;
    }
    
    // 显示加载状态
    showNotification('正在连接摄像头...', 'info');
    
    // 调用后端API启动摄像头
    fetch('/api/camera/start/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            camera_id: 'default',
            resolution: '1280x720'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('摄像头启动成功');
            showNotification('摄像头启动成功', 'success');
            
            // 启动画面更新循环
            startVideoStreamUpdate();
            
            // 更新UI状态
            updateCameraUI(true);
            
            // 启用识别按钮
            if (startRecognitionBtn) {
                startRecognitionBtn.disabled = false;
                startRecognitionBtn.classList.remove('opacity-50');
            }
            
            // 显示识别过程容器
            if (recognitionProcessContainer) {
                recognitionProcessContainer.style.display = 'block';
            }
        } else {
            console.error('摄像头启动失败:', data.message);
            showNotification(data.message, 'error');
            showCameraError('摄像头启动失败');
        }
    })
    .catch(error => {
        console.error('调用摄像头API失败:', error);
        showNotification('无法连接到服务器，请检查网络连接', 'error');
        showCameraError('服务器连接错误');
    });
}

/**
 * 停止摄像头（使用后端API）
 */
function stopCamera() {
    showNotification('正在关闭摄像头...', 'info');
    
    // 停止识别
    if (isRecognitionActive) {
        stopRecognition();
    }
    
    // 停止视频流更新
    stopVideoStreamUpdate();
    
    // 调用后端API停止摄像头
    fetch('/api/recognition/camera/stop/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('摄像头停止成功');
            
            // 清空图像源
            if (cameraFeedElement) {
                cameraFeedElement.src = '';
            }
            
            // 更新UI状态
            updateCameraUI(false);
            
            // 禁用识别按钮
            if (startRecognitionBtn) {
                startRecognitionBtn.disabled = true;
                startRecognitionBtn.classList.add('opacity-50');
            }
            if (stopRecognitionBtn) {
                stopRecognitionBtn.disabled = true;
                stopRecognitionBtn.classList.add('opacity-50');
            }
            
            // 隐藏识别过程容器
            if (recognitionProcessContainer) {
                recognitionProcessContainer.style.display = 'none';
            }
            
            showNotification('摄像头已关闭', 'success');
        } else {
            console.error('摄像头停止失败:', data.message);
            showNotification('摄像头停止失败', 'error');
        }
    })
    .catch(error => {
        console.error('调用摄像头API失败:', error);
        showNotification('无法连接到服务器', 'error');
    });
}

/**
 * 刷新摄像头
 */
function refreshCamera() {
    showNotification('正在刷新摄像头画面...', 'info');
    
    if (isCameraActive) {
        // 停止并重新启动视频流更新
        stopVideoStreamUpdate();
        startVideoStreamUpdate();
        showNotification('摄像头画面已刷新', 'success');
    } else {
        // 直接启动摄像头
        startCamera();
    }
}

/**
 * 重置视频元素
 */
function resetVideoElement() {
    if (!cameraFeedElement) {
        // 如果不存在，创建一个新的video元素
        const newVideoElement = document.createElement('video');
        newVideoElement.id = 'camera-feed';
        newVideoElement.className = 'w-full h-full object-cover';
        
        // 设置必要的属性
        newVideoElement.autoplay = true;
        newVideoElement.muted = true;
        newVideoElement.playsInline = true;
        
        // 确保正确的样式
        newVideoElement.style.width = '100%';
        newVideoElement.style.height = '100%';
        newVideoElement.style.objectFit = 'cover';
        
        // 添加到容器
        if (cameraContainer) {
            const existingFeed = cameraContainer.querySelector('#camera-feed');
            if (existingFeed) {
                cameraContainer.replaceChild(newVideoElement, existingFeed);
            } else {
                cameraContainer.appendChild(newVideoElement);
            }
        }
        
        // 更新引用
        cameraFeedElement = newVideoElement;
    } else {
        // 清空现有视频源
        cameraFeedElement.src = '';
    }
}

/**
 * 通过后端API更新视频流
 */
function startVideoStreamUpdate() {
    // 停止之前可能存在的更新循环
    if (videoStreamInterval) {
        clearInterval(videoStreamInterval);
    }
    
    // 开始新的更新循环（每33ms更新一次，约30fps）
    videoStreamInterval = setInterval(() => {
        if (isCameraActive && cameraFeedElement) {
            try {
                // 通过URL参数添加时间戳防止缓存
                const timestamp = new Date().getTime();
                
                // 根据是否正在识别，选择不同的API端点
                const endpoint = isRecognitionActive 
                    ? `/api/recognition/camera/detections/?t=${timestamp}` 
                    : `/api/recognition/frame/?t=${timestamp}`;
                
                cameraFeedElement.src = endpoint;
            } catch (error) {
                console.error('更新摄像头画面时发生错误:', error);
            }
        }
    }, 33);
}

/**
 * 停止视频流更新
 */
function stopVideoStreamUpdate() {
    if (videoStreamInterval) {
        clearInterval(videoStreamInterval);
        videoStreamInterval = null;
    }
}

/**
 * 捕获摄像头画面
 */
function captureCameraImage() {
    if (!isCameraActive) {
        showNotification('请先开启摄像头', 'warning');
        return;
    }
    
    showNotification('正在捕获画面并识别商品...', 'info');
    
    // 创建一个临时图片元素获取当前帧
    const tempImage = new Image();
    tempImage.crossOrigin = 'anonymous';
    tempImage.onload = function() {
        try {
            // 创建canvas元素
            const canvas = document.createElement('canvas');
            canvas.width = tempImage.width;
            canvas.height = tempImage.height;
            
            // 在canvas上绘制图像
            const ctx = canvas.getContext('2d');
            ctx.drawImage(tempImage, 0, 0);
            
            // 转换为图片URL
            const imageUrl = canvas.toDataURL('image/png');
            
            // 发送到后端进行识别
            recognizeProductsFromFrame(imageUrl);
        } catch (error) {
            console.error('捕获画面失败:', error);
            showNotification('捕获画面失败', 'error');
        }
    };
    
    // 设置图片源，添加时间戳防止缓存
    const timestamp = new Date().getTime();
    tempImage.src = `/api/recognition/frame/?t=${timestamp}`;
}

/**
 * 从当前帧识别商品
 */
function recognizeProductsFromFrame(imageUrl) {
    // 提取base64数据
    const base64Data = imageUrl.split(',')[1];
    
    // 发送到后端进行识别
    fetch('/api/recognition/recognize/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ image: base64Data })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('商品识别成功:', data.products);
            showNotification(`成功识别到 ${data.count} 件商品`, 'success');
            
            // 更新识别结果到UI
            updateRecognitionResults(data.products, data.total_price);
            
            // 保存当前识别结果
            currentRecognitionResults = data.products;
        } else {
            console.error('商品识别失败:', data.message);
            showNotification('商品识别失败', 'error');
        }
    })
    .catch(error => {
        console.error('调用识别API失败:', error);
        showNotification('识别服务暂时不可用', 'error');
    });
}

/**
 * 更新识别结果到UI
 */
function updateRecognitionResults(products, totalPrice) {
    const resultsContainer = document.getElementById('recognition-results');
    if (!resultsContainer) return;
    
    // 清空现有结果
    resultsContainer.innerHTML = '';
    
    // 添加商品列表
    const productsList = document.createElement('div');
    productsList.className = 'space-y-2';
    
    products.forEach(product => {
        const productItem = document.createElement('div');
        productItem.className = 'flex justify-between items-center p-2 bg-white/10 rounded';
        productItem.innerHTML = `
            <div>
                <h4 class="font-medium text-white">${product.name}</h4>
                ${product.barcode ? `<span class="text-xs text-gray-300">条码: ${product.barcode}</span>` : ''}
            </div>
            <span class="text-lg font-semibold text-yellow-400">¥${product.price.toFixed(2)}</span>
        `;
        productsList.appendChild(productItem);
    });
    
    // 添加总价
    const totalDiv = document.createElement('div');
    totalDiv.className = 'mt-4 p-3 bg-primary/20 rounded-lg border border-primary/30';
    totalDiv.innerHTML = `
        <div class="flex justify-between items-center">
            <span class="text-white text-lg font-medium">商品总价</span>
            <span class="text-yellow-400 text-xl font-bold">¥${totalPrice.toFixed(2)}</span>
        </div>
    `;
    
    resultsContainer.appendChild(productsList);
    resultsContainer.appendChild(totalDiv);
    
    // 显示结果容器
    resultsContainer.style.display = 'block';
    
    // 如果是实时识别模式，更新识别过程UI
    if (isRecognitionActive) {
        updateRecognitionStepsUI({
            'step1': { completed: true, message: '已捕获商品图像' },
            'step2': { completed: true, message: `识别到${products.length}件商品` },
            'step3': { completed: true, message: `总价计算完成：¥${totalPrice.toFixed(2)}` }
        });
    }
}

/**
 * 切换全屏显示
 */
function toggleFullscreen() {
    if (!cameraContainer) {
        console.error('找不到摄像头容器元素');
        return;
    }
    
    try {
        if (!document.fullscreenElement) {
            // 进入全屏
            if (cameraContainer.requestFullscreen) {
                cameraContainer.requestFullscreen();
            } else if (cameraContainer.webkitRequestFullscreen) { /* Safari */
                cameraContainer.webkitRequestFullscreen();
            } else if (cameraContainer.msRequestFullscreen) { /* IE11 */
                cameraContainer.msRequestFullscreen();
            }
        } else {
            // 退出全屏
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) { /* Safari */
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) { /* IE11 */
                document.msExitFullscreen();
            }
        }
    } catch (error) {
        console.error('全屏操作失败:', error);
        showNotification('全屏操作失败', 'error');
    }
}

/**
 * 更新摄像头UI状态
 */
function updateCameraUI(isActive) {
    isCameraActive = isActive;
    
    // 更新按钮样式
    if (cameraToggleButton) {
        if (isActive) {
            cameraToggleButton.classList.remove('bg-danger/80');
            cameraToggleButton.classList.add('bg-success');
        } else {
            cameraToggleButton.classList.remove('bg-success');
            cameraToggleButton.classList.add('bg-danger/80');
        }
    }
    
    // 更新占位层显示
    if (cameraPlaceholder) {
        cameraPlaceholder.style.display = isActive ? 'none' : 'flex';
    }
    
    // 更新实时监控标记
    if (cameraContainer) {
        let liveIndicator = document.getElementById('camera-live-indicator');
        
        if (isActive) {
            if (!liveIndicator) {
                liveIndicator = document.createElement('div');
                liveIndicator.id = 'camera-live-indicator';
                liveIndicator.className = 'absolute top-4 left-4 bg-red-600 text-white text-xs px-2 py-1 rounded-full flex items-center';
                liveIndicator.innerHTML = `<span class="inline-block w-2 h-2 bg-white rounded-full mr-1 animate-pulse"></span>实时监控`;
                cameraContainer.appendChild(liveIndicator);
            } else {
                liveIndicator.style.display = 'flex';
            }
        } else if (liveIndicator) {
            liveIndicator.style.display = 'none';
        }
    }
}

/**
 * 显示摄像头错误信息
 */
function showCameraError(message) {
    if (cameraPlaceholder) {
        cameraPlaceholder.innerHTML = `
            <div class="text-white text-center p-6">
                <i class="fa fa-exclamation-triangle text-6xl mb-4 text-yellow-500"></i>
                <h3 class="text-xl font-semibold mb-2">${message.split('\n')[0]}</h3>
                ${message.split('\n').length > 1 ? `<p class="text-gray-300">${message.split('\n')[1]}</p>` : ''}
                <button id="retry-camera-btn" class="mt-4 bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-md transition-colors">
                    重试连接
                </button>
            </div>
        `;
        cameraPlaceholder.style.display = 'flex';
        
        // 添加重试按钮事件
        setTimeout(() => {
            const retryBtn = document.getElementById('retry-camera-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', startCamera);
            }
        }, 100);
    }
}

/**
 * 检查摄像头状态
 */
function checkCameraStatus() {
    fetch('/recognition/camera/status/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.status.is_running) {
                console.log('摄像头已在运行');
                isCameraActive = true;
                updateCameraUI(true);
                startVideoStreamUpdate();
                
                // 启用识别按钮
                if (startRecognitionBtn) {
                    startRecognitionBtn.disabled = false;
                    startRecognitionBtn.classList.remove('opacity-50');
                }
                
                // 显示识别过程容器
                if (recognitionProcessContainer) {
                    recognitionProcessContainer.style.display = 'block';
                }
            }
        })
        .catch(error => {
            console.error('获取摄像头状态失败:', error);
        });
}

/**
 * 开始商品识别
 */
function startRecognition() {
    if (!isCameraActive) {
        showNotification('请先启动摄像头', 'warning');
        return;
    }
    
    console.log('开始商品识别...');
    isRecognitionActive = true;
    
    // 更新状态显示
    if (recognitionStatus) {
        recognitionStatus.classList.remove('hidden');
    }
    if (statusMessage) {
        statusMessage.textContent = '正在识别商品...';
    }
    
    // 更新按钮状态
    if (startRecognitionBtn) {
        startRecognitionBtn.disabled = true;
        startRecognitionBtn.classList.add('opacity-50');
    }
    if (stopRecognitionBtn) {
        stopRecognitionBtn.disabled = false;
        stopRecognitionBtn.classList.remove('opacity-50');
    }
    
    showNotification('开始商品识别', 'info');
    
    // 更新识别过程UI
    updateRecognitionStepsUI({
        'step1': { completed: true, message: '已捕获商品图像，正在进行识别' },
        'step2': { completed: false, message: '正在进行商品识别...' },
        'step3': { completed: false, message: '等待识别结果...' }
    });
    
    // 立即获取一次识别结果
    fetchRecognitionResults();
    
    // 开始定期获取识别结果（每秒一次）
    recognitionInterval = setInterval(fetchRecognitionResults, 1000);
}

/**
 * 停止商品识别
 */
function stopRecognition() {
    console.log('停止商品识别...');
    isRecognitionActive = false;
    currentRecognitionResults = [];
    
    // 停止识别结果获取
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
    
    // 更新状态显示
    if (recognitionStatus) {
        recognitionStatus.classList.add('hidden');
    }
    if (statusMessage) {
        statusMessage.textContent = '识别系统就绪';
    }
    
    // 更新按钮状态
    if (startRecognitionBtn) {
        startRecognitionBtn.disabled = false;
        startRecognitionBtn.classList.remove('opacity-50');
    }
    if (stopRecognitionBtn) {
        stopRecognitionBtn.disabled = true;
        stopRecognitionBtn.classList.add('opacity-50');
    }
    
    // 重置识别过程UI
    updateRecognitionStepsUI({
        'step1': { completed: false, message: '等待开始识别' },
        'step2': { completed: false, message: '等待开始识别' },
        'step3': { completed: false, message: '等待开始识别' }
    });
    
    showNotification('已停止商品识别', 'info');
}

/**
 * 获取识别结果
 */
function fetchRecognitionResults() {
    if (!isRecognitionActive) return;
    
    fetch('/recognition/results/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                currentRecognitionResults = data.results || [];
                
                if (currentRecognitionResults.length > 0) {
                    // 计算总价
                    const totalPrice = currentRecognitionResults.reduce((sum, item) => sum + (item.price || 0), 0);
                    
                    // 更新识别结果UI
                    updateRecognitionResults(currentRecognitionResults, totalPrice);
                    
                    // 更新状态消息
                    if (statusMessage) {
                        statusMessage.textContent = `已识别 ${currentRecognitionResults.length} 件商品`;
                    }
                }
            } else {
                console.error('获取识别结果失败:', data.message);
            }
        })
        .catch(error => {
            console.error('获取识别结果时发生错误:', error);
        });
}

/**
 * 更新识别过程步骤UI
 */
function updateRecognitionStepsUI(stepStatuses) {
    const steps = document.querySelectorAll('#recognition-process-container .space-y-4 > div');
    
    if (!steps.length) return;
    
    // 更新每个步骤
    steps.forEach((step, index) => {
        const stepKey = `step${index + 1}`;
        const status = stepStatuses[stepKey];
        
        if (status) {
            // 更新图标
            const iconDiv = step.querySelector('div:first-child');
            const icon = iconDiv.querySelector('i');
            
            if (iconDiv && icon) {
                if (status.completed) {
                    iconDiv.className = 'w-10 h-10 rounded-full bg-success/10 flex items-center justify-center flex-shrink-0';
                    icon.className = 'fa fa-check text-success';
                } else {
                    iconDiv.className = 'w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0';
                    icon.className = 'fa fa-circle-o text-gray-400';
                }
            }
            
            // 更新消息
            const messageP = step.querySelector('div:nth-child(2) p:nth-child(2)');
            if (messageP) {
                messageP.textContent = status.message || '';
            }
            
            // 更新时间
            const timeSpan = step.querySelector('div:nth-child(2) div span');
            if (timeSpan && status.completed) {
                const now = new Date();
                const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
                              now.getMinutes().toString().padStart(2, '0') + ':' +
                              now.getSeconds().toString().padStart(2, '0');
                timeSpan.textContent = timeStr;
            }
        }
    });
}

/**
 * 获取CSRF令牌
 */
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')// 注意这里分号后有空格
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    // 这里可以使用项目现有的通知系统
    // 如果没有，创建一个简单的通知
    const notificationContainer = document.createElement('div');
    notificationContainer.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 transition-opacity duration-300 ${getNotificationClass(type)}`;
    notificationContainer.innerHTML = `
        <div class="flex items-center">
            <i class="fa ${getNotificationIcon(type)} mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notificationContainer);
    
    // 3秒后自动关闭
    setTimeout(() => {
        notificationContainer.style.opacity = '0';
        setTimeout(() => {
            if (notificationContainer.parentNode) {
                notificationContainer.parentNode.removeChild(notificationContainer);
            }
        }, 300);
    }, 3000);
}

/**
 * 获取通知样式类
 */
function getNotificationClass(type) {
    switch (type) {
        case 'success':
            return 'bg-success text-white';
        case 'error':
            return 'bg-danger text-white';
        case 'warning':
            return 'bg-warning text-white';
        case 'info':
        default:
            return 'bg-primary text-white';
    }
}

/**
 * 获取通知图标
 */
function getNotificationIcon(type) {
    switch (type) {
        case 'success':
            return 'fa-check-circle';
        case 'error':
            return 'fa-times-circle';
        case 'warning':
            return 'fa-exclamation-triangle';
        case 'info':
        default:
            return 'fa-info-circle';
    }
}

// 在页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRecognitionSystem);
} else {
    initRecognitionSystem();
}