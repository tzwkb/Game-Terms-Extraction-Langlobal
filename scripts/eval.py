#!/usr/bin/env python3
import os, sys, time, argparse
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from datetime import datetime
import pandas as pd

from core.checkpoint import task_id, clear as ckpt_clear

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.main import run_pipeline

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = "https://api.vectorengine.ai/v1"
MODEL = "claude-opus-4-7"
PROFILE = "yanyun"

T = ROOT / "test_file"

parser = argparse.ArgumentParser()
parser.add_argument("--source", default=str(T / "原文.xlsx"))
parser.add_argument("--manual", default=str(T / "人工术语_cleaned.xlsx"))
parser.add_argument("--profile", default=PROFILE)
args = parser.parse_args()

SOURCE = args.source
MANUAL = Path(args.manual)
PROFILE = args.profile
GLOSSARY = str(T / "【日更】0514术语表.xlsx")

t0 = time.time()
tid = task_id(SOURCE, PROFILE)
RUN_ID = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{PROFILE}"
CKPT = str(ROOT / "output" / "_checkpoints" / tid)
OUT = ROOT / "output" / "runs" / RUN_ID
OUT.mkdir(parents=True, exist_ok=True)

results = run_pipeline(SOURCE, GLOSSARY, PROFILE, API_KEY, BASE_URL, MODEL,
                       output_dir=str(OUT), checkpoint_dir=CKPT, raw_dir=str(OUT / "raw_data"))
ckpt_clear(CKPT)

df_man = pd.read_excel(MANUAL)
manual = {}
for _, row in df_man.iterrows():
    s = str(row[df_man.columns[0]]).strip()
    if s and s != "nan":
        manual[s.lower()] = s

ext_set = set(t["term"].lower() for t in results)
man_set = set(manual.keys())
tp = ext_set & man_set
fn = man_set - ext_set
fp = ext_set - man_set

p = len(tp) / len(ext_set) * 100 if ext_set else 0
r = len(tp) / len(man_set) * 100 if man_set else 0
f1 = 2 * p * r / (p + r) if p + r > 0 else 0

exact = sum(1 for t in results if t.get("match_type") == "exact")
hint = sum(1 for t in results if t.get("match_type") == "llm_translated")

# ===== Against full glossary =====
glossary_keys = set()
df_gl = pd.read_excel(GLOSSARY)
for _, row in df_gl.iterrows():
    k = str(row.iloc[0]).strip()
    if k and k != "nan":
        glossary_keys.add(k.lower())
gl_hit = ext_set & glossary_keys
gl_cov = len(gl_hit) / len(ext_set) * 100 if ext_set else 0

print(f"\n{'='*60}")
print(f"  vs 人工术语表 ({len(man_set)} terms)")
print(f"{'='*60}")
print(f"  Precision: {p:.1f}%  Recall: {r:.1f}%  F1: {f1:.1f}%")
print(f"  Hit: {len(tp)}  Missed: {len(fn)}  Noise: {len(fp)}")

print(f"\n{'='*60}")
print(f"  vs 全量术语表 ({len(glossary_keys)} terms)")
print(f"{'='*60}")
print(f"  Coverage: {gl_cov:.1f}% ({len(gl_hit)}/{len(ext_set)})")
print(f"  Exact match: {exact}  LLM translated: {hint}")

with open(OUT / "report.txt", "w", encoding="utf-8") as f:
    f.write(f"=== vs 人工术语表 ===\n")
    f.write(f"Precision: {p:.1f}% | Recall: {r:.1f}% | F1: {f1:.1f}%\n\n")
    f.write(f"HITS ({len(tp)}):\n")
    for t in sorted(tp):
        f.write(f"  {manual[t]}\n")
    f.write(f"\nMISSED ({len(fn)}):\n")
    for t in sorted(fn):
        f.write(f"  {manual[t]}\n")
    f.write(f"\nNOISE ({len(fp)}):\n")
    for t in sorted(fp):
        f.write(f"  {t}\n")
    f.write(f"\n=== vs 全量术语表 ===\n")
    f.write(f"Coverage: {gl_cov:.1f}% ({len(gl_hit)}/{len(ext_set)})\n")
    f.write(f"Exact match: {exact} | LLM translated: {hint}\n")

pd.DataFrame(results).to_excel(OUT / "results.xlsx", index=False)
print(f"Report: {OUT / 'report.txt'}")
print(f"Total: {(time.time()-t0)/60:.1f}m")
