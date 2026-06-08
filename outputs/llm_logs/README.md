# `outputs/llm_logs/` — DeepSeek call audit trail

Every call made by `src/llm/deepseek_client.py::chat` / `reason`
(and their `safe_*` wrappers) writes a single timestamped JSON
file into this directory containing:

```jsonc
{
  "model":       "deepseek-chat" | "deepseek-reasoner",
  "temperature": 0.5,
  "system":      "…full system prompt…",
  "user":        "…full user prompt…",
  "response":    "…full assistant message…",
  "usage":       { "prompt_tokens": N, "completion_tokens": N, … }
}
```

Filename convention: `<tag>_<unix-ms>.json` (e.g.
`synth_fg_zscore_90_1717800123456.json`,
`report_1717800124567.json`,
`strategy_desc_FAIL_1717800125678.json`).

## Why this dir is committed empty

The dev doc (§7.1 + §8.5) requires "全量 prompt/response 落盘" —
every prompt and every response must be persisted so the
hallucination detector and human auditors can trace each number in
the final report back to the exact prompt that produced it.

The directory is committed via `.gitkeep` so that fresh clones get
a writable target; the actual `*.json` audit files are git-ignored
(see `.gitignore`) because they contain large prompt bodies and
can be regenerated deterministically by re-running:

```bash
python scripts/05_generate_spec.py    # per-factor synth + strategy_desc
python scripts/06_write_report.py     # full report draft
```

## What lives here after a successful pipeline run

- `synth_<factor_id>_*.json` — one file per FDR-significant factor
  (skipped when the FDR filter returns the empty set; both behaviours
  are honest and documented).
- `strategy_desc_*.json` — the 3-sentence top-level description.
- `report_*.json` — the full 8-chapter draft.
- `*_FAIL_*.json` — `safe_chat` / `safe_reason` failure envelopes
  with the captured exception, so judges can see when the LLM was
  unreachable and the deterministic template fallback was used.
