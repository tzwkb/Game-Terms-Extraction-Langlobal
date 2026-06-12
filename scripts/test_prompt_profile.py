#!/usr/bin/env python3
"""Verify profile wiring: translation_rules injection, bilingual few-shot
preference, and term_corrections override (offline, no API)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.prompt_base import build_translation_prompt, build_user_prompt
from core.main import _apply_term_corrections

results = []


def check(name, ok):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")


PROFILE = {
    "game_type": "武侠",
    "term_categories": ["人名", "技能"],
    "translation_rules": ["角色名 → 音译（拼音）", "技能名 → 意译"],
    "term_corrections": {"墨门": "Momen"},
    "fewshot_examples": [{"input": "单语示例输入", "output": [{"term": "示例", "category": "人名"}]}],
    "fewshot_examples_bilingual": [{"input": "ZH: 双语示例 | EN: Bilingual sample",
                                    "output": [{"zh_term": "双语示例", "eng_term": "Bilingual sample", "category": "技能"}]}],
}

# translation_rules injection
sp, up = build_translation_prompt(PROFILE, [{"term": "八荒剑诀", "source_text": "x", "_ref_term": "r", "_ref_trans": "R"}])
check("translation_rules appear in user prompt", "翻译风格规则（必须遵守）" in up and "角色名 → 音译（拼音）" in up)
check("rules absent when profile has none", "翻译风格规则" not in build_translation_prompt({"game_type": "g"}, [])[1])

# bilingual few-shot preference
up_bi = build_user_prompt(PROFILE, "[1] ZH: a | EN: b", include_context=False, bilingual=True)
up_mono = build_user_prompt(PROFILE, "[1] a", include_context=False, bilingual=False)
check("bilingual mode uses bilingual few-shot", "双语示例" in up_bi and "单语示例输入" not in up_bi)
check("mono mode uses mono few-shot", "单语示例输入" in up_mono and "双语示例" not in up_mono)
no_bi = {k: v for k, v in PROFILE.items() if k != "fewshot_examples_bilingual"}
check("bilingual falls back to mono few-shot when variant absent",
      "单语示例输入" in build_user_prompt(no_bi, "[1] ZH: a | EN: b", include_context=False, bilingual=True))

# term_corrections override
items = [
    {"term": "墨门", "translation": "Mo Sect", "match_type": "llm_translated"},
    {"term": "墨门弟子", "translation": "Disciple", "match_type": "exact"},
    {"term": "墨门", "translation": "Momen", "match_type": "exact"},
]
out = _apply_term_corrections(items, PROFILE)
check("wrong translation overridden + marked corrected", out[0]["translation"] == "Momen" and out[0]["match_type"] == "corrected")
check("non-listed term untouched", out[1]["translation"] == "Disciple" and out[1]["match_type"] == "exact")
check("already-correct translation not re-marked", out[2]["match_type"] == "exact")
check("no corrections -> passthrough", _apply_term_corrections([{"term": "x", "translation": "y"}], {"game_type": "g"})[0]["translation"] == "y")

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if n == len(results) else 1)
