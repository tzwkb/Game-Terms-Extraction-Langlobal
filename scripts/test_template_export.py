#!/usr/bin/env python3
"""Verify pipeline results -> unified 8-column annotation template (offline, no API)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.main import results_to_template_df, TEMPLATE_COLUMNS

RESULTS = [
    {"term": "墨门", "category": "门派势力", "source_text": "青长老说墨门弟子需恪守门规",
     "source_key": "DLG_001",
     "translation": "Momen", "match_type": "exact", "ref_term": "墨门", "ref_trans": "Momen", "ref_sim": 1.0},
    {"term": "八荒剑诀", "category": "技能", "source_text": "习得八荒剑诀第一式",
     "translation": "", "match_type": "no_translate"},
    {"term": "青长老", "category": "人名", "source_text": float("nan"),
     "translation": None, "match_type": "llm_translated"},
]

df = results_to_template_df(RESULTS, timestamp="2026-06-11T12:00:00")

CASES = [
    ("column order matches template", list(df.columns) == TEMPLATE_COLUMNS),
    ("row count", len(df) == 3),
    ("term -> 术语原文", df.loc[0, "术语原文"] == "墨门"),
    ("translation -> 术语译文", df.loc[0, "术语译文"] == "Momen"),
    ("source_text -> 来源原文", df.loc[0, "来源原文"] == "青长老说墨门弟子需恪守门规"),
    ("source_key -> Key值", df.loc[0, "Key值"] == "DLG_001"),
    ("missing source_key -> empty Key值", df.loc[1, "Key值"] == "" and df.loc[2, "Key值"] == ""),
    ("备注 all empty", (df["备注"] == "").all()),
    ("审核状态 all 未审核", (df["审核状态"] == "未审核").all()),
    ("timestamp applied", (df["最新修订时间"] == "2026-06-11T12:00:00").all()),
    ("NaN/None -> empty string", df.loc[2, "来源原文"] == "" and df.loc[2, "术语译文"] == ""),
    ("empty results -> header-only df", list(results_to_template_df([]).columns) == TEMPLATE_COLUMNS),
    ("default timestamp ISO-like", "T" in results_to_template_df(RESULTS[:1]).loc[0, "最新修订时间"]),
]

n_pass = 0
for name, ok in CASES:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    n_pass += ok

print(f"\n{n_pass}/{len(CASES)} passed")
sys.exit(0 if n_pass == len(CASES) else 1)
