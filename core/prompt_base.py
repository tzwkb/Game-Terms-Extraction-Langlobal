#!/usr/bin/env python3

import json
from typing import Dict, Any


def build_system_prompt(profile: Dict[str, Any]) -> str:
    game_type = profile.get("game_type", "游戏")
    ex = profile.get("extract_examples", {})
    include_lines = "\n".join(ex.get("include", []))
    exclude_lines = "\n".join(ex.get("exclude", []))
    principle = profile.get("core_principle", "")

    exclude_section = f"\n\n❌ 不提取：\n{exclude_lines}" if exclude_lines else ""

    return f"""\
你是一位专业的{game_type}游戏本地化术语抽取专家。你的任务是从游戏文本中识别并提取需要本地化处理的专业术语。

{principle}

【提取范围】

✅ 提取：
{include_lines}{exclude_section}

请严格按照要求的 JSON 格式输出，不要添加任何额外文字。"""


def _build_rules(profile: Dict[str, Any]) -> str:
    cats = "、".join(profile.get("term_categories", []))
    lead = (f"只提取以下类型的游戏专有名词：{cats}" if cats
            else "提取游戏专有名词：人名、地名、物品名、技能名、机构名、事件名、称谓")
    notes = profile.get("extraction_notes", [])
    rules = [lead] + notes
    return "提取规则：\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))


def _build_ner_hint(ner_hints: dict) -> str:
    if not ner_hints:
        return ""
    persons = ner_hints.get("persons", [])
    places = ner_hints.get("places", [])
    if not persons and not places:
        return ""
    lines = "【预识别命名实体】以下人名和地名已确认出现在上述文本中，必须逐一检查并提炼为术语（请按上方给定的术语分类归类）：\n"
    if persons:
        lines += f"人名（{len(persons)}个）：{'、'.join(persons)}\n"
    if places:
        lines += f"地名（{len(places)}个）：{'、'.join(places)}\n"
    return lines


def build_user_prompt(
    profile: Dict[str, Any],
    text: str,
    include_context: bool = True,
    bilingual: bool = False,
    jieba_hints: list = None,
    ner_hints: dict = None,
) -> str:
    fewshot = profile.get("fewshot_examples", [])
    if fewshot:
        def _fmt_output(out):
            if isinstance(out, list):
                return json.dumps({"terms": out}, ensure_ascii=False)
            return out
        fewshot_rule = "\n\n【Few-Shot 示例】\n" + "\n".join(
            f"输入：{ex['input']}\n输出：{_fmt_output(ex['output'])}" for ex in fewshot
        )
    else:
        fewshot_rule = ""
    categories_str = "、".join(profile.get("term_categories", []))

    if bilingual:
        term_field_1 = '"zh_term": "中文术语", "eng_term": "必须原文照抄EN字段中对应的英文"'
        term_field_2 = '"zh_term": "另一个术语", "eng_term": "Copy exact English from EN field"'
    else:
        term_field_1 = '"term": "术语名称"'
        term_field_2 = '"term": "另一个术语"'

    if include_context:
        context_field = ', "context": "原文（≤20字）"'
    else:
        context_field = ""

    common_fields = f'"category": "分类"{context_field}'

    next_step = 5
    if bilingual:
        bilingual_rule = (
            f"\n{next_step}. 每条文本格式为 \"ZH: 中文 | EN: 英文\"，"
            "zh_term 取 ZH 部分识别出的术语，eng_term 必须原文照抄该术语在 EN 部分对应的英文单词/短语，"
            "严禁使用 EN 字段以外的任何英文（包括你自己的知识库、其他行的内容）"
        )
        next_step += 1
    else:
        bilingual_rule = ""

    if include_context:
        context_rule = f"\n{next_step}. context 填写术语所在的原始文本，最多 20 个汉字，超出截断"
    else:
        context_rule = ""

    if bilingual:
        task_desc = (
            "任务：从以下游戏文本条目中提取需要本地化的专业术语。\n\n"
            "文本条目格式为\"[序号] ZH: 中文内容 | EN: 英文内容\"，"
            "请从 ZH 部分识别术语，eng_term 必须原文照抄该条目 EN 部分中对应的英文，"
            "绝对禁止使用 EN 字段以外的英文（包括你的知识库、其他条目、历史翻译）。\n\n"
        )
    else:
        task_desc = (
            "任务：从以下游戏文本条目中提取需要本地化的专业术语。\n\n"
            "文本条目格式为\"[序号] 文本内容\"，请从\"文本内容\"部分提取术语。\n\n"
        )

    return (
        "你的回复必须只包含一个 JSON 对象，不得有任何额外文字。\n\n"
        + task_desc
        + "术语分类（必须从以下分类中选择一个）：\n"
        + f"{categories_str}\n\n"
        + _build_rules(profile)
        + bilingual_rule
        + context_rule
        + fewshot_rule + "\n\n"
        + "输出格式（JSON）：\n"
        + "{{\n"
        + '  "terms": [\n'
        + f'    {{{term_field_1}, {common_fields}}},\n'
        + f'    {{{term_field_2}, {common_fields}}}\n'
        + "  ]\n"
        + "}}\n\n"
        + _build_ner_hint(ner_hints)
        + (f"【术语表命中（以下词在术语库中存在，请判断是否在此语境中是术语）】\n{'、'.join(jieba_hints)}\n\n" if jieba_hints else "")
        + "待分析游戏文本条目：\n"
        + f"{text}\n"
    )


def build_translation_prompt(profile, terms_with_ref: list) -> tuple:
    hints = "\n".join(
        f"- {t['term']}  |  中文语境: {t.get('source_text', '')}  |  术语库参考: {t['_ref_term']} → {t['_ref_trans']}"
        for t in terms_with_ref
    )
    game_type = profile.get("game_type", "游戏")
    system = f"你是一位专业的{game_type}本地化翻译专家。"
    user = f"""你是游戏本地化翻译专家。将以下中文游戏术语翻译成英文。

术语库参考译文仅供参考，请以原文语境为准做出最佳翻译。

严格按 JSON 格式输出，不要任何额外文字：
{{"translations": [{{"term": "中文术语", "translation": "英文译文"}}, ...]}}

{hints}"""
    return system, user
