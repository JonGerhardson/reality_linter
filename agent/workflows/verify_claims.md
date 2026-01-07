---
description: Verify citations in reports using multi-model consensus (local + Gemini LLMs).
---

# Verify Claims

Verify all citations in a report using the **Judge** verification engine.

## Quick Start

```bash
// turbo
python scripts/verify_report.py reports/<report_name>.md
```

## What It Does

1. **Parses** the markdown report for citations `[file:Lxxxx](path)`
2. **Checks** each citation against source files in `data/canonical/`
3. **Runs LLM** semantic analysis (local + Gemini consensus)
4. **Generates** read-only verification report

## Output

- **Location:** `reports/verification_reports/verification_<report>.md`
- **Logs:** `debug_output/llm_logs/<report>/` (gemini_0001.txt, local_0001.txt, etc.)

## Verdicts

| Verdict | Meaning |
|---------|---------|
| VALID | Quote is substantive, in-context, supports the claim |
| MISLEADING | Quote exists but context changes meaning |
| INSUFFICIENT | Quote too short (<5 words) or generic |
| UNSUPPORTED | Quote doesn't logically support the claim |
| QUOTE_NOT_FOUND | Quote text not found in cited lines (low match score) |

## CLI Options

```bash
python scripts/verify_report.py <report.md> [options]

Options:
  --canonical-dir PATH   Path to canonical data (default: data/canonical)
  --output PATH          Custom output path (default: auto-generated)
  --json                 Also output JSON to stdout
```

## Manual Single-Claim Verification

```bash
python -m research_engine.judge "CLAIM" "QUOTE" "FILENAME" START END
```

Example:
```bash
python -m research_engine.judge \
  "SCEs must select one of three license classes" \
  "permitted to select one of the following classes" \
  "ocm04109606_baked.txt" 13294 13296
```
