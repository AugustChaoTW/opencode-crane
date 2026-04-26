"""Feynman + Le Chun analysis for issues"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any


def run_feynman_analysis(issue_body: str, paper_path: str = "/fake/paper.tex") -> Dict[str, Any]:
    cmd = [
        "crane", "generate_feynman_session",
        "--paper_path", paper_path,
        "--mode", "methodology",
        "--num_questions", "5",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            return {"verdict": "PASS", "questions": data}
        return {"verdict": "PASS", "questions": data.get("questions", [])}
    return {"verdict": "NEEDS_WORK", "questions": ["Feynman call failed"]}


def le_chun_validate(issue: Dict) -> Dict[str, bool]:
    body = issue.get("body", "")
    return {
        "reproducible_steps": bool(re.search(r"## 重現步驟", body)),
        "quantified_metrics": bool(re.search(r"## (預期|實際|量化差異)", body)),
        "dependencies": bool(re.search(r"## 依賴", body)),
    }


def compute_verdict(feynman: Dict, le_chun: Dict) -> str:
    if feynman.get("verdict") == "NEEDS_WORK":
        return "NEEDS_WORK"
    if le_chun.get("verdict") == "NEEDS_WORK":
        return "NEEDS_WORK"
    if not all(le_chun.values()):
        return "NEEDS_WORK"
    return "PASS"


def write_log(log_entries: List[Dict], output_file: Path):
    output_file.write_text(json.dumps(log_entries, ensure_ascii=False, indent=2))