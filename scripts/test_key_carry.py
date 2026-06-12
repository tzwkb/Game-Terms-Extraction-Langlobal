#!/usr/bin/env python3
"""Verify source-row key carrying through context matching (offline, no API)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.main import _batch_match_context

TEXTS = [
    "你习得了八荒剑诀第一式，去找师父复命吧。",
    "青长老说墨门弟子需恪守门规，不得擅自下山。",
    "墨门后山藏有秘籍。",
]
KEYS = ["DLG_001", "DLG_002", "DLG_003"]

terms = [{"term": "墨门"}, {"term": "八荒剑诀"}, {"term": "不存在的术语"}]
_batch_match_context(terms, TEXTS, KEYS)

t = {x["term"]: x for x in terms}
CASES = [
    ("first matching line wins (墨门 -> DLG_002, not DLG_003)", t["墨门"]["source_key"] == "DLG_002"),
    ("source_text matches keyed line", t["墨门"]["source_text"] == TEXTS[1]),
    ("term in line 0 -> DLG_001", t["八荒剑诀"]["source_key"] == "DLG_001"),
    ("unmatched term -> empty key + empty text", t["不存在的术语"]["source_key"] == "" and t["不存在的术语"]["source_text"] == ""),
]

terms2 = [{"term": "墨门"}]
_batch_match_context(terms2, TEXTS)
CASES.append(("no keys passed -> empty source_key, context still set",
              terms2[0]["source_key"] == "" and terms2[0]["source_text"] == TEXTS[1]))

n_pass = 0
for name, ok in CASES:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    n_pass += ok

print(f"\n{n_pass}/{len(CASES)} passed")
sys.exit(0 if n_pass == len(CASES) else 1)
