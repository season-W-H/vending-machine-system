# -*- coding: utf-8 -*-
"""
数据集管理模块

该模块负责管理训练数据集，包括数据加载、预处理和增强功能。
支持训练集、验证集和测试集的管理。
"""

import os
import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from sklearn.model_selection import train_test_split
import json
from datetime import datetime


class DatasetManager:
    """
    数据集管理器类，负责数据集的加载、预处理和管理
    """
    
    def __init__(self, dataset_path: str = "d:\\SmartUVM_Datasets\\UVM_Datasets\\divide\\divide"):
        """
        初始化数据集管理器
        
        Args:
            dataset_path: 数据集根目录路径
        """
        self.dataset_path = dataset_path
        self.train_path = os.path.join(dataset_path, "train")
        self.val_path = os.path.join(dataset_path, "val")
        self.test_path = os.path.join(dataset_path, "test")
        
        # 商品类别映射（基于实际数据集文件夹结构）
        self.class_mapping = {
            'bss': {'name': '百事可乐', 'price': 3.5},
            'fd': {'name': '芬达', 'price': 3.0}, 
            'jdb': {'name': '加多宝', 'price': 4.0},
            'ksfh': {'name': '康师傅红烧牛肉面', 'price': 5.5},
            'llds': {'name': '乐事薯片', 'price': 6.0},
            'md': {'name': '脉动', 'price': 4.5},
            'mzy': {'name': '美汁源', 'price': 3.5},
            'tycl': {'name': '统一老坛酸菜面', 'price': 5.0},
            'tyyc': {'name': '统一鲜橙多', 'price': 3.0},
            'yykx': {'name': '怡宝矿泉水', 'price': 2.0}
        }
        
        # 自动发现数据集中的类别
        self._discover_classes()
        
        self.class_names = list(self.class_mapping.keys())
        self.num_classes = len(self.class_names)
        
        # 数据集统计信息
        self.dataset_stats = {}
        
        # 验证数据集结构
        self._validate_dataset()
    
    def _discover_classes(self):
        """自动发现数据集中的类别"""
        if not os.path.exists(self.train_path):
            print(f"训练数据集路径不存在: {self.train_path}")
            return
        
        # 扫描训练文件夹中的所有子目录作为类别
        discovered_classes = []
        for item in os.listdir(self.train_path):
            class_path = os.path.join(self.train_path, item)
            if os.path.isdir(class_path):
                discovered_classes.append(item)
        
        # 更新类别映射，保留已知的，添加新发现的
        for cls in discovered_classes:
            if cls not in self.class_mapping:
                self.class_mapping[cls] = {
                    'name': cls.upper(),  # 默认名称
                    'price': 3.0  # 默认价格
                }
                print(f"发现新类别: {cls}")
    
    def _validate_dataset(self):
        """验证数据集结构"""
        required_paths = [self.train_path, self.val_path, self.test_path]
        
        for path in required_paths:
            if not os.path.exists(path):
                print(f"警告: 数据集路径不存在 - {path}")
                continue
            
            # 检查每个类别文件夹是否存在
            for class_name in self.class_names:
                class_path = os.path.join(path, class_name)
                if not os.path.exists(class_path):
                    print(f"警告: 类别文件夹不存在 - {class_path}")
                else:
                    # 统计该类别的图片数量
                    image_files = [f for f in os.listdir(class_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    if len(image_files) == 0:
                        print(f"警告: 类别 {class_name} 在 {os.path.basename(path)} 中没有图片")
    
    def get_dataset_info(self) -> Dict:
        """
        获取数据集详细信息
        
        Returns:
            Dict: 数据集信息
        """
        info = {
            'dataset_path': self.dataset_path,
            'total_classes': self.num_classes,
            'class_mapping': self.class_mapping,
            'class_names': self.class_names,
            'statistics': self.get_dataset_statistics(),
            'is_valid': self._is_dataset_valid(),
            'last_updated': datetime.now().isoformat()
        }
        return info
    
    def _is_dataset_valid(self) -> bool:
        """检查数据集是否有效"""
        if not os.path.exists(self.dataset_path):
            return False
        
        # 检查至少有一个子集存在
        for subset_path in [self.train_path, self.val_path, self.test_path]:
            if os.path.exists(subset_path):
                # 检查是否有类别文件夹
                for class_name in self.class_names:
                    class_path = os.path.join(subset_path, class_name)
                    if os.path.exists(class_path):
                        # 检查是否有图片
                        image_files = [f for f in os.listdir(class_path) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                        if len(image_files) > 0:
                            return True
        return False
        
    def load_dataset(self, subset: str = 'train') -> Tuple[List[np.ndarray], List[int], List[str]]:
        """
        加载数据集
        
        Args:
            subset: 数据集子集 ('train', 'val', 'test')
            
        Returns:
            Tuple[List[np.ndarray], List[int], List[str]]: (图像数据, 标签, 文件路径)
        """
        if subset not in ['train', 'val', 'test']:
            raise ValueError("subset 必须是 'train', 'val', 或 'test'")
        
        subset_path = getattr(self, f"{subset}_path")
        images = []
        labels = []
        file_paths = []
        
        print(f"正在加载 {subset} 数据集...")
        
        for class_idx, class_name in enumerate(self.class_names):
            class_path = os.path.join(subset_path, class_name)
            
            if not os.path.exists(class_path):
                print(f"警告: 类别文件夹 {class_path} 不存在")
                continue
                
            class_files = [f for f in os.listdir(class_path) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            for file_name in class_files:
                file_path = os.path.join(class_path, file_name)
                
                try:
                    # 读取图像
                    image = cv2.imread(file_path)
                    if image is not None:
                        # 调整图像大小
                        image = cv2.resize(image, (224, 224))
                        images.append(image)
                        labels.append(class_idx)
                        file_paths.append(file_path)
                except Exception as e:
                    print(f"加载图像失败 {file_path}: {e}")
        
        print(f"成功加载 {len(images)} 张 {subset} 图像")
        return images, labels, file_paths
    
    def preprocess_image(self, image: np.ndarray, augment: bool = False) -> np.ndarray:
        """
        图像预处理
        
        Args:
            image: 输入图像
            augment: 是否进行数据增强
            
        Returns:
            np.ndarray: 预处理后的图像
        """
        # 转换为RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 归一化到[0,1]
        image = image.astype(np.float32) / 255.0
        
        if augment:
            # 数据增强
            if np.random.random() > 0.5:
                # 随机水平翻转
                image = cv2.flip(image, 1)
            
            if np.random.random() > 0.5:
                # 随机旋转
                angle = np.random.uniform(-15, 15)
                h, w = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                image = cv2.warpAffine(image, M, (w, h))
            
            if np.random.random() > 0.5:
                # 随机亮度调整
                brightness = np.random.uniform(0.8, 1.2)
                image = np.clip(image * brightness, 0, 1)
        
        return image
    
    def get_class_weights(self) -> Dict[int, float]:
        """
        计算类别权重，用于处理类别不平衡问题
        
        Returns:
            Dict[int, float]: 类别权重字典
        """
        _, labels, _ = self.load_dataset('train')
        
        # 统计每个类别的样本数量
        class_counts = {}
        for label in labels:
            class_counts[label] = class_counts.get(label, 0) + 1
        
        # 计算权重（样本数量越少，权重越大）
        total_samples = len(labels)
        class_weights = {}
        for class_idx in range(self.num_classes):
            count = class_counts.get(class_idx, 1)
            weight = total_samples / (self.num_classes * count)
            class_weights[class_idx] = weight
        
        return class_weights
    
    def get_dataset_statistics(self) -> Dict:
        """
        获取数据集统计信息
        
        Returns:
            Dict: 数据集统计信息
        """
        if self.dataset_stats:
            return self.dataset_stats
        
        stats = {}
        
        for subset in ['train', 'val', 'test']:
            _, labels, _ = self.load_dataset(subset)
            
            # 统计每个类别的样本数量
            class_counts = {}
            for label in labels:
                class_name = self.class_names[label]
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            stats[subset] = {
                'total_samples': len(labels),
                'class_counts': class_counts,
                'class_distribution': {k: v/len(labels) for k, v in class_counts.items()}
            }
        
        self.dataset_stats = stats
        return stats
    
    def create_data_generator(self, subset: str = 'train', batch_size: int = 32, 
                            augment: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """
        创建数据生成器
        
        Args:
            subset: 数据集子集
            batch_size: 批次大小
            augment: 是否进行数据增强
            
        Yields:
            Tuple[np.ndarray, np.ndarray]: 批次数据 (图像, 标签)
        """
        images, labels, _ = self.load_dataset(subset)
        
        num_samples = len(images)
        indices = np.arange(num_samples)
        
        while True:
            # 打乱索引
            np.random.shuffle(indices)
            
            for start_idx in range(0, num_samples, batch_size):
                end_idx = min(start_idx + batch_size, num_samples)
                batch_indices = indices[start_idx:end_idx]
                
                batch_images = []
                batch_labels = []
                
                for idx in batch_indices:
                    # 预处理图像
                    processed_image = self.preprocess_image(images[idx], augment)
                    batch_images.append(processed_image)
                    batch_labels.append(labels[idx])
                
                yield np.array(batch_images), np.array(batch_labels)
    
    def save_dataset_info(self, output_path: str = "dataset_info.json"):
        """
        保存数据集信息到JSON文件
        
        Args:
            output_path: 输出文件路径
        """
        stats = self.get_dataset_statistics()
        
        dataset_info = {
            'dataset_path': self.dataset_path,
            'class_mapping': self.class_mapping,
            'num_classes': self.num_classes,
            'statistics': stats,
            'created_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_info, f, ensure_ascii=False, indent=2)
        
        print(f"数据集信息已保存到 {output_path}")
    
    def visualize_samples(self, subset: str = 'train', num_samples: int = 5):
        """
        可视化数据集样本
        
        Args:
            subset: 数据集子集
            num_samples: 每个类别显示的样本数量
        """
        import matplotlib.pyplot as plt
        
        images, labels, _ = self.load_dataset(subset)
        
        plt.figure(figsize=(15, 10))
        
        for class_idx in range(min(self.num_classes, 10)):  # 最多显示10个类别
            # 找到该类别的所有样本
            class_indices = [i for i, label in enumerate(labels) if label == class_idx]
            
            for i in range(min(num_samples, len(class_indices))):
                idx = class_indices[i]
                
                plt.subplot(self.num_classes, num_samples, 
                           class_idx * num_samples + i + 1)
                
                plt.imshow(cv2.cvtColor(images[idx], cv2.COLOR_BGR2RGB))
                plt.title(f"{self.class_names[class_idx]}")
                plt.axis('off')
        
        plt.tight_layout()
        plt.show()


# 全局数据集管理器实例
dataset_manager = DatasetManager()