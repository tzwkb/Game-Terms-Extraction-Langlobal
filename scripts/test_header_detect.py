#!/usr/bin/env python3
"""Verify LLM-based header detection (core/header_detect.py).

Reads api_key/api_base from .ui_config.json at project root.
Cases 1-4 call the real LLM API; case 5 is offline (no key -> default fallback).
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.header_detect import detect_source_column, detect_glossary_columns

CFG = json.loads((ROOT / ".ui_config.json").read_text(encoding="utf-8"))
API_KEY = os.getenv("OPENAI_API_KEY", "") or CFG.get("api_key", "")
API_BASE = os.getenv("OPENAI_API_BASE", "") or CFG.get("api_base", "https://api.vectorengine.ai/v1")
if not API_KEY:
    sys.exit("No API key: set OPENAI_API_KEY env or fill api_key in .ui_config.json")

TEMPLATE_8COL = pd.DataFrame({
    "Key值": ["UI_SKILL_001", "NPC_NAME_017"],
    "术语分类": ["技能", "人名"],
    "术语原文": ["八荒剑诀", "青长老"],
    "术语译文": ["Eight Wilds Sword Art", "Elder Qing"],
    "备注": ["", "门派长老"],
    "来源原文": ["习得八荒剑诀第一式", "青长老说墨门弟子需恪守门规"],
    "审核状态": ["已审核", "未审核"],
    "最新修订时间": ["2026-06-10T12:00:00", "2026-06-11T09:30:00"],
})

CLASSIC_2COL = pd.DataFrame({
    "中文": ["墨门", "八荒剑诀"],
    "英文": ["Momen", "Eight Wilds Sword Art"],
})

SWAPPED_2COL = pd.DataFrame({
    "English": ["Momen", "Elder Qing"],
    "术语": ["墨门", "青长老"],
})

SOURCE_3COL = pd.DataFrame({
    "Key": ["DLG_001", "DLG_002"],
    "原文文本": ["青长老说墨门弟子需恪守门规，不得擅自下山。", "你习得了八荒剑诀第一式，去找师父复命吧。"],
    "备注": ["", "新手引导"],
})

results = []


def check(name, actual, expected):
    ok = all(actual.get(k) == v for k, v in expected.items())
    results.append(ok)
    detail = "" if ok else f"  expected={expected} actual={actual}"
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{detail}")


print(f"API base: {API_BASE}\n")

r = detect_glossary_columns(TEMPLATE_8COL, API_KEY, API_BASE)
check("8-col template -> cn=2(术语原文), en=3(术语译文)", r, {"cn_col": 2, "en_col": 3, "method": "ai"})

r = detect_glossary_columns(CLASSIC_2COL, API_KEY, API_BASE)
check("classic 2-col -> cn=0, en=1", r, {"cn_col": 0, "en_col": 1, "method": "ai"})

r = detect_glossary_columns(SWAPPED_2COL, API_KEY, API_BASE)
check("swapped 2-col (EN first) -> cn=1, en=0", r, {"cn_col": 1, "en_col": 0, "method": "ai"})

r = detect_source_column(SOURCE_3COL, API_KEY, API_BASE)
check("source 3-col (key/text/note) -> text_col=1", r, {"text_col": 1, "method": "ai"})

r = detect_glossary_columns(TEMPLATE_8COL, api_key="", base_url="")
check("offline (no key) -> default 0/1 fallback", r, {"cn_col": 0, "en_col": 1, "method": "default"})

n_pass = sum(results)
print(f"\n{n_pass}/{len(results)} passed")
sys.exit(0 if n_pass == len(results) else 1)
