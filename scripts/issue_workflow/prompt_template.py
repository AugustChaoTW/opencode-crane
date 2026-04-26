"""Prompt template substitution"""

import re
from typing import Dict


def substitute(template: str, variables: Dict[str, str]) -> str:
    pattern = re.compile(r"\{\{(\w+)\}\}")
    missing = pattern.findall(template)
    for var in missing:
        if var not in variables:
            raise ValueError(f"Missing variable: {var}")
    result = template
    for key, value in variables.items():
        result = result.replace("{{" + key + "}}", value)
    return result