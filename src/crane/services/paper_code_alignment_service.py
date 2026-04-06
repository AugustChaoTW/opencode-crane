from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _MatchRecord:
    category: str
    key: str
    latex_value: str
    code_value: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "key": self.key,
            "latex_value": self.latex_value,
            "code_value": self.code_value,
            "reason": self.reason,
        }


class _CodeVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.hyperparameters: dict[str, str] = {}
        self.metrics: set[str] = set()
        self.datasets: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        value = _literal_to_text(node.value)
        if value is not None:
            for target in node.targets:
                for name in _extract_target_names(target):
                    self._capture_assignment(name, value)

        if isinstance(node.value, ast.Dict):
            self._capture_dict_literal(node.value)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            value = _literal_to_text(node.value)
            if value is not None:
                for name in _extract_target_names(node.target):
                    self._capture_assignment(name, value)

            if isinstance(node.value, ast.Dict):
                self._capture_dict_literal(node.value)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func_name = _call_name(node)

        if func_name.endswith("add_argument"):
            self._capture_argparse_defaults(node)

        for keyword in node.keywords:
            arg_name = keyword.arg or ""
            value = _literal_to_text(keyword.value)
            if not arg_name or value is None:
                continue
            self._capture_assignment(arg_name, value)

        for arg in node.args:
            literal = _literal_to_text(arg)
            if literal is None:
                continue
            self._capture_dataset(literal)
            self._capture_metric(literal)

        self.generic_visit(node)

    def _capture_argparse_defaults(self, node: ast.Call) -> None:
        argument_name = ""
        if node.args:
            first_arg = _literal_to_text(node.args[0])
            if first_arg:
                argument_name = first_arg.lstrip("-")

        for keyword in node.keywords:
            if keyword.arg == "dest":
                dest = _literal_to_text(keyword.value)
                if dest:
                    argument_name = dest

        if not argument_name:
            return

        default_value = ""
        for keyword in node.keywords:
            if keyword.arg == "default":
                val = _literal_to_text(keyword.value)
                if val is not None:
                    default_value = val
                break

        if default_value:
            self._capture_assignment(argument_name, default_value)

    def _capture_dict_literal(self, node: ast.Dict) -> None:
        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                continue
            key = _literal_to_text(key_node)
            value = _literal_to_text(value_node)
            if key is None or value is None:
                continue
            self._capture_assignment(key, value)

    def _capture_assignment(self, name: str, value: str) -> None:
        normalized_name = _normalize_key(name)
        if not normalized_name:
            return

        if normalized_name in _KNOWN_HPARAM_ALIASES:
            canonical = _KNOWN_HPARAM_ALIASES[normalized_name]
            self.hyperparameters[canonical] = value
            return

        if _looks_like_hyperparameter(normalized_name):
            self.hyperparameters[normalized_name] = value

        self._capture_metric(name)
        self._capture_metric(value)
        self._capture_dataset(name)
        self._capture_dataset(value)

    def _capture_metric(self, text: str) -> None:
        metric = _normalize_metric(text)
        if metric:
            self.metrics.add(metric)

    def _capture_dataset(self, text: str) -> None:
        dataset = _normalize_dataset(text)
        if dataset:
            self.datasets.add(dataset)


_KNOWN_HPARAM_ALIASES: dict[str, str] = {
    "lr": "learning_rate",
    "learning_rate": "learning_rate",
    "learningrate": "learning_rate",
    "batch_size": "batch_size",
    "batchsize": "batch_size",
    "epochs": "epochs",
    "epoch": "epochs",
    "num_epochs": "epochs",
    "dropout": "dropout",
    "weight_decay": "weight_decay",
    "wd": "weight_decay",
    "momentum": "momentum",
    "seed": "seed",
}

_HPARAM_HINTS = (
    "learning",
    "lr",
    "batch",
    "epoch",
    "dropout",
    "weight_decay",
    "momentum",
    "optimizer",
    "seed",
)

_METRIC_SYNONYMS: dict[str, str] = {
    "acc": "accuracy",
    "accuracy": "accuracy",
    "f1": "f1",
    "f1_score": "f1",
    "precision": "precision",
    "recall": "recall",
    "auc": "auc",
    "auroc": "auc",
    "bleu": "bleu",
    "rouge": "rouge",
}

_DATASET_KEYWORDS = (
    "mnist",
    "cifar10",
    "cifar100",
    "imagenet",
    "wikitext",
    "squad",
    "glue",
)

_TABLE_ROW_PATTERN = re.compile(r"^(?P<key>[^&\\\\]+?)\s*&\s*(?P<value>[^\\\\]+?)\\\\")
_INLINE_SETTING_PATTERN = re.compile(
    r"(?P<key>learning\s*rate|lr|batch\s*size|epochs?|dropout|weight\s*decay|momentum|seed)"
    r"\s*(?:=|:|is|of)?\s*(?P<value>[0-9]+(?:\.[0-9]+)?(?:e-?[0-9]+)?%?)",
    re.IGNORECASE,
)
_DATASET_PATTERN = re.compile(
    r"(?:dataset|datasets?)\s*(?:is|are|:|=)?\s*([A-Za-z0-9_\-/+]+)",
    re.IGNORECASE,
)
_METRIC_PATTERN = re.compile(
    r"(?:metric|metrics?|evaluation|score|scores?)\s*(?:is|are|:|=)?\s*([A-Za-z0-9_\-/+]+)",
    re.IGNORECASE,
)


class PaperCodeAlignmentService:
    def __init__(self, refs_dir: str = "references"):
        """
        Initialize paper-code alignment service.

        Args:
            refs_dir: Reference directory path retained for workspace consistency.

        Returns:
            None

        Raises:
            ValueError: If refs_dir is empty.
        """
        if not refs_dir:
            raise ValueError("refs_dir must not be empty")
        self.refs_dir = str(Path(refs_dir))

    def extract_latex_settings(self, latex_path: str) -> dict[str, object]:
        """
        Parse LaTeX file and extract experiment settings.

        Args:
            latex_path: Path to LaTeX manuscript.

        Returns:
            Dictionary containing extracted settings:
            - hyperparameters: dict[str, str]
            - metrics: list[str]
            - datasets: list[str]

        Raises:
            FileNotFoundError: If LaTeX file does not exist.
        """
        path = Path(latex_path)
        if not path.exists():
            raise FileNotFoundError(f"LaTeX file not found: {latex_path}")

        text = path.read_text(encoding="utf-8")
        hyperparameters: dict[str, str] = {}
        metrics: set[str] = set()
        datasets: set[str] = set()

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            table_match = _TABLE_ROW_PATTERN.match(stripped)
            if table_match:
                key = _normalize_key(table_match.group("key"))
                value = table_match.group("value").strip()
                canonical = _KNOWN_HPARAM_ALIASES.get(key, key)
                if canonical and (
                    _looks_like_hyperparameter(canonical)
                    or canonical in _KNOWN_HPARAM_ALIASES.values()
                ):
                    hyperparameters[canonical] = value

            for inline in _INLINE_SETTING_PATTERN.finditer(stripped):
                raw_key = inline.group("key")
                raw_value = inline.group("value")
                key = _KNOWN_HPARAM_ALIASES.get(_normalize_key(raw_key), _normalize_key(raw_key))
                if key:
                    hyperparameters[key] = raw_value

            for dataset_match in _DATASET_PATTERN.finditer(stripped):
                dataset = _normalize_dataset(dataset_match.group(1))
                if dataset:
                    datasets.add(dataset)

            for metric_match in _METRIC_PATTERN.finditer(stripped):
                metric = _normalize_metric(metric_match.group(1))
                if metric:
                    metrics.add(metric)

            for keyword in _DATASET_KEYWORDS:
                if keyword in stripped.lower():
                    datasets.add(keyword)

            metric_token = _normalize_metric(stripped)
            if metric_token:
                metrics.add(metric_token)

        return {
            "hyperparameters": hyperparameters,
            "metrics": sorted(metrics),
            "datasets": sorted(datasets),
        }

    def extract_code_settings(self, code_path: str) -> dict[str, object]:
        """
        Parse Python codebase and extract implementation settings with AST.

        Args:
            code_path: Path to Python file or project directory.

        Returns:
            Dictionary containing extracted settings:
            - hyperparameters: dict[str, str]
            - metrics: list[str]
            - datasets: list[str]

        Raises:
            FileNotFoundError: If code path does not exist.
        """
        path = Path(code_path)
        if not path.exists():
            raise FileNotFoundError(f"Code path not found: {code_path}")

        python_files: list[Path] = [path] if path.is_file() else sorted(path.rglob("*.py"))

        visitor = _CodeVisitor()
        for py_file in python_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (UnicodeDecodeError, SyntaxError):
                continue
            visitor.visit(tree)

        return {
            "hyperparameters": dict(sorted(visitor.hyperparameters.items())),
            "metrics": sorted(visitor.metrics),
            "datasets": sorted(visitor.datasets),
        }

    def compare_settings(
        self,
        latex_settings: dict[str, object],
        code_settings: dict[str, object],
    ) -> dict[str, object]:
        """
        Compare extracted paper and code settings with semantic normalization.

        Args:
            latex_settings: Settings extracted from LaTeX.
            code_settings: Settings extracted from code.

        Returns:
            Alignment report dictionary containing:
            - aligned: bool
            - matches: list[dict[str, str]]
            - mismatches: list[dict[str, str]]
            - alignment_score: float

        Raises:
            ValueError: If required setting sections are missing.
        """
        required_keys = {"hyperparameters", "metrics", "datasets"}
        if not required_keys.issubset(set(latex_settings.keys())):
            raise ValueError("latex_settings must include hyperparameters, metrics, and datasets")
        if not required_keys.issubset(set(code_settings.keys())):
            raise ValueError("code_settings must include hyperparameters, metrics, and datasets")

        latex_hp = _as_string_dict(latex_settings.get("hyperparameters"))
        code_hp = _as_string_dict(code_settings.get("hyperparameters"))
        latex_metrics = _as_string_list(latex_settings.get("metrics"))
        code_metrics = _as_string_list(code_settings.get("metrics"))
        latex_datasets = _as_string_list(latex_settings.get("datasets"))
        code_datasets = _as_string_list(code_settings.get("datasets"))

        matches: list[_MatchRecord] = []
        mismatches: list[_MatchRecord] = []

        for key, latex_value in latex_hp.items():
            canonical = _KNOWN_HPARAM_ALIASES.get(_normalize_key(key), _normalize_key(key))
            code_key = _find_key(code_hp, canonical)
            if code_key is None:
                mismatches.append(
                    _MatchRecord(
                        category="hyperparameter",
                        key=canonical,
                        latex_value=latex_value,
                        code_value="",
                        reason="missing_in_code",
                    )
                )
                continue

            code_value = code_hp[code_key]
            if _values_semantically_equal(latex_value, code_value):
                matches.append(
                    _MatchRecord(
                        category="hyperparameter",
                        key=canonical,
                        latex_value=latex_value,
                        code_value=code_value,
                        reason="value_match",
                    )
                )
            else:
                mismatches.append(
                    _MatchRecord(
                        category="hyperparameter",
                        key=canonical,
                        latex_value=latex_value,
                        code_value=code_value,
                        reason="value_mismatch",
                    )
                )

        code_metric_set = {_normalize_metric(metric) for metric in code_metrics if metric}
        for metric in latex_metrics:
            normalized = _normalize_metric(metric)
            if not normalized:
                continue
            if normalized in code_metric_set:
                matches.append(
                    _MatchRecord(
                        category="metric",
                        key=normalized,
                        latex_value=metric,
                        code_value=normalized,
                        reason="metric_found",
                    )
                )
            else:
                mismatches.append(
                    _MatchRecord(
                        category="metric",
                        key=normalized,
                        latex_value=metric,
                        code_value="",
                        reason="metric_missing_in_code",
                    )
                )

        code_dataset_set = {_normalize_dataset(dataset) for dataset in code_datasets if dataset}
        for dataset in latex_datasets:
            normalized = _normalize_dataset(dataset)
            if not normalized:
                continue
            if normalized in code_dataset_set:
                matches.append(
                    _MatchRecord(
                        category="dataset",
                        key=normalized,
                        latex_value=dataset,
                        code_value=normalized,
                        reason="dataset_found",
                    )
                )
            else:
                mismatches.append(
                    _MatchRecord(
                        category="dataset",
                        key=normalized,
                        latex_value=dataset,
                        code_value="",
                        reason="dataset_missing_in_code",
                    )
                )

        total_compared = len(matches) + len(mismatches)
        alignment_score = len(matches) / total_compared if total_compared else 0.0

        return {
            "aligned": alignment_score >= 0.85,
            "matches": [entry.to_dict() for entry in matches],
            "mismatches": [entry.to_dict() for entry in mismatches],
            "alignment_score": round(alignment_score, 4),
        }

    def generate_alignment_report(self, latex_path: str, code_path: str) -> dict[str, object]:
        """
        Generate full paper-code alignment report.

        Args:
            latex_path: Path to LaTeX manuscript.
            code_path: Path to implementation file or directory.

        Returns:
            Unified report with extracted settings and alignment summary.

        Raises:
            FileNotFoundError: If input files/paths do not exist.
        """
        latex_settings = self.extract_latex_settings(latex_path)
        code_settings = self.extract_code_settings(code_path)
        comparison = self.compare_settings(latex_settings, code_settings)

        report = dict(comparison)
        report["latex_settings"] = latex_settings
        report["code_settings"] = code_settings
        return report


def _extract_target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for item in node.elts:
            names.extend(_extract_target_names(item))
        return names
    return []


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _literal_to_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        if node.value is None:
            return None
        return str(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _literal_to_text(node.operand)
        if operand is None:
            return None
        sign = "-" if isinstance(node.op, ast.USub) else "+"
        return f"{sign}{operand}"
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
        return "".join(parts) if parts else None
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [_literal_to_text(item) for item in node.elts]
        filtered = [item for item in values if item is not None]
        return ",".join(filtered) if filtered else None
    return None


def _normalize_key(text: str) -> str:
    lowered = text.strip().lower()
    lowered = lowered.replace("-", "_").replace(" ", "_")
    lowered = re.sub(r"[^a-z0-9_]+", "", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return lowered


def _normalize_metric(text: str) -> str:
    token = _normalize_key(text)
    if not token:
        return ""
    if token in _METRIC_SYNONYMS:
        return _METRIC_SYNONYMS[token]
    for alias, canonical in _METRIC_SYNONYMS.items():
        if alias in token:
            return canonical
    return ""


def _normalize_dataset(text: str) -> str:
    token = _normalize_key(text)
    if not token:
        return ""
    for keyword in _DATASET_KEYWORDS:
        if keyword in token:
            return keyword
    if token.endswith("dataset"):
        token = token[: -len("dataset")]
    token = token.strip("_")
    return token if len(token) >= 3 else ""


def _looks_like_hyperparameter(name: str) -> bool:
    return any(hint in name for hint in _HPARAM_HINTS)


def _try_parse_number(value: str) -> tuple[float, bool] | None:
    stripped = value.strip().lower().replace(" ", "")
    is_percent = stripped.endswith("%")
    if is_percent:
        stripped = stripped[:-1]

    if not stripped:
        return None

    try:
        numeric = float(stripped)
    except ValueError:
        return None
    return numeric, is_percent


def _values_semantically_equal(left: str, right: str) -> bool:
    left_num = _try_parse_number(left)
    right_num = _try_parse_number(right)
    if left_num is not None and right_num is not None:
        left_value, left_percent = left_num
        right_value, right_percent = right_num

        if left_percent != right_percent:
            if left_percent:
                left_value = left_value / 100.0
            if right_percent:
                right_value = right_value / 100.0

        baseline = max(abs(left_value), abs(right_value), 1.0)
        return abs(left_value - right_value) <= 1e-6 * baseline

    normalized_left = re.sub(r"\s+", "", left.strip().lower())
    normalized_right = re.sub(r"\s+", "", right.strip().lower())
    return normalized_left == normalized_right


def _as_string_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, val in value.items():
        result[str(key)] = str(val)
    return result


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _find_key(mapping: dict[str, str], canonical: str) -> str | None:
    for raw_key in mapping.keys():
        normalized = _normalize_key(raw_key)
        resolved = _KNOWN_HPARAM_ALIASES.get(normalized, normalized)
        if resolved == canonical:
            return raw_key
    return None
