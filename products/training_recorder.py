#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练记录管理器
记录每次模型训练的结果和过程
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingStatus(Enum):
    """训练状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TrainingMetrics:
    """训练指标数据类"""
    epoch: int
    train_loss: float
    train_accuracy: float
    val_loss: float
    val_accuracy: float
    val_precision: Optional[float] = None
    val_recall: Optional[float] = None
    val_f1_score: Optional[float] = None
    learning_rate: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class TrainingConfig:
    """训练配置数据类"""
    model_type: str  # yolov8, mask_rcnn, sam
    model_version: str
    dataset_path: str
    epochs: int
    batch_size: int
    learning_rate: float
    optimizer: str
    loss_function: str
    image_size: int
    augmentation_enabled: bool
    custom_params: Optional[Dict[str, Any]] = None

@dataclass
class TrainingResult:
    """训练结果数据类"""
    training_id: str
    status: TrainingStatus
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    # 配置信息
    config: TrainingConfig
    
    # 训练历史
    training_history: List[TrainingMetrics] = None
    
    # 最终指标
    final_train_loss: Optional[float] = None
    final_train_accuracy: Optional[float] = None
    final_val_loss: Optional[float] = None
    final_val_accuracy: Optional[float] = None
    final_val_precision: Optional[float] = None
    final_val_recall: Optional[float] = None
    final_val_f1_score: Optional[float] = None
    
    # 模型信息
    model_save_path: Optional[str] = None
    model_size_bytes: Optional[int] = None
    
    # 系统信息
    system_info: Optional[Dict[str, Any]] = None
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 备注
    notes: Optional[str] = None

    def __post_init__(self):
        if self.training_history is None:
            self.training_history = []

class TrainingRecorder:
    """训练记录管理器"""
    
    def __init__(self, records_dir: str = "training_records"):
        """
        初始化训练记录器
        
        Args:
            records_dir: 记录保存目录
        """
        self.records_dir = Path(records_dir)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.records_file = self.records_dir / "training_records.json"
        
        # 加载现有记录
        self.records: Dict[str, TrainingResult] = self._load_records()
        
        logger.info(f"✅ 训练记录器初始化完成，记录目录: {self.records_dir}")
        logger.info(f"📊 已加载 {len(self.records)} 条训练记录")
    
    def _load_records(self) -> Dict[str, TrainingResult]:
        """加载训练记录"""
        if self.records_file.exists():
            try:
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {k: self._dict_to_training_result(v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"❌ 加载训练记录失败: {e}")
        return {}
    
    def _save_records(self):
        """保存训练记录"""
        try:
            data = {k: self._training_result_to_dict(v) for k, v in self.records.items()}
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"✅ 训练记录已保存到 {self.records_file}")
        except Exception as e:
            logger.error(f"❌ 保存训练记录失败: {e}")
    
    def _dict_to_training_result(self, data: Dict) -> TrainingResult:
        """字典转换为TrainingResult对象"""
        # 转换配置
        config_data = data.pop('config', {})
        config = TrainingConfig(**config_data)
        
        # 转换训练历史
        history_data = data.pop('training_history', [])
        training_history = [TrainingMetrics(**m) for m in history_data]
        
        # 转换状态
        status = TrainingStatus(data.pop('status', 'pending'))
        
        return TrainingResult(
            config=config,
            training_history=training_history,
            status=status,
            **data
        )
    
    def _training_result_to_dict(self, result: TrainingResult) -> Dict:
        """TrainingResult对象转换为字典"""
        data = asdict(result)
        data['status'] = result.status.value
        data['config'] = asdict(result.config)
        data['training_history'] = [asdict(m) for m in result.training_history]
        return data
    
    def generate_training_id(self) -> str:
        """生成唯一训练ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"training_{timestamp}"
    
    def start_training(self, config: TrainingConfig) -> str:
        """
        开始训练，创建训练记录
        
        Args:
            config: 训练配置
            
        Returns:
            training_id: 训练ID
        """
        training_id = self.generate_training_id()
        
        result = TrainingResult(
            training_id=training_id,
            status=TrainingStatus.RUNNING,
            start_time=datetime.now().isoformat(),
            config=config
        )
        
        self.records[training_id] = result
        self._save_records()
        
        logger.info(f"🎬 训练已开始，ID: {training_id}")
        return training_id
    
    def add_epoch_metrics(self, training_id: str, metrics: TrainingMetrics):
        """
        添加训练轮次指标
        
        Args:
            training_id: 训练ID
            metrics: 训练指标
        """
        if training_id in self.records:
            self.records[training_id].training_history.append(metrics)
            self._save_records()
            logger.debug(f"📈 已添加第 {metrics.epoch} 轮指标，训练ID: {training_id}")
        else:
            logger.error(f"❌ 训练ID不存在: {training_id}")
    
    def complete_training(self, training_id: str, 
                         final_metrics: Dict[str, Any],
                         model_save_path: str = None,
                         notes: str = None):
        """
        完成训练
        
        Args:
            training_id: 训练ID
            final_metrics: 最终指标
            model_save_path: 模型保存路径
            notes: 备注
        """
        if training_id in self.records:
            result = self.records[training_id]
            result.status = TrainingStatus.COMPLETED
            result.end_time = datetime.now().isoformat()
            
            # 计算训练时长
            start_dt = datetime.fromisoformat(result.start_time)
            end_dt = datetime.fromisoformat(result.end_time)
            result.duration_seconds = (end_dt - start_dt).total_seconds()
            
            # 设置最终指标
            result.final_train_loss = final_metrics.get('train_loss')
            result.final_train_accuracy = final_metrics.get('train_accuracy')
            result.final_val_loss = final_metrics.get('val_loss')
            result.final_val_accuracy = final_metrics.get('val_accuracy')
            result.final_val_precision = final_metrics.get('val_precision')
            result.final_val_recall = final_metrics.get('val_recall')
            result.final_val_f1_score = final_metrics.get('val_f1_score')
            
            # 设置模型信息
            result.model_save_path = model_save_path
            if model_save_path and os.path.exists(model_save_path):
                result.model_size_bytes = os.path.getsize(model_save_path)
            
            # 设置备注
            result.notes = notes
            
            self._save_records()
            logger.info(f"✅ 训练完成，ID: {training_id}, 时长: {result.duration_seconds:.2f}秒")
        else:
            logger.error(f"❌ 训练ID不存在: {training_id}")
    
    def fail_training(self, training_id: str, error_message: str):
        """
        训练失败
        
        Args:
            training_id: 训练ID
            error_message: 错误信息
        """
        if training_id in self.records:
            result = self.records[training_id]
            result.status = TrainingStatus.FAILED
            result.end_time = datetime.now().isoformat()
            result.error_message = error_message
            
            # 计算训练时长
            start_dt = datetime.fromisoformat(result.start_time)
            end_dt = datetime.fromisoformat(result.end_time)
            result.duration_seconds = (end_dt - start_dt).total_seconds()
            
            self._save_records()
            logger.error(f"❌ 训练失败，ID: {training_id}, 错误: {error_message}")
        else:
            logger.error(f"❌ 训练ID不存在: {training_id}")
    
    def get_training_record(self, training_id: str) -> Optional[TrainingResult]:
        """
        获取训练记录
        
        Args:
            training_id: 训练ID
            
        Returns:
            TrainingResult或None
        """
        return self.records.get(training_id)
    
    def get_all_records(self) -> List[TrainingResult]:
        """获取所有训练记录"""
        return list(self.records.values())
    
    def get_records_by_status(self, status: TrainingStatus) -> List[TrainingResult]:
        """
        按状态获取训练记录
        
        Args:
            status: 训练状态
            
        Returns:
            训练记录列表
        """
        return [r for r in self.records.values() if r.status == status]
    
    def get_records_by_model_type(self, model_type: str) -> List[TrainingResult]:
        """
        按模型类型获取训练记录
        
        Args:
            model_type: 模型类型
            
        Returns:
            训练记录列表
        """
        return [r for r in self.records.values() 
                if r.config.model_type.lower() == model_type.lower()]
    
    def export_training_report(self, training_id: str, output_path: str) -> bool:
        """
        导出训练报告
        
        Args:
            training_id: 训练ID
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        record = self.get_training_record(training_id)
        if not record:
            logger.error(f"❌ 训练ID不存在: {training_id}")
            return False
        
        try:
            report = self._generate_report(record)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 训练报告已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 导出训练报告失败: {e}")
            return False
    
    def _generate_report(self, record: TrainingResult) -> Dict:
        """生成训练报告"""
        report = {
            "training_id": record.training_id,
            "status": record.status.value,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "duration_seconds": record.duration_seconds,
            "config": asdict(record.config),
            "final_metrics": {
                "train_loss": record.final_train_loss,
                "train_accuracy": record.final_train_accuracy,
                "val_loss": record.final_val_loss,
                "val_accuracy": record.final_val_accuracy,
                "val_precision": record.final_val_precision,
                "val_recall": record.final_val_recall,
                "val_f1_score": record.final_val_f1_score
            },
            "training_history": [asdict(m) for m in record.training_history],
            "model_info": {
                "save_path": record.model_save_path,
                "size_bytes": record.model_size_bytes
            },
            "notes": record.notes,
            "error_message": record.error_message
        }
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取训练统计信息
        
        Returns:
            统计信息字典
        """
        records = self.get_all_records()
        if not records:
            return {"total_records": 0}
        
        completed = [r for r in records if r.status == TrainingStatus.COMPLETED]
        failed = [r for r in records if r.status == TrainingStatus.FAILED]
        running = [r for r in records if r.status == TrainingStatus.RUNNING]
        
        stats = {
            "total_records": len(records),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "running_count": len(running),
            "success_rate": len(completed) / len(records) if records else 0
        }
        
        # 计算平均指标
        if completed:
            avg_train_acc = sum(r.final_train_accuracy or 0 for r in completed) / len(completed)
            avg_val_acc = sum(r.final_val_accuracy or 0 for r in completed) / len(completed)
            avg_duration = sum(r.duration_seconds or 0 for r in completed) / len(completed)
            
            stats.update({
                "average_train_accuracy": avg_train_acc,
                "average_val_accuracy": avg_val_acc,
                "average_duration_seconds": avg_duration
            })
        
        return stats


# 全局训练记录器实例
training_recorder = TrainingRecorder()


if __name__ == "__main__":
    # 示例使用
    recorder = TrainingRecorder()
    
    # 创建训练配置
    config = TrainingConfig(
        model_type="yolov8",
        model_version="v8.0.0",
        dataset_path="datasets/products",
        epochs=50,
        batch_size=16,
        learning_rate=0.001,
        optimizer="AdamW",
        loss_function="CIoU",
        image_size=640,
        augmentation_enabled=True
    )
    
    # 开始训练
    training_id = recorder.start_training(config)
    
    # 模拟训练过程
    for epoch in range(1, 6):
        metrics = TrainingMetrics(
            epoch=epoch,
            train_loss=0.5 / epoch,
            train_accuracy=0.8 + 0.02 * epoch,
            val_loss=0.6 / epoch,
            val_accuracy=0.78 + 0.015 * epoch
        )
        recorder.add_epoch_metrics(training_id, metrics)
        time.sleep(0.1)
    
    # 完成训练
    final_metrics = {
        "train_loss": 0.1,
        "train_accuracy": 0.9,
        "val_loss": 0.12,
        "val_accuracy": 0.88,
        "val_precision": 0.89,
        "val_recall": 0.87,
        "val_f1_score": 0.88
    }
    
    recorder.complete_training(
        training_id,
        final_metrics,
        model_save_path="models/best_model.pt",
        notes="测试训练记录功能"
    )
    
    # 获取统计信息
    stats = recorder.get_statistics()
    print("\n训练统计:")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    # 导出报告
    recorder.export_training_report(training_id, "training_report.json")
