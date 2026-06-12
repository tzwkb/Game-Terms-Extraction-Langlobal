#!/usr/bin/env python3
"""Verify profile wiring: translation_rules injection, bilingual few-shot
preference, and glossary-over-EN priority with conflict note (offline, no API)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.prompt_base import build_translation_prompt, build_user_prompt
from core.main import match_and_translate

results = []


def check(name, ok):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")


PROFILE = {
    "game_type": "武侠",
    "term_categories": ["人名", "技能"],
    "translation_rules": ["角色名 → 音译（拼音）", "技能名 → 意译"],
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

# glossary > bilingual copy, conflict noted
GLOSSARY = {"墨门": ("墨门", "Momen")}
extracted = [
    {"term": "墨门", "eng_term": "Mo Sect", "category": "门派"},
    {"term": "八荒剑诀", "eng_term": "Eight Wilds Sword Art", "category": "技能"},
]
out = match_and_translate([dict(t) for t in extracted], GLOSSARY, PROFILE, "", "", "m", bilingual=True)
by = {d["term"]: d for d in out}
check("glossary wins over EN column", by["墨门"]["translation"] == "Momen" and by["墨门"]["match_type"] == "exact")
check("conflict recorded in note", "Mo Sect" in by["墨门"].get("note", ""))
check("no glossary hit -> EN copied", by["八荒剑诀"]["translation"] == "Eight Wilds Sword Art" and by["八荒剑诀"]["match_type"] == "bilingual")
check("eng_term stripped from results", all("eng_term" not in d for d in out))
out2 = match_and_translate([{"term": "墨门", "eng_term": "Momen", "category": "门派"}], GLOSSARY, PROFILE, "", "", "m", bilingual=True)
check("EN agreeing with glossary -> no note", "note" not in out2[0])
out3 = match_and_translate([{"term": "墨门", "category": "门派"}], GLOSSARY, PROFILE, "", "", "m", bilingual=False)
check("mono mode exact match unchanged", out3[0]["translation"] == "Momen" and "note" not in out3[0])

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if n == len(results) else 1)
