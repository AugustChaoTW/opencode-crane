"""ExperimentGenerationService 單元測試"""

import tempfile
from pathlib import Path

import pytest

from src.crane.services.experiment_generation_service import (
    AblationModule,
    CodeGenerationModule,
    ExperimentConfig,
    ExperimentGenerationService,
    ExperimentResult,
    HyperparameterOptimizationModule,
    MethodParsingModule,
    TreeSearchModule,
)


class TestMethodParsingModule:
    def test_parse_methods_section(self):
        latex_content = r"""
        \section{Methods}
        We use BERT with learning_rate=0.001 and batch_size=32.
        We trained on ImageNet dataset.
        \section{Results}
        """
        parser = MethodParsingModule()
        result = parser.parse_methods_section(latex_content)

        assert "algorithm" in result
        assert "BERT" in result.get("algorithm", "")
        assert "ImageNet" in result.get("datasets", [])

    def test_extract_hyperparameters(self):
        parser = MethodParsingModule()
        text = "learning_rate = 0.001, batch_size = 64"
        hyperparams = parser._extract_hyperparameters(text)

        assert hyperparams.get("learning_rate") == 0.001
        assert hyperparams.get("batch_size") == 64


class TestCodeGenerationModule:
    def test_generate_baseline_code(self):
        generator = CodeGenerationModule()
        parsed_methods = {
            "algorithm": "BERT",
            "hyperparameters": {"learning_rate": 0.001, "batch_size": 32},
            "datasets": ["CIFAR10"],
        }
        code = generator.generate_baseline_code(parsed_methods)

        assert "BERT" in code
        assert "0.001" in code
        assert "32" in code


class TestHyperparameterOptimizationModule:
    def test_optimize_hyperparameters(self):
        optimizer = HyperparameterOptimizationModule()
        config = ExperimentConfig(
            algorithm="BERT",
            hyperparameters={"learning_rate": 0.001},
            dataset="CIFAR10",
            implementation_id="test",
        )
        search_space = {"learning_rate": [0.0001, 0.001, 0.01]}

        best_config, history = optimizer.optimize_hyperparameters(
            config, search_space, max_trials=3
        )

        assert len(history) > 0
        assert best_config is not None
        assert all(r.stage == 2 for r in history)


class TestTreeSearchModule:
    def test_execute_tree_search(self):
        searcher = TreeSearchModule()
        config = ExperimentConfig(
            algorithm="BERT",
            hyperparameters={"learning_rate": 0.001},
            dataset="CIFAR10",
            implementation_id="test",
        )

        tree = searcher.execute_tree_search(config, search_depth=2, branching_factor=2)

        assert tree.root is not None
        assert len(tree.children) == 2
        assert all(r.stage == 3 for r in [c.root for c in tree.children])


class TestAblationModule:
    def test_identify_key_components(self):
        ablation = AblationModule()
        parsed_methods = {"algorithm": "Transformer", "loss_functions": ["cross entropy"]}

        components = ablation.identify_key_components(parsed_methods)

        assert len(components) > 0
        assert "attention_mechanism" in components

    def test_generate_ablation_studies(self):
        ablation = AblationModule()
        config = ExperimentConfig(
            algorithm="BERT",
            hyperparameters={},
            dataset="CIFAR10",
            implementation_id="test",
        )
        components = ["attention", "feed_forward"]

        ablation_configs = ablation.generate_ablation_studies(config, components)

        assert len(ablation_configs) == 2
        assert all(
            c.implementation_id.startswith(config.implementation_id) for c in ablation_configs
        )


class TestExperimentGenerationService:
    def test_run_full_pipeline(self):
        service = ExperimentGenerationService()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
            f.write(
                r"""
            \section{Methods}
            We implement BERT with learning_rate=0.001.
            \section{Results}
            """
            )
            temp_file = f.name

        try:
            result = service.run_full_pipeline(
                paper_path=temp_file, dataset_info={"name": "CIFAR10"}, budget_hours=1.0
            )

            assert result.get("success") is True
            assert "total_experiments" in result
            assert result["stages_completed"] == 4
        finally:
            Path(temp_file).unlink()

    def test_get_results_summary(self):
        service = ExperimentGenerationService()

        config = ExperimentConfig(
            algorithm="BERT",
            hyperparameters={},
            dataset="CIFAR10",
            implementation_id="test",
        )
        result = ExperimentResult(
            config=config,
            metrics={"accuracy": 0.85, "loss": 0.15},
            runtime_seconds=100,
            code_path="/tmp/test.py",
            notes="test",
            stage=1,
        )
        service.experiment_results.append(result)

        summary = service.get_results_summary()

        assert summary["total_experiments"] == 1
        assert summary["best_accuracy"] == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
