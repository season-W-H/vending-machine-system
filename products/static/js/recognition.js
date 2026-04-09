// 识别页面JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 延迟初始化WebSocket连接，等待页面完全加载
    setTimeout(() => {
        initWebSocket();
    }, 1000);
    
    // 初始化页面功能
    initRecognitionPage();
});

// WebSocket连接管理
let recognitionSocket = null;
let isConnected = false;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function initWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/recognition/`;
    console.log('尝试连接WebSocket:', wsUrl);
    
    try {
        recognitionSocket = new WebSocket(wsUrl);
        
        recognitionSocket.onopen = function(event) {
            isConnected = true;
            reconnectAttempts = 0;
            console.log('WebSocket连接已建立');
            updateConnectionStatus(true);
            
            // 获取初始状态
            getRecognitionStatus();
        };
        
        recognitionSocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('解析WebSocket消息错误:', e);
            }
        };
        
        recognitionSocket.onclose = function(event) {
            isConnected = false;
            console.log('WebSocket连接已关闭，代码:', event.code, '原因:', event.reason);
            updateConnectionStatus(false);
            
            // 尝试重新连接（限制重试次数）
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`尝试重新连接 (${reconnectAttempts}/${maxReconnectAttempts})`);
                setTimeout(() => {
                    if (!isConnected) {
                        initWebSocket();
                    }
                }, 3000 * reconnectAttempts);
            } else {
                console.log('已达到最大重试次数，停止重连');
            }
        };
        
        recognitionSocket.onerror = function(error) {
            console.error('WebSocket错误:', error);
        };
        
    } catch (e) {
        console.error('创建WebSocket连接失败:', e);
    }
}

function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connection-status');
    if (statusIndicator) {
        if (connected) {
            statusIndicator.className = 'badge bg-success';
            statusIndicator.textContent = '已连接';
        } else {
            statusIndicator.className = 'badge bg-danger';
            statusIndicator.textContent = '已断开';
        }
    }
}

function handleWebSocketMessage(data) {
    console.log('收到WebSocket消息:', data);
    
    switch(data.type) {
        case 'connection':
            console.log('WebSocket连接确认:', data.message);
            break;
        case 'recognition_result':
            handleRecognitionResult(data.data);
            break;
        case 'auto_flow_status':
            updateAutoFlowStatus(data.data);
            break;
        case 'order_update':
            updateOrderStats(data.data);
            break;
        case 'inventory_update':
            updateInventoryStats(data.data);
            break;
        case 'performance_metrics':
            updatePerformanceMetrics(data.data);
            break;
        default:
            console.log('未知的消息类型:', data.type);
    }
}

// 识别页面初始化
function initRecognitionPage() {
    // 初始化摄像头控制
    initCameraControls();
    
    // 初始化自动识别流程
    initAutoFlowControls();
    
    // 初始化识别结果展示
    initRecognitionResults();
    
    // 初始化性能监控
    initPerformanceMonitor();
    
    // 初始化设置面板
    initSettingsPanel();
}

// 摄像头控制
function initCameraControls() {
    const startCameraBtn = document.getElementById('start-camera-btn');
    const stopCameraBtn = document.getElementById('stop-camera-btn');
    const cameraStatus = document.getElementById('camera-status');
    
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startCamera);
    }
    
    if (stopCameraBtn) {
        stopCameraBtn.addEventListener('click', stopCamera);
    }
    
    // 检查摄像头状态
    checkCameraStatus();
}

function startCamera() {
    fetch('/api/camera/start/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateCameraStatus('active');
                startVideoStream();
                showAlert('摄像头启动成功', 'success');
            } else {
                showAlert('摄像头启动失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('启动摄像头错误:', error);
            showAlert('启动摄像头时发生错误', 'error');
        });
}

function stopCamera() {
    fetch('/api/camera/stop/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateCameraStatus('stopped');
                stopVideoStream();
                showAlert('摄像头停止成功', 'success');
            } else {
                showAlert('摄像头停止失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('停止摄像头错误:', error);
            showAlert('停止摄像头时发生错误', 'error');
        });
}

function startVideoStream() {
    const videoElement = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    
    if (!videoElement || !canvas) return;
    
    // 从服务器获取帧（支持测试模式）
    updateFrameFromServer();
    
    // 同时尝试浏览器原生摄像头用于本地预览（可选）
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function(stream) {
                // 如果浏览器摄像头可用，使用浏览器摄像头
                videoElement.srcObject = stream;
                videoElement.play();
            })
            .catch(function(error) {
                console.log('浏览器摄像头不可用，使用服务器帧:', error.message);
                // 浏览器摄像头不可用时，使用服务器帧
            });
    }
}

function updateFrameFromServer() {
    const videoElement = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    
    if (!videoElement || !canvas) return;
    
    const context = canvas.getContext('2d');
    
    // 从服务器获取帧
    fetch('/api/camera/frame/')
        .then(response => {
            if (!response.ok) throw new Error('获取帧失败');
            return response.json();
        })
        .then(data => {
            if (data.frame) {
                const img = new Image();
                img.onload = function() {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    context.drawImage(img, 0, 0);
                    
                    // 继续获取下一帧
                    if (isCameraActive()) {
                        setTimeout(updateFrameFromServer, 100);
                    }
                };
                img.src = 'data:image/jpeg;base64,' + data.frame;
            } else {
                // 没有帧，继续尝试
                if (isCameraActive()) {
                    setTimeout(updateFrameFromServer, 500);
                }
            }
        })
        .catch(error => {
            console.log('获取帧错误:', error.message);
            if (isCameraActive()) {
                setTimeout(updateFrameFromServer, 500);
            }
        });
}

function isCameraActive() {
    const cameraStatus = document.getElementById('camera-status');
    if (cameraStatus && cameraStatus.textContent === '运行中') {
        return true;
    }
    return false;
}

function captureVideoFrame() {
    // 这个函数现在主要用于向后兼容
    // 主要的帧获取逻辑已移到 updateFrameFromServer()
    updateFrameFromServer();
}

function stopVideoStream() {
    const videoElement = document.getElementById('camera-video');
    
    if (videoElement && videoElement.srcObject) {
        const tracks = videoElement.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoElement.srcObject = null;
    }
}

function updateCameraStatus(status) {
    const cameraStatus = document.getElementById('camera-status');
    if (cameraStatus) {
        if (status === 'active') {
            cameraStatus.className = 'badge bg-success';
            cameraStatus.textContent = '运行中';
        } else {
            cameraStatus.className = 'badge bg-secondary';
            cameraStatus.textContent = '已停止';
        }
    }
}

function checkCameraStatus() {
    fetch('/api/products/camera/status/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateCameraStatus(data.data.status);
            }
        })
        .catch(error => {
            console.error('检查摄像头状态错误:', error);
        });
}

// 自动识别流程控制
function initAutoFlowControls() {
    const startAutoFlowBtn = document.getElementById('start-auto-flow-btn');
    const stopAutoFlowBtn = document.getElementById('stop-auto-flow-btn');
    
    if (startAutoFlowBtn) {
        startAutoFlowBtn.addEventListener('click', startAutoFlow);
    }
    
    if (stopAutoFlowBtn) {
        stopAutoFlowBtn.addEventListener('click', stopAutoFlow);
    }
    
    // 检查自动流程状态
    checkAutoFlowStatus();
}

function startAutoFlow() {
    fetch('/api/recognition/start-auto-flow/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateAutoFlowStatus(true);
                showAlert('自动识别流程已启动', 'success');
            } else {
                showAlert('启动自动识别流程失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('启动自动识别流程错误:', error);
            showAlert('启动自动识别流程时发生错误', 'error');
        });
}

function stopAutoFlow() {
    fetch('/api/recognition/stop-auto-flow/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateAutoFlowStatus(false);
                showAlert('自动识别流程已停止', 'success');
            } else {
                showAlert('停止自动识别流程失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('停止自动识别流程错误:', error);
            showAlert('停止自动识别流程时发生错误', 'error');
        });
}

function updateAutoFlowStatus(active) {
    const autoFlowStatus = document.getElementById('auto-flow-status');
    const startBtn = document.getElementById('start-auto-flow-btn');
    const stopBtn = document.getElementById('stop-auto-flow-btn');
    
    if (autoFlowStatus) {
        if (active) {
            autoFlowStatus.className = 'badge bg-success';
            autoFlowStatus.textContent = '运行中';
        } else {
            autoFlowStatus.className = 'badge bg-secondary';
            autoFlowStatus.textContent = '已停止';
        }
    }
    
    if (startBtn) {
        startBtn.disabled = active;
    }
    
    if (stopBtn) {
        stopBtn.disabled = !active;
    }
}

function checkAutoFlowStatus() {
    fetch('/api/products/recognition/auto-flow-status/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateAutoFlowStatus(data.data.active);
            }
        })
        .catch(error => {
            console.error('检查自动流程状态错误:', error);
        });
}

function getRecognitionStatus() {
    fetch('/api/products/recognition/status/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 更新各种状态
                if (data.data.camera_status) {
                    updateCameraStatus(data.data.camera_status);
                }
                if (data.data.auto_flow_status !== undefined) {
                    updateAutoFlowStatus(data.data.auto_flow_status);
                }
            }
        })
        .catch(error => {
            console.error('获取识别状态错误:', error);
        });
}

// 识别结果处理
function initRecognitionResults() {
    // 初始化结果展示区域
    displayRecognitionResults([]);
}

function handleRecognitionResult(result) {
    console.log('识别结果:', result);
    
    // 添加到结果历史
    addRecognitionResult(result);
    
    // 更新实时显示
    updateRealTimeDisplay(result);
}

function addRecognitionResult(result) {
    const resultsContainer = document.getElementById('recognition-results');
    if (!resultsContainer) return;
    
    const resultElement = document.createElement('div');
    resultElement.className = 'recognition-result';
    
    const timestamp = new Date().toLocaleTimeString();
    resultElement.innerHTML = `
        <div class="result-header">
            <span class="badge bg-primary">${result.class_name}</span>
            <span class="confidence">置信度: ${(result.confidence * 100).toFixed(2)}%</span>
            <small class="text-muted">${timestamp}</small>
        </div>
        ${result.bounding_box ? `
            <div class="bbox-info">
                位置: [${result.bounding_box.x}, ${result.bounding_box.y}, ${result.bounding_box.width}, ${result.bounding_box.height}]
            </div>
        ` : ''}
    `;
    
    resultsContainer.insertBefore(resultElement, resultsContainer.firstChild);
    
    // 限制显示数量
    while (resultsContainer.children.length > 10) {
        resultsContainer.removeChild(resultsContainer.lastChild);
    }
}

function updateRealTimeDisplay(result) {
    // 更新实时显示区域
    const currentResult = document.getElementById('current-result');
    if (currentResult) {
        currentResult.innerHTML = `
            <div class="current-detection">
                <h5>当前检测</h5>
                <div class="detection-info">
                    <span class="badge bg-success">${result.class_name}</span>
                    <span class="confidence">${(result.confidence * 100).toFixed(2)}%</span>
                </div>
                ${result.bounding_box ? `<div class="bbox-display">[${result.bounding_box.x}, ${result.bounding_box.y}]</div>` : ''}
            </div>
        `;
    }
}

function displayRecognitionResults(results) {
    const resultsContainer = document.getElementById('recognition-results');
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = '';
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted">暂无识别结果</p>';
        return;
    }
    
    results.forEach(result => {
        addRecognitionResult(result);
    });
}

// 性能监控
function initPerformanceMonitor() {
    // 初始化性能监控显示
    updatePerformanceMetrics({});
}

function updatePerformanceMetrics(metrics) {
    const metricsContainer = document.getElementById('performance-metrics');
    if (!metricsContainer) return;
    
    const metricsHtml = `
        <div class="performance-item">
            <label>推理时间:</label>
            <span>${metrics.inference_time || 0}ms</span>
        </div>
        <div class="performance-item">
            <label>FPS:</label>
            <span>${metrics.fps || 0}</span>
        </div>
        <div class="performance-item">
            <label>内存使用:</label>
            <span>${metrics.memory_usage || 0}MB</span>
        </div>
        <div class="performance-item">
            <label>GPU使用率:</label>
            <span>${metrics.gpu_usage || 0}%</span>
        </div>
    `;
    
    metricsContainer.innerHTML = metricsHtml;
}

function getPerformanceMetrics() {
    fetch('/api/products/recognition/performance/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updatePerformanceMetrics(data.data);
            }
        })
        .catch(error => {
            console.error('获取性能指标错误:', error);
        });
}

// 设置面板
function initSettingsPanel() {
    loadSettings();
}

function loadSettings() {
    fetch('/api/products/recognition/settings/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                populateSettingsForm(data.data);
            }
        })
        .catch(error => {
            console.error('加载设置错误:', error);
        });
}

function populateSettingsForm(settings) {
    // 填充设置表单
    Object.keys(settings).forEach(key => {
        const input = document.getElementById(`setting-${key}`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = settings[key];
            } else {
                input.value = settings[key];
            }
        }
    });
}

function saveSettings() {
    const settings = {};
    
    // 收集表单数据
    const inputs = document.querySelectorAll('[id^="setting-"]');
    inputs.forEach(input => {
        const key = input.id.replace('setting-', '');
        if (input.type === 'checkbox') {
            settings[key] = input.checked;
        } else {
            settings[key] = input.value;
        }
    });
    
    fetch('/api/products/recognition/settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('设置保存成功', 'success');
        } else {
            showAlert('设置保存失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('保存设置错误:', error);
        showAlert('保存设置时发生错误', 'error');
    });
}

// 工具函数
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertElement);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (alertElement.parentNode) {
            alertElement.parentNode.removeChild(alertElement);
        }
    }, 3000);
}

function updateOrderStats(data) {
    // 更新订单统计显示
    console.log('订单统计更新:', data);
}

function updateInventoryStats(data) {
    // 更新库存统计显示
    console.log('库存统计更新:', data);
}

// 页面离开时清理资源
window.addEventListener('beforeunload', function() {
    if (recognitionSocket) {
        recognitionSocket.close();
    }
});