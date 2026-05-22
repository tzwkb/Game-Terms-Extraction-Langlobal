#!/usr/bin/env python3

import asyncio
import json
import re
import time
import logging
import threading
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI
from config import EXTRACTOR_CONFIG, get_token_param_name

class LLMExtractor:

    def __init__(self, api_key: str, base_url: str='https://api.openai.com/v1', base_dir: str='output', cache_dir: str=''):
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=EXTRACTOR_CONFIG["timeout"], max_retries=EXTRACTOR_CONFIG["max_retries"])
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        session_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._exchange_log_file = self.base_dir / f'api_log_{session_ts}.jsonl'
        self._log_fh = open(self._exchange_log_file, 'a', encoding='utf-8')
        self._log_lock = threading.Lock()
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self.logger = logging.getLogger('pipeline')

    def _log_exchange(self, custom_id: str, messages: list, raw_content: str, usage: dict, model: str) -> None:
        entry = {'timestamp': datetime.now().isoformat(), 'custom_id': custom_id, 'model': model, 'messages': messages, 'response': raw_content, 'usage': usage}
        with self._log_lock:
            self._log_fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
            self._log_fh.flush()

    def _cache_path(self, custom_id: str) -> Path:
        return self._cache_dir / f'{custom_id}.json'

    def _load_cache(self, custom_id: str) -> Optional[Dict[str, Any]]:
        if self._cache_dir is None:
            return None
        p = self._cache_path(custom_id)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                if data.get('custom_id') == custom_id:
                    self.logger.info(f'[{custom_id}] cache hit')
                    return data
            except Exception:
                pass
        return None

    def _save_cache(self, custom_id: str, result: Dict[str, Any]):
        if self._cache_dir is None:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path(custom_id).write_text(json.dumps(result, ensure_ascii=False, default=str), encoding='utf-8')
        except Exception as e:
            self.logger.warning(f'[{custom_id}] cache save failed: {e}')

    async def _process_single_text_async(self, text: str, custom_id: str, semaphore: asyncio.Semaphore, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int, source_file: str) -> Dict[str, Any]:
        cached = self._load_cache(custom_id)
        if cached is not None:
            return cached
        async with semaphore:
            api_params = self._build_api_params(system_prompt, user_prompt, model, temperature, max_tokens)
            self.logger.info(f'[{custom_id}] input={len(system_prompt)+len(user_prompt)} chars')
            attempt = 0
            delay = 5.0
            max_attempts = 5
            while True:
                attempt += 1
                try:
                    response = await self.async_client.chat.completions.create(**api_params)
                    try:
                        raw_content = response.choices[0].message.content
                        raw_usage = {'total_tokens': response.usage.total_tokens if response.usage else 0, 'prompt_tokens': response.usage.prompt_tokens if response.usage else 0, 'completion_tokens': response.usage.completion_tokens if response.usage else 0}
                    except Exception:
                        raw_content = str(response)
                        raw_usage = {}
                    self._log_exchange(custom_id, api_params['messages'], raw_content, raw_usage, model)
                    result = self._process_api_response(response, custom_id, model, source_file)
                    self._save_cache(custom_id, result)
                    return result
                except Exception as e:
                    if attempt >= max_attempts:
                        self.logger.error(f'[{custom_id}] failed after {max_attempts} attempts: {type(e).__name__}: {str(e)[:120]}')
                        return self._create_error_result(custom_id, model, source_file, f'{type(e).__name__}: {str(e)}')
                    self.logger.warning(f'[{custom_id}] retry#{attempt} {type(e).__name__}: {str(e)[:120]}, retry in {delay:.0f}s')
                    self.logger.debug(traceback.format_exc())
                    import random
                    jitter = random.uniform(0, delay * 0.5)
                    await asyncio.sleep(delay + jitter)
                    delay = min(delay * 2, 120.0)

    def _build_api_params(self, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
        api_params = {'model': model, 'messages': [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}], 'temperature': temperature}
        token_param = get_token_param_name(model)
        api_params[token_param] = max_tokens
        return api_params

    def _process_api_response(self, response, custom_id: str, model: str, source_file: str) -> Dict[str, Any]:
        try:
            content = response.choices[0].message.content
            usage_info = {
                'total_tokens': response.usage.total_tokens if response.usage else 0,
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
            }
            self.logger.debug(f'[{custom_id}] raw: {content[:200]}')
            extracted_terms = self._parse_json_response(content)
            result = {'custom_id': custom_id, 'extracted_terms': extracted_terms, 'usage': usage_info, 'model': response.model, 'source_file': source_file, 'created': int(time.time())}
            self.logger.info(f'[{custom_id}] done, {usage_info["total_tokens"]} tokens')
            return result
        except Exception as e:
            self.logger.error(f'[{custom_id}] response error: {type(e).__name__}: {str(e)}')
            self.logger.debug(traceback.format_exc())
            return self._create_error_result(custom_id, model, source_file, f'{type(e).__name__}: {str(e)}')

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        stripped = content.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            return self._validate_parsed_json(parsed)
        except json.JSONDecodeError:
            pass
        md_match = re.search('```(?:json)?\\s*\n([\\s\\S]*?)\n\\s*```', content)
        if md_match:
            candidate = md_match.group(1).strip()
            try:
                parsed = json.loads(candidate)
                return self._validate_parsed_json(parsed)
            except json.JSONDecodeError:
                pass
        json_start = stripped.find('{')
        if json_start == -1:
            json_start = stripped.find('[')
        if json_start != -1:
            end_char = '}' if stripped[json_start] == '{' else ']'
            json_end = stripped.rfind(end_char)
            if json_end > json_start:
                try:
                    parsed = json.loads(stripped[json_start:json_end + 1])
                    return self._validate_parsed_json(parsed)
                except json.JSONDecodeError:
                    pass
        self.logger.error(f'json_parse_failed: {content[:200]}')
        return {'raw_content': content}

    def _validate_parsed_json(self, parsed: Any) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            self.logger.warning(f'non-dict response: {type(parsed)}')
            return {'raw_content': str(parsed)}
        if 'terms' not in parsed:
            if len(parsed) == 1:
                single_key, single_val = next(iter(parsed.items()))
                if isinstance(single_val, list):
                    self.logger.info(f"using '{single_key}' as terms")
                    return {'terms': single_val}
            self.logger.warning(f"missing 'terms', got keys: {list(parsed.keys())}")
            return {'raw_content': str(parsed)}
        return parsed

    def _create_error_result(self, custom_id: str, model: str, source_file: str, error_msg: str) -> Dict[str, Any]:
        return {'custom_id': custom_id, 'error': error_msg, 'extracted_terms': {'raw_content': str(error_msg)}, 'usage': {'total_tokens': 0}, 'model': model, 'source_file': source_file, 'created': int(time.time())}

    async def run_batch_async(self, texts: List[str], system_prompt: str, user_prompts: List[str], model: str, temperature: float, max_tokens: int, max_concurrent: int, source_files: List[str], batch_id: str = '', progress: callable = None) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        for i, text in enumerate(texts):
            custom_id = f'{batch_id}_t{i}' if batch_id else f'term-extraction-{i + 1}'
            source_file = source_files[i] if source_files and i < len(source_files) else ''
            user_prompt = user_prompts[i] if user_prompts and i < len(user_prompts) else ''
            tasks.append(self._process_single_text_async(text=text, custom_id=custom_id, semaphore=semaphore, system_prompt=system_prompt, user_prompt=user_prompt, model=model, temperature=temperature, max_tokens=max_tokens, source_file=source_file))
        total = len(tasks)
        results: List[Dict[str, Any]] = []
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            result = await coro
            results.append(result)
            self.logger.info(f'[{i}/{total}] done')
            if progress:
                progress(i, total)
        return results

    def process_batch_concurrent(self, texts: List[str], system_prompt: str=None, user_prompts: List[str]=None, model: str='gpt-4-turbo-preview', temperature: float=0.1, max_tokens: int=4096, max_concurrent: int=10, source_files: List[str]=None, batch_id: str='') -> List[Dict[str, Any]]:
        if not texts:
            return []
        max_concurrent = min(max_concurrent, len(texts))
        self.logger.info(f'batch_start: texts={len(texts)} concurrent={max_concurrent}')
        results = asyncio.run(self.run_batch_async(texts=texts, system_prompt=system_prompt, user_prompts=user_prompts or [], model=model, temperature=temperature, max_tokens=max_tokens, max_concurrent=max_concurrent, source_files=source_files or [], batch_id=batch_id))
        results.sort(key=lambda x: x.get('custom_id', ''))
        self.logger.info(f'batch_done: {len(results)} results')
        return results
