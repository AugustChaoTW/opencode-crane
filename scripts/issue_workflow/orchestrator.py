"""Fetch and group closed issues from GitHub"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict


def fetch_closed_issues(label: str, limit: int = 50) -> List[Dict]:
    cmd = [
        "gh", "issue", "list",
        "--state", "closed",
        "--label", label,
        "--limit", str(limit),
        "--json", "number,title,body,state,labels,comments",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    result.check_returncode()
    return json.loads(result.stdout)


def group_issues(issues: List[Dict], batch_size: int = 3) -> List[List[Dict]]:
    groups = []
    for i in range(0, len(issues), batch_size):
        groups.append(issues[i:i+batch_size])
    return groups


def write_batch(issues: List[Dict], output_file: Path):
    output_file.write_text(json.dumps(issues, ensure_ascii=False, indent=2))