# -*- coding: utf-8 -*-
"""
改进的深度学习物体识别算法

该模块实现了基于深度学习的物体识别算法，支持训练、评估和推理。
使用CNN架构进行商品识别，包含模型训练、性能监控和优化功能。
"""

import os
import cv2
import numpy as np
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import threading
import time

# 深度学习框架
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers, callbacks
    from sklearn.metrics import classification_report, confusion_matrix
    TF_AVAILABLE = True
except ImportError:
    print("TensorFlow未安装，将使用模拟识别功能")
    TF_AVAILABLE = False

from .dataset_manager import DatasetManager


class DeepLearningRecognizer:
    """
    深度学习物体识别器
    """
    
    def __init__(self, model_path: str = "models/product_recognition.h5"):
        """
        初始化识别器
        
        Args:
            model_path: 模型保存路径
        """
        self.model_path = model_path
        self.model = None
        self.dataset_manager = DatasetManager()
        
        # 性能监控数据
        self.performance_metrics = {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'loss': 0.0,
            'confusion_matrix': None,
            'classification_report': None,
            'training_history': [],
            'last_updated': None
        }
        
        # 识别统计
        self.recognition_stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_confidence': 0.0,
            'class_counts': {}
        }
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 尝试加载已训练的模型
        self._load_model()
    
    def _create_model(self) -> keras.Model:
        """
        创建改进的CNN模型架构
        
        Returns:
            keras.Model: 创建的模型
        """
        if not TF_AVAILABLE:
            return None
        
        # 使用更先进的模型架构
        inputs = layers.Input(shape=(224, 224, 3))
        
        # 数据增强层
        x = layers.RandomFlip('horizontal')(inputs)
        x = layers.RandomRotation(0.1)(x)
        x = layers.RandomZoom(0.1)(x)
        x = layers.RandomContrast(0.1)(x)
        
        # 第一个卷积块 - 更深的特征提取
        x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Dropout(0.25)(x)
        
        # 第二个卷积块
        x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Dropout(0.25)(x)
        
        # 第三个卷积块
        x = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Dropout(0.25)(x)
        
        # 第四个卷积块
        x = layers.Conv2D(512, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(512, (3, 3), activation='relu', padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Dropout(0.25)(x)
        
        # 全连接层
        x = layers.Flatten()(x)
        x = layers.Dense(512, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.5)(x)
        x = layers.Dense(256, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.5)(x)
        
        # 输出层
        outputs = layers.Dense(self.dataset_manager.num_classes, activation='softmax')(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        
        # 使用学习率调度
        optimizer = optimizers.Adam(learning_rate=0.001)
        
        model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        return model
    
    def _load_model(self):
        """加载已训练的模型"""
        if not TF_AVAILABLE:
            print("TensorFlow不可用，无法加载模型")
            return
        
        try:
            if os.path.exists(self.model_path):
                self.model = keras.models.load_model(self.model_path)
                print(f"成功加载模型: {self.model_path}")
                
                # 检查模型输出层类别数量是否与当前数据集匹配
                if self.model.output_shape[-1] != self.dataset_manager.num_classes:
                    print(f"警告: 模型输出层类别数量({self.model.output_shape[-1]})与当前数据集类别数量({self.dataset_manager.num_classes})不匹配")
                    print("正在重新创建模型...")
                    self.model = self._create_model()
                
                self._load_performance_metrics()
            else:
                print("未找到预训练模型，将创建新模型")
                self.model = self._create_model()
        except Exception as e:
            print(f"加载模型失败: {e}")
            self.model = self._create_model()
    
    def train(self, epochs: int = 50, batch_size: int = 32, 
              save_best: bool = True) -> Dict:
        """
        训练模型
        
        Args:
            epochs: 训练轮数
            batch_size: 批次大小
            save_best: 是否保存最佳模型
            
        Returns:
            Dict: 训练历史和性能指标
        """
        if not TF_AVAILABLE:
            print("TensorFlow不可用，无法训练模型")
            return {}
        
        print("开始训练模型...")
        
        # 创建数据生成器
        train_generator = self.dataset_manager.create_data_generator(
            'train', batch_size, augment=True)
        val_generator = self.dataset_manager.create_data_generator(
            'val', batch_size, augment=False)
        
        # 计算训练和验证步数
        train_stats = self.dataset_manager.get_dataset_statistics()
        steps_per_epoch = train_stats['train']['total_samples'] // batch_size
        validation_steps = train_stats['val']['total_samples'] // batch_size
        
        # 设置回调函数
        callbacks_list = []
        if save_best:
            # 确保模型目录存在
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            callbacks_list.extend([
                callbacks.ModelCheckpoint(
                    self.model_path,
                    monitor='val_accuracy',
                    save_best_only=True,
                    verbose=1
                ),
                callbacks.EarlyStopping(
                    monitor='val_accuracy',
                    patience=10,
                    restore_best_weights=True,
                    verbose=1
                ),
                callbacks.ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.2,
                    patience=5,
                    min_lr=1e-7,
                    verbose=1
                )
            ])
        
        # 训练模型
        history = self.model.fit(
            train_generator,
            steps_per_epoch=steps_per_epoch,
            epochs=epochs,
            validation_data=val_generator,
            validation_steps=validation_steps,
            callbacks=callbacks_list,
            verbose=1
        )
        
        # 评估模型
        self._evaluate_model()
        
        # 保存性能指标
        self._save_performance_metrics()
        
        return {
            'history': history.history,
            'performance_metrics': self.performance_metrics
        }
    
    def _evaluate_model(self):
        """评估模型性能"""
        if not TF_AVAILABLE or self.model is None:
            return
        
        print("正在评估模型性能...")
        
        # 加载测试数据
        test_images, test_labels, _ = self.dataset_manager.load_dataset('test')
        
        # 预处理测试图像
        test_images_processed = np.array([
            self.dataset_manager.preprocess_image(img, augment=False) 
            for img in test_images
        ])
        
        # 预测
        predictions = self.model.predict(test_images_processed)
        predicted_labels = np.argmax(predictions, axis=1)
        
        # 计算性能指标
        self.performance_metrics['classification_report'] = classification_report(
            test_labels, predicted_labels, 
            target_names=self.dataset_manager.class_names,
            output_dict=True
        )
        
        self.performance_metrics['confusion_matrix'] = confusion_matrix(
            test_labels, predicted_labels).tolist()
        
        # 计算总体指标
        report = self.performance_metrics['classification_report']
        self.performance_metrics['accuracy'] = report['accuracy']
        self.performance_metrics['precision'] = report['macro avg']['precision']
        self.performance_metrics['recall'] = report['macro avg']['recall']
        self.performance_metrics['f1_score'] = report['macro avg']['f1-score']
        
        # 评估损失
        loss, accuracy = self.model.evaluate(test_images_processed, test_labels, verbose=0)
        self.performance_metrics['loss'] = loss
        
        self.performance_metrics['last_updated'] = datetime.now().isoformat()
        
        print(f"模型评估完成 - 准确率: {self.performance_metrics['accuracy']:.4f}")
    
    def recognize_objects(self, image: np.ndarray) -> List[Dict]:
        """
        识别图像中的物体
        
        Args:
            image: 输入图像
            
        Returns:
            List[Dict]: 识别结果列表
        """
        with self.lock:
            self.recognition_stats['total_recognitions'] += 1
        
        try:
            if not TF_AVAILABLE or self.model is None:
                # 模拟识别结果
                return self._simulate_recognition(image)
            
            # 预处理图像
            processed_image = self.dataset_manager.preprocess_image(image, augment=False)
            processed_image = np.expand_dims(processed_image, axis=0)
            
            # 预测
            predictions = self.model.predict(processed_image, verbose=0)
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            
            # 构建结果
            class_name = self.dataset_manager.class_names[predicted_class_idx]
            class_display_name = self.dataset_manager.class_mapping[class_name]
            
            # 更新统计信息
            with self.lock:
                self.recognition_stats['successful_recognitions'] += 1
                self.recognition_stats['average_confidence'] = (
                    (self.recognition_stats['average_confidence'] * 
                     (self.recognition_stats['successful_recognitions'] - 1) + confidence) /
                    self.recognition_stats['successful_recognitions']
                )
                
                if class_name not in self.recognition_stats['class_counts']:
                    self.recognition_stats['class_counts'][class_name] = 0
                self.recognition_stats['class_counts'][class_name] += 1
            
            return [{
                'class_id': predicted_class_idx,
                'class_name': class_name,
                'display_name': class_display_name,
                'confidence': confidence,
                'bbox': [0, 0, image.shape[1], image.shape[0]],  # 全图作为边界框
                'timestamp': datetime.now().isoformat()
            }]
            
        except Exception as e:
            print(f"识别失败: {e}")
            with self.lock:
                self.recognition_stats['failed_recognitions'] += 1
            return []
    
    def _simulate_recognition(self, image: np.ndarray) -> List[Dict]:
        """
        模拟识别结果（当TensorFlow不可用时）
        
        Args:
            image: 输入图像
            
        Returns:
            List[Dict]: 模拟的识别结果
        """
        # 当TensorFlow不可用时，返回空结果，避免随机识别
        # 这样可以确保在没有实际检测时不会显示假的识别结果
        print("TensorFlow不可用，返回空识别结果")
        
        # 更新统计信息
        with self.lock:
            self.recognition_stats['failed_recognitions'] += 1
        
        return []
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表
            
        Returns:
            np.ndarray: 绘制了检测结果的图像
        """
        result_image = image.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            class_name = detection['display_name']
            confidence = detection['confidence']
            
            # 绘制边界框
            x, y, w, h = map(int, bbox)
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # 绘制标签背景
            cv2.rectangle(result_image, 
                         (x, y - label_size[1] - 10),
                         (x + label_size[0], y),
                         (0, 255, 0), -1)
            
            # 绘制标签文字
            cv2.putText(result_image, label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        return result_image
    
    def get_performance_metrics(self) -> Dict:
        """
        获取性能指标
        
        Returns:
            Dict: 性能指标
        """
        with self.lock:
            return {
                'model_performance': self.performance_metrics.copy(),
                'recognition_stats': self.recognition_stats.copy()
            }
    
    def get_recognition_stats(self) -> Dict:
        """
        获取识别统计信息
        
        Returns:
            Dict: 识别统计信息
        """
        with self.lock:
            return self.recognition_stats.copy()
    
    def _save_performance_metrics(self):
        """保存性能指标到文件"""
        metrics_path = self.model_path.replace('.h5', '_metrics.json')
        
        metrics_data = {
            'performance_metrics': self.performance_metrics,
            'recognition_stats': self.recognition_stats,
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(metrics_path, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)
            print(f"性能指标已保存到 {metrics_path}")
        except Exception as e:
            print(f"保存性能指标失败: {e}")
    
    def _load_performance_metrics(self):
        """从文件加载性能指标"""
        metrics_path = self.model_path.replace('.h5', '_metrics.json')
        
        try:
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                
                self.performance_metrics = metrics_data.get('performance_metrics', {})
                self.recognition_stats = metrics_data.get('recognition_stats', {})
                print(f"成功加载性能指标: {metrics_path}")
        except Exception as e:
            print(f"加载性能指标失败: {e}")
    
    def reset_stats(self):
        """重置识别统计信息"""
        with self.lock:
            self.recognition_stats = {
                'total_recognitions': 0,
                'successful_recognitions': 0,
                'failed_recognitions': 0,
                'average_confidence': 0.0,
                'class_counts': {}
            }
    
    def optimize_hyperparameters(self, param_grid: Dict = None) -> Dict:
        """
        超参数优化
        
        Args:
            param_grid: 参数网格，如果为None则使用默认网格
            
        Returns:
            Dict: 优化结果
        """
        if param_grid is None:
            param_grid = {
                'learning_rate': [0.001, 0.01, 0.0001],
                'batch_size': [16, 32, 64],
                'dropout_rate': [0.3, 0.5, 0.7],
                'epochs': [30, 50, 80]
            }
        
        best_params = None
        best_score = 0.0
        optimization_results = []
        
        print("开始超参数优化...")
        
        # 网格搜索
        for lr in param_grid.get('learning_rate', [0.001]):
            for batch_size in param_grid.get('batch_size', [32]):
                for dropout_rate in param_grid.get('dropout_rate', [0.5]):
                    for epochs in param_grid.get('epochs', [50]):
                        
                        params = {
                            'learning_rate': lr,
                            'batch_size': batch_size,
                            'dropout_rate': dropout_rate,
                            'epochs': epochs
                        }
                        
                        print(f"测试参数: {params}")
                        
                        # 创建新模型
                        self.model = self._create_model()
                        
                        # 训练模型
                        try:
                            history = self.train(
                                epochs=epochs,
                                batch_size=batch_size,
                                save_best=False
                            )
                            
                            # 获取最佳验证准确率
                            val_acc = max(history.get('val_accuracy', [0.0]))
                            
                            result = {
                                'params': params,
                                'val_accuracy': val_acc,
                                'history': history
                            }
                            
                            optimization_results.append(result)
                            
                            # 更新最佳参数
                            if val_acc > best_score:
                                best_score = val_acc
                                best_params = params
                                print(f"发现更好的参数组合! 准确率: {val_acc:.4f}")
                                
                        except Exception as e:
                            print(f"参数组合 {params} 训练失败: {e}")
                            continue
        
        # 保存优化结果
        optimization_summary = {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': optimization_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # 使用最佳参数创建最终模型
        if best_params:
            print(f"\n最佳参数: {best_params}")
            print(f"最佳准确率: {best_score:.4f}")
            
            # 用最佳参数重新训练模型
            self.model = self._create_model()
            self.train(
                epochs=best_params['epochs'],
                batch_size=best_params['batch_size'],
                save_best=True
            )
            
            # 保存优化结果
            results_path = os.path.join(
                os.path.dirname(self.model_path), 
                'hyperparameter_optimization.json'
            )
            os.makedirs(os.path.dirname(results_path), exist_ok=True)
            
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(optimization_summary, f, indent=2, ensure_ascii=False)
            
            print(f"优化结果已保存到: {results_path}")
        
        return optimization_summary
    
    def apply_data_augmentation(self, images: np.ndarray) -> np.ndarray:
        """
        应用数据增强
        
        Args:
            images: 输入图像数组
            
        Returns:
            np.ndarray: 增强后的图像
        """
        if not TF_AVAILABLE:
            print("TensorFlow不可用，无法应用数据增强")
            return images
        
        # 创建数据增强层
        data_augmentation = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.1),
            tf.keras.layers.RandomZoom(0.1),
            tf.keras.layers.RandomContrast(0.1),
        ])
        
        # 应用增强
        augmented_images = data_augmentation(images, training=True)
        
        return augmented_images.numpy()
    
    def implement_transfer_learning(self, base_model_name: str = 'MobileNetV2') -> bool:
        """
        实现迁移学习
        
        Args:
            base_model_name: 基础模型名称
            
        Returns:
            bool: 是否成功实现
        """
        if not TF_AVAILABLE:
            print("TensorFlow不可用，无法实现迁移学习")
            return False
        
        try:
            # 选择预训练模型
            if base_model_name == 'MobileNetV2':
                base_model = tf.keras.applications.MobileNetV2(
                    input_shape=(224, 224, 3),
                    include_top=False,
                    weights='imagenet'
                )
            elif base_model_name == 'ResNet50':
                base_model = tf.keras.applications.ResNet50(
                    input_shape=(224, 224, 3),
                    include_top=False,
                    weights='imagenet'
                )
            elif base_model_name == 'EfficientNetB0':
                base_model = tf.keras.applications.EfficientNetB0(
                    input_shape=(224, 224, 3),
                    include_top=False,
                    weights='imagenet'
                )
            else:
                print(f"不支持的模型: {base_model_name}")
                return False
            
            # 冻结基础模型层
            base_model.trainable = False
            
            # 构建新模型
            inputs = tf.keras.Input(shape=(224, 224, 3))
            
            # 预处理
            x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
            
            # 基础模型
            x = base_model(x, training=False)
            
            # 全局平均池化
            x = tf.keras.layers.GlobalAveragePooling2D()(x)
            
            # Dropout
            x = tf.keras.layers.Dropout(0.5)(x)
            
            # 输出层
            num_classes = len(self.dataset_manager.class_names) if self.dataset_manager else 4
            outputs = tf.keras.layers.Dense(num_classes, activation='softmax')(x)
            
            # 创建模型
            self.model = tf.keras.Model(inputs, outputs)
            
            # 编译模型
            self.model.compile(
                optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )
            
            print(f"成功实现基于 {base_model_name} 的迁移学习")
            
            # 保存模型架构
            model_architecture_path = os.path.join(
                os.path.dirname(self.model_path), 
                f'transfer_learning_{base_model_name.lower()}_architecture.json'
            )
            os.makedirs(os.path.dirname(model_architecture_path), exist_ok=True)
            
            with open(model_architecture_path, 'w') as f:
                f.write(self.model.to_json())
            
            return True
            
        except Exception as e:
            print(f"迁移学习实现失败: {e}")
            return False
    
    def fine_tune_model(self, unfreeze_layers: int = 10) -> bool:
        """
        微调迁移学习模型
        
        Args:
            unfreeze_layers: 解冻的层数
            
        Returns:
            bool: 是否成功微调
        """
        if not self.model:
            print("模型未初始化")
            return False
        
        if not TF_AVAILABLE:
            print("TensorFlow不可用，无法微调模型")
            return False
        
        try:
            # 找到基础模型层
            base_model = None
            for layer in self.model.layers:
                if hasattr(layer, 'layers') and len(layer.layers) > 100:
                    base_model = layer
                    break
            
            if not base_model:
                print("未找到基础模型，无法微调")
                return False
            
            # 解冻最后几层
            base_model.trainable = True
            
            # 冻结前面的层
            for layer in base_model.layers[:-unfreeze_layers]:
                layer.trainable = False
            
            # 重新编译模型，使用较低的学习率
            self.model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )
            
            print(f"成功设置微调，解冻了最后 {unfreeze_layers} 层")
            return True
            
        except Exception as e:
            print(f"微调设置失败: {e}")
            return False
    
    def get_model_summary(self) -> Dict:
        """
        获取模型摘要信息
        
        Returns:
            Dict: 模型摘要
        """
        if not self.model:
            return {"error": "模型未初始化"}
        
        try:
            # 计算模型参数
            total_params = self.model.count_params()
            trainable_params = sum(
                [tf.keras.backend.count_params(w) for w in self.model.trainable_weights]
            )
            
            # 获取层信息
            layer_info = []
            for i, layer in enumerate(self.model.layers):
                layer_info.append({
                    'index': i,
                    'name': layer.name,
                    'type': type(layer).__name__,
                    'output_shape': str(layer.output_shape) if hasattr(layer, 'output_shape') else None,
                    'trainable': layer.trainable if hasattr(layer, 'trainable') else None
                })
            
            summary = {
                'total_parameters': int(total_params),
                'trainable_parameters': int(trainable_params),
                'non_trainable_parameters': int(total_params - trainable_params),
                'input_shape': str(self.model.input_shape) if hasattr(self.model, 'input_shape') else None,
                'output_shape': str(self.model.output_shape) if hasattr(self.model, 'output_shape') else None,
                'layers': layer_info,
                'model_type': 'transfer_learning' if any(
                    hasattr(layer, 'layers') and len(layer.layers) > 100 
                    for layer in self.model.layers
                ) else 'custom_cnn'
            }
            
            return summary
            
        except Exception as e:
            return {"error": f"获取模型摘要失败: {e}"}
    
    def save_optimized_model(self, model_name: str = "optimized_model") -> str:
        """
        保存优化后的模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            str: 保存路径
        """
        if not self.model:
            raise ValueError("模型未初始化")
        
        # 创建保存目录
        save_dir = os.path.join(os.path.dirname(self.model_path), 'optimized')
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存模型
        model_path = os.path.join(save_dir, f"{model_name}.h5")
        self.model.save(model_path)
        
        # 保存模型摘要
        summary = self.get_model_summary()
        summary_path = os.path.join(save_dir, f"{model_name}_summary.json")
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"优化模型已保存到: {model_path}")
        print(f"模型摘要已保存到: {summary_path}")
        
        return model_path


# 全局识别器实例
deep_learning_recognizer = DeepLearningRecognizer()