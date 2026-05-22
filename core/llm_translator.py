#!/usr/bin/env python3
import asyncio, json, re, logging
from typing import Dict, Optional

from openai import AsyncOpenAI
from config import TRANSLATOR_CONFIG


class TermTranslator:

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o", profile: Optional[Dict] = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=TRANSLATOR_CONFIG["timeout"], max_retries=TRANSLATOR_CONFIG["max_retries"])
        self.model = model
        self.profile = profile or {}
        self.logger = logging.getLogger("pipeline")

    def translate_with_hints(self, system_prompt: str, user_prompt: str) -> Dict[str, str]:
        self.logger.info(f"[translate] input={len(system_prompt) + len(user_prompt)} chars")
        async def _call():
            attempt = 0
            delay = 10.0
            max_attempts = 10
            while True:
                attempt += 1
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model, temperature=TRANSLATOR_CONFIG["temperature"], max_tokens=TRANSLATOR_CONFIG["max_tokens"],
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    )
                    tokens = response.usage.total_tokens if response.usage else 0
                    self.logger.info(f"[translate] done, {tokens} tokens")
                    return response.choices[0].message.content
                except Exception as e:
                    if attempt >= max_attempts:
                        self.logger.error(f"[translate] failed after {max_attempts} attempts")
                        raise
                    self.logger.warning(f"[translate] retry#{attempt} {type(e).__name__}: {str(e)[:120]}, retry in {delay:.0f}s")
                    await asyncio.sleep(delay)
                    import random
                    delay = min(delay * 1.5 + random.uniform(0, 5), 120.0)

        raw = asyncio.run(_call())
        trans_map = {}
        try:
            data = json.loads(raw)
            for item in data.get("translations", []):
                trans_map[item["term"]] = item["translation"]
        except (json.JSONDecodeError, KeyError):
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group())
                    for item in data.get("translations", []):
                        trans_map[item["term"]] = item["translation"]
                except (json.JSONDecodeError, KeyError):
                    pass
        return trans_map
