# Design Doc

## Architecture

```
config.py
  ├── logger.py
  ├── prompt_base.py            # LLM prompts (extraction + translation)
  ├── embed_store.py            # BGE-M3 + SQLite embedding store
  ├── profiles/*.yaml           # game_type, tiers, categories, rule_extractors
  │
main.py (orchestrator)
  ├── extract_terms()           → LLM 3-vote + hint providers
  ├── match_and_translate()     → glossary lookup + embedding match + LLM translate
  └── run_pipeline()            → full flow

eval.py
  └── run_pipeline → compare vs 人工术语表 + 全量术语表
```

## Modules

| Module | Role |
|--------|------|
| `config.py` | EXTRACTOR_CONFIG, VOTE_TEMPS, get_token_param_name |
| `logger.py` | logging setup |
| `prompt_base.py` | system prompt, user prompt (with hints), translation prompt |
| `embed_store.py` | BGE-M3 local model, SQLite persistence, cosine search |
| `llm_extractor.py` | async LLM batch calls with retry + cache |
| `llm_translator.py` | LLM batch translation with hints |
| `checkpoint.py` | save/resume/clear chunk-level progress |
| `main.py` | pipeline orchestrator |
| `eval.py` | benchmark vs manual + glossary |

## Term Extraction Flow

```
原文.xlsx
  ├─ dedup → chunk (~1200 chars, overlap=3 lines)
  │
  ├─ Per batch (10 chunks):
  │
  │   3 hint sources (all per-chunk filtered):
  │   ┌────────────────────────────────────────────────┐
  │   │ a) jieba × glossary (jieba_hints)              │
  │   │ b) Flash NER async x10 (ner_hints: persons +   │
  │   │    places, substring-filtered per chunk)        │
  │   │ c) _rule_extract: jieba + 百家姓 2-3 char      │
  │   │    tokens → merged into ner_hints persons       │
  │   └────────────────────────────────────────────────┘
  │         │
  │         ▼
  │   LLM 3-vote (t=0, 0.3, 0.7)
  │   pure LLM voting, no external votes
  │   threshold: ≥3 votes OR (2 votes + high priority)
  │
  ├─ dedup + match_context → extracted terms
```

## Match & Translate Flow

```
extracted terms
  ├── glossary exact match → direct translation (52%)
  └── no match:
        ├── BGE-M3 embedding search (database/glossary_embeddings.db)
        ├── top-1 reference term from glossary
        └── LLM translate with reference + source context
```

## Embedding Store

- Model: BAAI/bge-m3 (local, 1024-dim, normalized)
- Storage: `database/glossary_embeddings.db`
  - `embeddings`: term (TEXT PK), emb (BLOB), dim (INT)
  - `meta`: key-value (model path, etc.)
- First run: builds db from all glossary keys
- Subsequent runs: loads db, only encodes query terms

## Profile YAML

```yaml
game_type: string
core_principle: string           # extraction strategy
rule_extractors:                 # jieba surname-based person hints
  surname_names:
    surnames: "百家姓..."
    min_len: 2
    max_len: 3
tier_examples: {tier1, tier2, tier3}
fewshot_examples: [...]
term_categories: [...]
tier_mapping: {high, medium, low}
translation_rules: [...]
```

## Chunking

- target_chars=1200
- overlap=3 (last 3 lines repeat into next chunk)
- prevents term boundary loss

## Checkpoint

- Save: per 2 batches (chunk_idx + terms)
- Cache: per-chunk API response cache in checkpoint dir
- Clear: `shutil.rmtree` full directory
