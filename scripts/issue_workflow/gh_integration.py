"""gh CLI integration"""

import subprocess


def post_comment(issue_number: int, body: str, dry_run: bool = False):
    if dry_run:
        return
    cmd = ["gh", "issue", "comment", str(issue_number), "--body", body]
    subprocess.run(cmd, check=True)


def reopen_if_needed(issue_number: int, verdict: str, dry_run: bool = False):
    if verdict == "NEEDS_WORK" and not dry_run:
        cmd = ["gh", "issue", "reopen", str(issue_number)]
        subprocess.run(cmd, check=True)