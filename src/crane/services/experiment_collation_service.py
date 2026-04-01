"""實驗數據蒐集與彙總服務。

自動掃描 git 管理的目錄，蒐集實驗結果檔案（CSV、JSON、YAML）
並轉換為統一的結構化格式。
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MetricValue:
    """單一指標值"""

    metric_name: str
    value: float | str | int
    unit: str = ""
    source_file: str = ""
    timestamp: str = ""


@dataclass
class ExperimentDataset:
    """實驗數據集（來自單一檔案）"""

    name: str
    file_path: str
    file_type: str  # "csv" | "json" | "yaml"
    metrics: list[MetricValue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentCollation:
    """彙總的實驗數據"""

    total_files: int
    total_metrics: int
    datasets: list[ExperimentDataset] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    collated_at: str = ""
    git_tracked: bool = True


class ExperimentCollationService:
    """蒐集並整理 git 管理目錄中的實驗數據"""

    def __init__(self, project_root: str | Path = "."):
        self.project_root = Path(project_root)

    def discover_tracked_experiment_files(self) -> list[Path]:
        """發現 git 追蹤的實驗數據檔案（排除 .gitignore）"""
        # 支援的檔案格式
        patterns = {
            "*.csv": "csv",
            "*.json": "json",
            "*.jsonl": "jsonl",
            "*.yaml": "yaml",
            "*.yml": "yaml",
        }

        tracked_files = []

        for pattern, file_type in patterns.items():
            for file_path in self.project_root.rglob(pattern):
                # 排除虛擬環境、測試、隱藏目錄等
                if any(
                    part in file_path.parts
                    for part in [".venv", "__pycache__", ".git", "node_modules"]
                ):
                    continue

                # 排除 PDF（被 .gitignore 忽略）
                if file_path.suffix.lower() == ".pdf":
                    continue

                # 優先檢查是否為實驗數據而非配置/文檔
                if self._is_likely_experiment_file(file_path):
                    tracked_files.append(file_path)

        return sorted(tracked_files)

    def _is_likely_experiment_file(self, file_path: Path) -> bool:
        """啟發式判斷檔案是否為實驗數據"""
        stem = file_path.stem.lower()

        # 明確的實驗數據相關名稱
        exp_patterns = [
            "result",
            "experiment",
            "data",
            "metric",
            "output",
            "benchmark",
            "evaluation",
            "performance",
            "score",
            "baseline",
            "model",
            "accuracy",
            "loss",
            "sjr",
        ]

        if any(pattern in stem for pattern in exp_patterns):
            return True

        # 排除明確的配置/文檔檔案
        exclude_patterns = [
            "config",
            "setup",
            "template",
            "readme",
            "license",
            "changelog",
            "manifest",
            "requirements",
            "pyproject",
            "makefile",
            "dockerfile",
            "editorconfig",
        ]

        if any(pattern in stem for pattern in exclude_patterns):
            return False

        # 資料目錄中的檔案優先視為實驗數據
        if "data" in file_path.parts or "results" in file_path.parts:
            return True

        return False

    def parse_csv_file(self, csv_path: Path) -> ExperimentDataset:
        """解析 CSV 實驗結果檔案"""
        metrics = []
        metadata = {}

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                lower_fields = [fn.lower() for fn in fieldnames]

                # Detect "metric,value,unit" pivoted format:
                # one column names the metric, another holds the value
                metric_col = None
                value_col = None
                unit_col = None
                for fn, lf in zip(fieldnames, lower_fields):
                    if lf in ("metric", "metric_name"):
                        metric_col = fn
                    elif lf == "value":
                        value_col = fn
                    elif lf == "unit":
                        unit_col = fn

                pivoted = metric_col is not None and value_col is not None

                for row_idx, row in enumerate(reader):
                    if pivoted:
                        # Pivoted format: each row is one metric
                        name = row.get(metric_col, f"metric_{row_idx}")
                        raw_value = row.get(value_col, "")
                        raw_unit = row.get(unit_col, "") if unit_col else ""
                        try:
                            num_value = float(raw_value) if raw_value else 0
                            metrics.append(
                                MetricValue(
                                    metric_name=name,
                                    value=num_value,
                                    unit=raw_unit or "",
                                    source_file=csv_path.name,
                                    timestamp=row.get("timestamp", ""),
                                )
                            )
                        except (ValueError, TypeError):
                            pass
                    else:
                        # Wide format: each column is a metric
                        for key, value in row.items():
                            if key.lower() not in ["name", "id", "timestamp"]:
                                try:
                                    num_value = float(value) if value else 0
                                    metrics.append(
                                        MetricValue(
                                            metric_name=key,
                                            value=num_value,
                                            source_file=csv_path.name,
                                            timestamp=row.get("timestamp", ""),
                                        )
                                    )
                                except (ValueError, TypeError):
                                    if key not in metadata:
                                        metadata[key] = []
                                    if value and value not in metadata[key]:
                                        metadata[key].append(value)

        except Exception as e:
            print(f"❌ Error parsing CSV {csv_path}: {e}")

        return ExperimentDataset(
            name=csv_path.stem,
            file_path=str(csv_path.relative_to(self.project_root)),
            file_type="csv",
            metrics=metrics,
            metadata=metadata,
        )

    def parse_json_file(self, json_path: Path) -> ExperimentDataset:
        """解析 JSON 實驗結果檔案"""
        metrics = []
        metadata = {}

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            metrics.append(
                                MetricValue(
                                    metric_name=key,
                                    value=value,
                                    source_file=json_path.name,
                                )
                            )
                        else:
                            metadata[key] = value
                elif isinstance(data, list):
                    # 如果是列表，假設每個項目都是指標
                    for idx, item in enumerate(data):
                        if isinstance(item, dict):
                            for key, value in item.items():
                                if isinstance(value, (int, float)):
                                    metrics.append(
                                        MetricValue(
                                            metric_name=f"{key}[{idx}]",
                                            value=value,
                                            source_file=json_path.name,
                                        )
                                    )

        except Exception as e:
            print(f"❌ Error parsing JSON {json_path}: {e}")

        return ExperimentDataset(
            name=json_path.stem,
            file_path=str(json_path.relative_to(self.project_root)),
            file_type="json",
            metrics=metrics,
            metadata=metadata,
        )

    def parse_yaml_file(self, yaml_path: Path) -> ExperimentDataset:
        """解析 YAML 實驗結果檔案"""
        metrics = []
        metadata = {}

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            metrics.append(
                                MetricValue(
                                    metric_name=key,
                                    value=value,
                                    source_file=yaml_path.name,
                                )
                            )
                        else:
                            metadata[key] = value

        except Exception as e:
            print(f"❌ Error parsing YAML {yaml_path}: {e}")

        return ExperimentDataset(
            name=yaml_path.stem,
            file_path=str(yaml_path.relative_to(self.project_root)),
            file_type="yaml",
            metrics=metrics,
            metadata=metadata,
        )

    def collate_all(self) -> ExperimentCollation:
        """彙總所有實驗數據"""
        datasets = []
        all_metrics = []

        for file_path in self.discover_tracked_experiment_files():
            dataset = None

            if file_path.suffix.lower() == ".csv":
                dataset = self.parse_csv_file(file_path)
            elif file_path.suffix.lower() == ".json":
                dataset = self.parse_json_file(file_path)
            elif file_path.suffix.lower() in [".yaml", ".yml"]:
                dataset = self.parse_yaml_file(file_path)

            if dataset and dataset.metrics:
                datasets.append(dataset)
                all_metrics.extend(dataset.metrics)

        return ExperimentCollation(
            total_files=len(datasets),
            total_metrics=len(all_metrics),
            datasets=datasets,
            summary=self._generate_summary(all_metrics),
            collated_at=datetime.now().isoformat(),
            git_tracked=True,
        )

    def _generate_summary(self, metrics: list[MetricValue]) -> dict[str, Any]:
        """生成統計摘要"""
        metric_groups: dict[str, list[float]] = {}

        for metric in metrics:
            name = metric.metric_name
            if name not in metric_groups:
                metric_groups[name] = []

            try:
                value = float(metric.value)
                metric_groups[name].append(value)
            except (ValueError, TypeError):
                pass

        summary = {}
        for metric_name, values in metric_groups.items():
            if values:
                summary[metric_name] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "std": self._calculate_std(values),
                }

        return summary

    @staticmethod
    def _calculate_std(values: list[float]) -> float:
        """計算標準差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    def to_markdown(self, collation: ExperimentCollation) -> str:
        """轉換為 Markdown 報告"""
        md = "# 實驗結果彙總\n\n"
        md += f"**生成時間**：{collation.collated_at}\n"
        md += f"**總檔案數**：{collation.total_files}\n"
        md += f"**總指標數**：{collation.total_metrics}\n"
        md += f"**Git 管理**：{'✅ 是' if collation.git_tracked else '❌ 否'}\n\n"

        if not collation.datasets:
            md += "❌ 未發現任何實驗數據檔案\n"
            return md

        # 統計摘要
        md += "## 統計摘要\n\n"
        if collation.summary:
            md += "| 指標 | 數量 | 平均值 | 最小值 | 最大值 | 標準差 |\n"
            md += "|------|------|--------|--------|--------|--------|\n"
            for metric_name, stats in collation.summary.items():
                md += (
                    f"| {metric_name} | {stats['count']} | "
                    f"{stats['mean']:.4f} | {stats['min']:.4f} | "
                    f"{stats['max']:.4f} | {stats['std']:.4f} |\n"
                )
        else:
            md += "*無可量化指標*\n"

        md += "\n## 數據檔案\n\n"
        for dataset in collation.datasets:
            md += f"### {dataset.name}\n"
            md += f"- **路徑**：`{dataset.file_path}`\n"
            md += f"- **格式**：{dataset.file_type.upper()}\n"
            md += f"- **指標數**：{len(dataset.metrics)}\n"

            if dataset.metrics:
                md += "- **指標**：\n"
                for metric in dataset.metrics[:10]:  # 最多顯示 10 個
                    unit_str = f" {metric.unit}" if metric.unit else ""
                    md += f"  - {metric.metric_name}: {metric.value}{unit_str}\n"
                if len(dataset.metrics) > 10:
                    md += f"  - ... 及其他 {len(dataset.metrics) - 10} 個指標\n"

            if dataset.metadata:
                md += "- **元數據**：\n"
                for key, value in list(dataset.metadata.items())[:5]:
                    md += f"  - {key}: {value}\n"

            md += "\n"

        return md

    def to_dict(self, collation: ExperimentCollation) -> dict[str, Any]:
        """轉換為字典（用於 YAML 序列化）"""
        return {
            "total_files": collation.total_files,
            "total_metrics": collation.total_metrics,
            "collated_at": collation.collated_at,
            "git_tracked": collation.git_tracked,
            "summary": collation.summary,
            "datasets": [
                {
                    "name": dataset.name,
                    "file_path": dataset.file_path,
                    "file_type": dataset.file_type,
                    "metrics": [
                        {
                            "metric_name": m.metric_name,
                            "value": m.value,
                            "unit": m.unit,
                            "source_file": m.source_file,
                            "timestamp": m.timestamp,
                        }
                        for m in dataset.metrics
                    ],
                    "metadata": dataset.metadata,
                }
                for dataset in collation.datasets
            ],
        }
