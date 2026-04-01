"""測試 ExperimentCollationService — 實驗數據蒐集與彙總"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from crane.services.experiment_collation_service import ExperimentCollationService


@pytest.fixture
def temp_experiment_repo():
    """建立臨時實驗 repo 結構"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        data_dir = repo / "data"
        data_dir.mkdir()

        csv_file = data_dir / "results.csv"
        csv_file.write_text(
            "metric,value,unit\naccuracy,0.95,\nf1_score,0.92,\nlatency,45.5,ms\n",
            encoding="utf-8",
        )

        json_file = data_dir / "metrics.json"
        json_file.write_text(
            json.dumps(
                {
                    "precision": 0.96,
                    "recall": 0.91,
                    "auc": 0.98,
                }
            ),
            encoding="utf-8",
        )

        yaml_file = data_dir / "performance.yaml"
        yaml_file.write_text(
            yaml.dump(
                {
                    "throughput": 1000,
                    "memory_usage_mb": 512,
                    "inference_time_ms": 35,
                }
            ),
            encoding="utf-8",
        )

        ignored_config = data_dir / "config.json"
        ignored_config.write_text(
            json.dumps({"model": "transformer", "version": "1.0"}),
            encoding="utf-8",
        )

        yield repo


def test_discover_tracked_experiment_files(temp_experiment_repo):
    """測試發現實驗檔案"""
    svc = ExperimentCollationService(temp_experiment_repo)
    files = svc.discover_tracked_experiment_files()

    assert len(files) >= 3, "應該找到至少 3 個實驗檔案"
    file_names = [f.name for f in files]
    assert "results.csv" in file_names
    assert "metrics.json" in file_names
    assert "performance.yaml" in file_names


def test_parse_csv_file(temp_experiment_repo):
    """測試解析 CSV 檔案"""
    svc = ExperimentCollationService(temp_experiment_repo)
    csv_file = temp_experiment_repo / "data" / "results.csv"

    dataset = svc.parse_csv_file(csv_file)

    assert dataset.name == "results"
    assert dataset.file_type == "csv"
    assert len(dataset.metrics) == 3
    assert dataset.metrics[0].metric_name == "accuracy"
    assert dataset.metrics[0].value == 0.95


def test_parse_json_file(temp_experiment_repo):
    """測試解析 JSON 檔案"""
    svc = ExperimentCollationService(temp_experiment_repo)
    json_file = temp_experiment_repo / "data" / "metrics.json"

    dataset = svc.parse_json_file(json_file)

    assert dataset.name == "metrics"
    assert dataset.file_type == "json"
    assert len(dataset.metrics) == 3
    assert dataset.metrics[0].metric_name == "precision"


def test_parse_yaml_file(temp_experiment_repo):
    """測試解析 YAML 檔案"""
    svc = ExperimentCollationService(temp_experiment_repo)
    yaml_file = temp_experiment_repo / "data" / "performance.yaml"

    dataset = svc.parse_yaml_file(yaml_file)

    assert dataset.name == "performance"
    assert dataset.file_type == "yaml"
    assert len(dataset.metrics) >= 3


def test_collate_all(temp_experiment_repo):
    """測試彙總所有實驗數據"""
    svc = ExperimentCollationService(temp_experiment_repo)
    collation = svc.collate_all()

    assert collation.total_files >= 3
    assert collation.total_metrics >= 9
    assert len(collation.datasets) >= 3
    assert len(collation.summary) > 0


def test_generate_summary(temp_experiment_repo):
    """測試生成統計摘要"""
    svc = ExperimentCollationService(temp_experiment_repo)
    collation = svc.collate_all()

    assert "accuracy" in collation.summary
    summary_entry = collation.summary["accuracy"]
    assert "mean" in summary_entry
    assert "min" in summary_entry
    assert "max" in summary_entry
    assert "count" in summary_entry


def test_to_markdown(temp_experiment_repo):
    """測試轉換為 Markdown 報告"""
    svc = ExperimentCollationService(temp_experiment_repo)
    collation = svc.collate_all()

    md = svc.to_markdown(collation)

    assert "實驗結果彙總" in md
    assert "統計摘要" in md
    assert "數據檔案" in md
    assert len(md) > 100


def test_to_dict(temp_experiment_repo):
    """測試轉換為字典"""
    svc = ExperimentCollationService(temp_experiment_repo)
    collation = svc.collate_all()

    result_dict = svc.to_dict(collation)

    assert result_dict["total_files"] >= 3
    assert result_dict["total_metrics"] >= 9
    assert "datasets" in result_dict
    assert "summary" in result_dict
    assert "collated_at" in result_dict


def test_calculate_std():
    """測試標準差計算"""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    std = ExperimentCollationService._calculate_std(values)

    assert std > 1.4 and std < 1.5


def test_empty_repo():
    """測試空倉庫"""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = ExperimentCollationService(tmpdir)
        collation = svc.collate_all()

        assert collation.total_files == 0
        assert collation.total_metrics == 0
        assert len(collation.datasets) == 0
