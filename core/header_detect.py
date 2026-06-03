#!/usr/bin/env python3
"""Auto-detect Excel column roles via rules + AI fallback."""

import json
import re
from typing import Optional
import pandas as pd
from openai import OpenAI


def _headers_and_sample(df: pd.DataFrame, max_rows: int = 4) -> tuple:
    headers = list(df.columns)
    sample_rows = df.head(max_rows).values.tolist()
    # convert all cells to string
    sample_rows = [[str(c) if pd.notna(c) else "" for c in row] for row in sample_rows]
    return headers, sample_rows


# ── Rules-based detection ────────────────────────────────

_SRC_PATTERNS = [
    r"原文|文本|内容|source|text|content|zh|chinese|中文|日语|韩语|原文.*文本",
]
_CN_PATTERNS = [
    r"中文|chinese|cn|zh|术语|term|原文|source|zh.*cn|cn.*zh|chinese.*simplified|简中",
]
_EN_PATTERNS = [
    r"英文|english|en|翻译|translation|译文|译|target|en.*us|english.*us",
]


def _match(col_name: str, patterns: list) -> bool:
    name = str(col_name).lower().strip()
    for pat in patterns:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


def _rules_detect_source(df: pd.DataFrame) -> Optional[int]:
    headers, _ = _headers_and_sample(df)
    for i, h in enumerate(headers):
        if _match(h, _SRC_PATTERNS):
            return i
    # fallback: first text column
    for i in range(min(5, len(df.columns))):
        col = df.iloc[:, i].dropna().head(10)
        if col.apply(lambda x: isinstance(x, str) and len(str(x)) > 10).sum() >= 3:
            return i
    return None


def _rules_detect_glossary(df: pd.DataFrame) -> tuple:
    headers, _ = _headers_and_sample(df)
    cn_col, en_col = None, None
    for i, h in enumerate(headers):
        if _match(h, _CN_PATTERNS) and cn_col is None:
            cn_col = i
        elif _match(h, _EN_PATTERNS) and en_col is None:
            en_col = i
    if cn_col is None and len(headers) >= 1:
        cn_col = 0
    if en_col is None and len(headers) >= 2 and cn_col != 1:
        en_col = 1
    elif en_col is None and len(headers) >= 2:
        en_col = 1 if cn_col == 0 else 0
    return cn_col, en_col


# ── AI fallback ──────────────────────────────────────────

_DETECT_PROMPT = """你是一个数据分析助手。分析以下 Excel 表格的列名和样本数据，判断每一列的角色。

{context}

列名和样本数据:
{sample}

请只返回一个 JSON 对象，不要任何额外文字:
{output_format}"""


def _ai_detect(df: pd.DataFrame, api_key: str, base_url: str, file_type: str) -> dict:
    headers, sample_rows = _headers_and_sample(df, max_rows=3)
    sample_text = "列名: " + " | ".join(f"[{i}] {h}" for i, h in enumerate(headers)) + "\n"
    for ri, row in enumerate(sample_rows):
        sample_text += f"第{ri+1}行: " + " | ".join(f"[{i}] {cell}" for i, cell in enumerate(row)) + "\n"

    if file_type == "source":
        context = "这是一个游戏文本文件，需要找出哪一列包含**需要提取术语的原文文本**。"
        output_format = '{"text_col": <列索引数字>}'
    else:
        context = "这是一个游戏术语表文件，需要找出哪一列是**中文术语**，哪一列是**英文翻译**。"
        output_format = '{"cn_col": <列索引数字>, "en_col": <列索引数字>}'

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
    resp = client.chat.completions.create(
        model="gemini-3.1-flash-lite",
        messages=[{"role": "user", "content": _DETECT_PROMPT.format(
            context=context, sample=sample_text, output_format=output_format
        )}],
        temperature=0,
        max_tokens=256,
    )
    raw = resp.choices[0].message.content.strip()
    # extract JSON
    m = re.search(r"\{[^}]+\}", raw)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {}


# ── Public API ───────────────────────────────────────────

def detect_source_column(df: pd.DataFrame, api_key: str = "", base_url: str = "") -> dict:
    """Return {"text_col": int, "method": "rules"|"ai"|"default", "confidence": str}"""
    result = _rules_detect_source(df)
    if result is not None:
        return {"text_col": result, "method": "rules", "confidence": "高"}
    if api_key:
        ai = _ai_detect(df, api_key, base_url, "source")
        col = ai.get("text_col")
        if col is not None and 0 <= col < len(df.columns):
            return {"text_col": col, "method": "ai", "confidence": "中（AI 识别）"}
    return {"text_col": 0, "method": "default", "confidence": "低（默认第一列）"}


def detect_glossary_columns(df: pd.DataFrame, api_key: str = "", base_url: str = "") -> dict:
    """Return {"cn_col": int, "en_col": int, "method": str, "confidence": str}"""
    cn, en = _rules_detect_glossary(df)
    if cn is not None and en is not None and cn != en:
        return {"cn_col": cn, "en_col": en, "method": "rules", "confidence": "高"}
    if api_key:
        ai = _ai_detect(df, api_key, base_url, "glossary")
        ai_cn = ai.get("cn_col")
        ai_en = ai.get("en_col")
        if ai_cn is not None and ai_en is not None and ai_cn != ai_en \
           and 0 <= ai_cn < len(df.columns) and 0 <= ai_en < len(df.columns):
            return {"cn_col": ai_cn, "en_col": ai_en, "method": "ai", "confidence": "中（AI 识别）"}
    # fallback defaults
    n = len(df.columns)
    if n >= 2:
        return {"cn_col": 0, "en_col": 1, "method": "default", "confidence": "低（默认前两列）"}
    return {"cn_col": 0, "en_col": 0, "method": "default", "confidence": "低（仅一列）"}
