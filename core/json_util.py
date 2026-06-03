"""Shared JSON-block extraction from LLM responses."""
import re, json
from typing import Any


def extract_json(raw: str) -> Any:
    """Try to parse JSON from raw LLM output, falling through extraction strategies.

    Returns parsed object on success, None if all strategies fail.
    """
    candidates = [raw.strip()]
    m = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', raw, re.DOTALL)
    if m:
        candidates.append(m.group(1).strip())
    for ch in ('{', '['):
        start = raw.find(ch)
        if start >= 0:
            end_ch = '}' if ch == '{' else ']'
            end = raw.rfind(end_ch)
            if end > start:
                candidates.append(raw[start:end + 1])

    for src in candidates:
        try:
            return json.loads(src)
        except (json.JSONDecodeError, ValueError):
            continue
    return None
