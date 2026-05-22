# Changelog

## [Unreleased] — 2026-04-13

### Added
- **Profile system** (`profiles/` package): game-specific content is now isolated in per-game profile modules. Switching projects requires changing one import line in `main.py`.
- `profiles/wuxia.py` — classic wuxia martial arts profile (migrated from hardcoded config)
- `profiles/neoepoch.py` — Neoepoch — The Gloam (modern urban supernatural visual novel, SEA setting). Includes `EXTRACTION_NOTES` with mandatory term replacements, faction singular/plural rules, and professional jargon guidance; `TERM_CORRECTIONS` dict for post-processing validation (30 entries).
- `profiles/fantasy_rpg.py` — fantasy RPG template
- `profiles/sci_fi.py` — sci-fi shooter template
- `prompt_base.py` — generic prompt scaffolding (`build_system_prompt`, `build_user_prompt`). All game-specific content injected via profile; no hardcoded game text.
- `config.init_profile(game_profile)` — initializes module-level caches (O(1) tier lookup table, `TERM_PROCESSING` quality-control lists) from the active profile. Must be called once after importing the profile in `main.py`.

### Changed
- `config.py`: removed all hardcoded game content (wuxia categories, tier mappings, professional indicators). Now a pure engine config.
- `config.get_tier_by_content()`: replaced per-call linear scan with O(1) dict lookup via `_CATEGORY_TO_TIER` reverse map.
- `main.py`: profile import at top; `config.init_profile()` called immediately after; `SYSTEM_PROMPT` built once from profile.
- `prompt_base.build_user_prompt()`: priority description text generalized (removed wuxia-specific examples).
- `main.py`: removed zombie `bilingual` parameter from `run_batch_processing` and `select_extraction_mode`.
- `main.py`: extracted duplicate file-selection input loop into `_prompt_file_choice()` helper.
- `main.py`: `_scan_other_locations` uses single `iterdir()` pass with `frozenset` suffix check instead of 7 separate `glob()` calls.
- `main.py`: `_add_file_labels` hoists invariant `len(texts) > 1` check outside loop; rewritten as list comprehension.
- `main.py`: `_extract_source_files` uses module-level compiled regex `_SOURCE_FILE_RE`; `import re` moved to top of file.
- `main.py`: `_SUPPORTED_EXTENSIONS` and `_SUPPORTED_SUFFIXES` extracted as module-level constants (was duplicated in two methods).
- `config.py`: removed dead `@property _system_prompt_compat` (module-level `@property` has no effect in Python).
- `config.py`: removed `get_system_prompt()`, `get_user_prompt()`, `_load_profile_lists()` — all replaced by `init_profile()` + direct `prompt_base` calls.
- `config.py`: removed duplicate `# 术语处理配置` section header.
- `config.py`: `validate_config()` batch key check simplified to `all(k in BATCH_CONFIG for k in ...)`.
- `config.py`: `TOKEN_PARAM_NAME` constant added; `get_token_param_name()` now returns it directly.

### Fixed
- `main.py`: `_cfg.INCLUDE_CONTEXT` in `run_batch_processing()` was a `NameError` at runtime (`_cfg` was defined in `run()` scope only). Fixed by using `config.INCLUDE_CONTEXT` directly.
- `main.py`: `_run_non_interactive_mode` passed `args.format` as the `model` argument and `model` as `bilingual`. Fixed argument order.
- `main.py`: duplicate step label "3." in `run()` — renumbered sequentially.
