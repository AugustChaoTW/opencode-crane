# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.paper_code_alignment_service import PaperCodeAlignmentService


@pytest.fixture
def service(tmp_path: Path) -> PaperCodeAlignmentService:
    return PaperCodeAlignmentService(refs_dir=str(tmp_path / "references"))


def _write_latex(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _write_code(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_latex_settings_missing_file_raises(service: PaperCodeAlignmentService) -> None:
    with pytest.raises(FileNotFoundError):
        service.extract_latex_settings("/tmp/does-not-exist.tex")


def test_extract_latex_settings_from_table_and_inline(
    service: PaperCodeAlignmentService, tmp_path: Path
) -> None:
    paper = _write_latex(
        tmp_path / "paper.tex",
        r"""
\begin{tabular}{ll}
Learning Rate & 1e-3 \\
Batch Size & 32 \\
\end{tabular}
We use dataset: CIFAR10.
Evaluation metric: F1.
""",
    )

    settings = service.extract_latex_settings(str(paper))
    hparams = settings["hyperparameters"]

    assert isinstance(hparams, dict)
    assert hparams["learning_rate"] == "1e-3"
    assert hparams["batch_size"] == "32"
    assert "cifar10" in settings["datasets"]
    assert "f1" in settings["metrics"]


def test_extract_latex_settings_detects_inline_hparams(
    service: PaperCodeAlignmentService, tmp_path: Path
) -> None:
    paper = _write_latex(
        tmp_path / "inline.tex",
        "The learning rate is 0.001, epochs=20, and dropout: 0.1.",
    )

    settings = service.extract_latex_settings(str(paper))
    hparams = settings["hyperparameters"]
    assert isinstance(hparams, dict)
    assert hparams["learning_rate"] == "0.001"
    assert hparams["epochs"] == "20"
    assert hparams["dropout"] == "0.1"


def test_extract_code_settings_missing_path_raises(service: PaperCodeAlignmentService) -> None:
    with pytest.raises(FileNotFoundError):
        service.extract_code_settings("/tmp/no-code-here")


def test_extract_code_settings_from_file(
    service: PaperCodeAlignmentService, tmp_path: Path
) -> None:
    code = _write_code(
        tmp_path / "train.py",
        """
import torch

LR = 0.001
BATCH_SIZE = 32

optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
metric_name = "accuracy"
dataset_name = "CIFAR10"
""",
    )

    settings = service.extract_code_settings(str(code))
    hparams = settings["hyperparameters"]

    assert isinstance(hparams, dict)
    assert hparams["learning_rate"] == "0.001"
    assert hparams["batch_size"] == "32"
    assert hparams["weight_decay"] == "0.0001"
    assert "accuracy" in settings["metrics"]
    assert "cifar10" in settings["datasets"]


def test_extract_code_settings_from_directory(
    service: PaperCodeAlignmentService, tmp_path: Path
) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _write_code(src_dir / "args.py", "parser.add_argument('--batch-size', default=64)")
    _write_code(src_dir / "config.py", "config = {'lr': 5e-4, 'epochs': 15}")

    settings = service.extract_code_settings(str(src_dir))
    hparams = settings["hyperparameters"]

    assert isinstance(hparams, dict)
    assert hparams["batch_size"] == "64"
    assert hparams["learning_rate"] == "0.0005"
    assert hparams["epochs"] == "15"


def test_compare_settings_exact_match(service: PaperCodeAlignmentService) -> None:
    latex = {
        "hyperparameters": {"learning_rate": "0.001", "batch_size": "32"},
        "metrics": ["accuracy"],
        "datasets": ["cifar10"],
    }
    code = {
        "hyperparameters": {"learning_rate": "0.001", "batch_size": "32"},
        "metrics": ["accuracy"],
        "datasets": ["cifar10"],
    }

    result = service.compare_settings(latex, code)
    assert result["aligned"] is True
    assert result["alignment_score"] == 1.0
    assert len(result["mismatches"]) == 0


def test_compare_settings_semantic_alias_and_numeric_equivalence(
    service: PaperCodeAlignmentService,
) -> None:
    latex = {
        "hyperparameters": {"learning rate": "1e-3", "batch size": "32"},
        "metrics": ["acc"],
        "datasets": ["CIFAR10"],
    }
    code = {
        "hyperparameters": {"lr": "0.001", "batch_size": "32"},
        "metrics": ["accuracy"],
        "datasets": ["cifar10"],
    }

    result = service.compare_settings(latex, code)
    assert result["aligned"] is True
    assert result["alignment_score"] == 1.0


def test_compare_settings_detects_mismatch(service: PaperCodeAlignmentService) -> None:
    latex = {
        "hyperparameters": {"learning_rate": "0.001", "batch_size": "32"},
        "metrics": ["f1"],
        "datasets": ["cifar10"],
    }
    code = {
        "hyperparameters": {"learning_rate": "0.01", "batch_size": "64"},
        "metrics": ["accuracy"],
        "datasets": ["mnist"],
    }

    result = service.compare_settings(latex, code)
    assert result["aligned"] is False
    assert result["alignment_score"] < 0.5
    assert len(result["mismatches"]) >= 4


def test_compare_settings_requires_expected_sections(service: PaperCodeAlignmentService) -> None:
    with pytest.raises(ValueError):
        service.compare_settings({"hyperparameters": {}}, {"hyperparameters": {}})


def test_generate_alignment_report_end_to_end(
    service: PaperCodeAlignmentService, tmp_path: Path
) -> None:
    paper = _write_latex(
        tmp_path / "paper.tex",
        r"""
\begin{tabular}{ll}
Learning Rate & 0.001 \\
Batch Size & 32 \\
\end{tabular}
Dataset: CIFAR10.
Metric: Accuracy.
""",
    )
    code = _write_code(
        tmp_path / "train.py",
        """
lr = 1e-3
batch_size = 32
metric = 'accuracy'
dataset = 'cifar10'
""",
    )

    result = service.generate_alignment_report(str(paper), str(code))
    assert result["aligned"] is True
    assert "latex_settings" in result
    assert "code_settings" in result


def test_compare_settings_handles_percentage_equivalence(
    service: PaperCodeAlignmentService,
) -> None:
    latex = {
        "hyperparameters": {"dropout": "10%"},
        "metrics": [],
        "datasets": [],
    }
    code = {
        "hyperparameters": {"dropout": "0.1"},
        "metrics": [],
        "datasets": [],
    }

    result = service.compare_settings(latex, code)
    assert result["aligned"] is True
    assert result["alignment_score"] == 1.0


def test_alignment_detection_accuracy_on_synthetic_set(service: PaperCodeAlignmentService) -> None:
    cases: list[tuple[dict[str, object], dict[str, object], bool]] = [
        (
            {
                "hyperparameters": {"learning_rate": "0.001", "batch_size": "32"},
                "metrics": ["accuracy"],
                "datasets": ["cifar10"],
            },
            {
                "hyperparameters": {"lr": "1e-3", "batch_size": "32"},
                "metrics": ["acc"],
                "datasets": ["cifar10"],
            },
            True,
        ),
        (
            {
                "hyperparameters": {"dropout": "10%"},
                "metrics": ["f1"],
                "datasets": ["mnist"],
            },
            {
                "hyperparameters": {"dropout": "0.1"},
                "metrics": ["f1_score"],
                "datasets": ["mnist"],
            },
            True,
        ),
        (
            {
                "hyperparameters": {"epochs": "20", "batch_size": "64"},
                "metrics": ["accuracy"],
                "datasets": ["imagenet"],
            },
            {
                "hyperparameters": {"epochs": "20", "batch_size": "64"},
                "metrics": ["accuracy"],
                "datasets": ["imagenet"],
            },
            True,
        ),
        (
            {
                "hyperparameters": {"learning_rate": "0.01", "batch_size": "128"},
                "metrics": ["accuracy"],
                "datasets": ["cifar100"],
            },
            {
                "hyperparameters": {"learning_rate": "0.001", "batch_size": "32"},
                "metrics": ["f1"],
                "datasets": ["mnist"],
            },
            False,
        ),
        (
            {
                "hyperparameters": {"weight_decay": "0.0001"},
                "metrics": ["auc"],
                "datasets": ["squad"],
            },
            {
                "hyperparameters": {"weight_decay": "0.0001"},
                "metrics": ["auc"],
                "datasets": ["squad"],
            },
            True,
        ),
        (
            {
                "hyperparameters": {"seed": "42"},
                "metrics": ["bleu"],
                "datasets": ["wikitext"],
            },
            {
                "hyperparameters": {"seed": "7"},
                "metrics": ["bleu"],
                "datasets": ["wikitext"],
            },
            False,
        ),
    ]

    correct = 0
    for latex, code, expected in cases:
        result = service.compare_settings(latex, code)
        if bool(result["aligned"]) == expected:
            correct += 1

    accuracy = correct / len(cases)
    assert accuracy >= 0.85
