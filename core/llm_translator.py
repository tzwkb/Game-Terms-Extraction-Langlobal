#!/usr/bin/env python3
import asyncio, logging
from typing import Dict, Optional

from openai import AsyncOpenAI
from config import TRANSLATOR_CONFIG
from core.json_util import extract_json
from core.retry import retry_async


class TermTranslator:

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o", profile: Optional[Dict] = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=TRANSLATOR_CONFIG["timeout"], max_retries=TRANSLATOR_CONFIG["max_retries"])
        self.model = model
        self.profile = profile or {}
        self.logger = logging.getLogger("pipeline")

    async def _call_one(self, system_prompt: str, user_prompt: str, tag: str = "") -> str:
        async def _req():
            return await self.client.chat.completions.create(
                model=self.model, temperature=TRANSLATOR_CONFIG["temperature"], max_tokens=TRANSLATOR_CONFIG["max_tokens"],
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            )
        try:
            response = await retry_async(_req, max_attempts=10, initial_delay=10.0,
                                         delay_multiplier=1.5, tag=f"[translate]{tag}")
            tokens = response.usage.total_tokens if response.usage else 0
            self.logger.info(f"[translate]{tag} done, {tokens} tokens")
            return response.choices[0].message.content
        except Exception:
            self.logger.error(f"[translate]{tag} failed after 10 attempts")
            return ""

    @staticmethod
    def _parse(raw: str) -> Dict[str, str]:
        data = extract_json(raw)
        if data and isinstance(data, dict):
            return {item["term"]: item["translation"]
                    for item in data.get("translations", [])}
        return {}

    def translate_batches(self, prompts: list, concurrent: int = None) -> Dict[str, str]:
        if concurrent is None:
            concurrent = TRANSLATOR_CONFIG["max_concurrent"]
        self.logger.info(f"[translate] {len(prompts)} batches, concurrent={concurrent}")

        async def _run():
            sem = asyncio.Semaphore(concurrent)
            async def _one(i, sp, up):
                async with sem:
                    return await self._call_one(sp, up, tag=f" b{i+1}/{len(prompts)}")
            return await asyncio.gather(*[_one(i, sp, up) for i, (sp, up) in enumerate(prompts)])

        raws = asyncio.run(_run())
        merged = {}
        for raw in raws:
            merged.update(self._parse(raw))
        self.logger.info(f"[translate] merged {len(merged)} translations from {len(prompts)} batches")
        return merged
