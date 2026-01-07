# Judge Verification Tool

The Judge is a multi-model citation verification system that validates claims against source documents.

## Overview

The Judge performs a 3-step verification process:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Step 1:        │ --> │  Step 2:        │ --> │  Step 3:        │
│  File Existence │     │  Text Matching  │     │  LLM Semantic   │
│  & Context      │     │  (Fuzzy)        │     │  Analysis       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Step 1: File existence and context retrieval

**Purpose:** Verify the cited file exists and extract text with surrounding context.

**Process:**
1. Load the baked file from `data/canonical/<filename>`
2. Extract the cited lines (e.g., L13326-L13328)
3. Fetch 5 lines **before** the cited range (context_before)
4. Fetch 5 lines **after** the cited range (context_after)

**Output:**
- `cited_text`: The exact lines cited
- `context_before`: 5 preceding lines
- `context_after`: 5 following lines
- `error`: Any file access errors

**Failure condition:** If file doesn't exist, return error immediately.

## Step 2: Text matching (fuzzy)

**Purpose:** Verify the claim text appears in the source document.

**Process:**
1. Combine `context_before + cited_text` into search area
2. Normalize both strings (lowercase, collapse whitespace, remove line tags)
3. Use `difflib.SequenceMatcher` to find longest common subsequence
4. Calculate score: `(longest match length) / (quote length)`

**Threshold:** 80% match required (configurable)

**Output:**
- `quote_match`: Boolean (passed threshold)
- `quote_score`: 0.0 to 1.0 (percentage match)

**Note:** Even if text matching fails, Step 3 still runs (for debugging). The final verdict will be `QUOTE_NOT_FOUND` but LLM analysis is logged.

## Step 3: LLM semantic analysis (The Jury)

**Purpose:** Determine if the source actually supports the claim semantically.

**Process:**
1. Build prompt with full context:
   ```
   SOURCE FILE: <filename>
   CITED LINES: L<start>-L<end>
   
   CONTEXT BEFORE:
   <5 lines before>
   
   CITED TEXT:
   <cited lines>
   
   CONTEXT AFTER:
   <5 lines after>
   
   CLAIM BEING MADE: <claim>
   QUOTE USED: <quote>
   ```

2. Send prompt to multiple LLMs (The Jury):
   - Local LLM (LM Studio/Ollama)
   - Gemini (gemma-3-27b-it)
   - OpenAI (gpt-4o-mini, if configured)

3. Each LLM answers:
   - Is the quote substantive (≥5 words)?
   - Is the quote in-context (not from hypothetical/opponent)?
   - Does the source support the claim?

4. Consensus voting:
   - If all agree → that verdict wins
   - If majority agrees → majority wins
   - If tie (e.g., 1 VALID, 1 INSUFFICIENT) → `HUNG_JURY`

**LLM verdicts:**

| Verdict | Meaning |
|---------|---------|
| `VALID` | Quote is substantive, in-context, and supports the claim |
| `MISLEADING` | Quote exists but context changes its meaning |
| `INSUFFICIENT` | Quote too short (<5 words) or too generic |
| `UNSUPPORTED` | Quote doesn't logically support the claim |

## Error handling

**LLM errors:**
- If one LLM fails but others succeed: Use remaining valid responses
- If all LLMs fail: Return `LLM_ERROR`

**File errors:**
- Missing file: Return immediately with error

**Rate limits:**
- Gemini has 20 requests/day on free tier
- Errors are logged but don't block other LLMs

## Output structure

```json
{
  "step_1_existence": true,
  "step_2_quote_match": true,
  "quote_score": 0.85,
  "step_3_semantic": {
    "verdict": "VALID",
    "substantive_quote": true,
    "quote_in_context": true,
    "supports_claim": true,
    "reason": "Consensus (2/2): VALID: The quote directly..."
  },
  "verdict": "VALID",
  "verified": true,
  "text_found": "[L13326] The Marijuana Event Organizer..."
}
```

## Logging

All LLM prompts and responses are logged to:
```
debug_output/llm_logs/<report_name>/
  ├── gemini_0001.txt
  ├── local_0001.txt
  ├── gemini_0002.txt
  ├── local_0002.txt
  └── ...
```

Each log file contains:
```
=== PROMPT ===
<full prompt sent to LLM>

=== RESPONSE ===
<raw JSON response or error>
```

## Batch verification (verify_report.py)

The `verify_report.py` script automates verification for all citations in a report:

1. **Parse report:** Extract all `[file:Lxxxx](path)` citations
2. **For each citation:**
   - Extract claim text (sentence before citation)
   - Find matching baked file in `data/canonical/`
   - Call `judge.verify_claim()` with citation index
3. **Generate report:** Write to `reports/verification_reports/` (read-only)
4. **Summary:** Count verdicts, calculate verification rate

## CLI usage

**Single claim:**
```bash
python -m research_engine.judge \
  "CLAIM_TEXT" \
  "QUOTE_TEXT" \
  "FILENAME" \
  START_LINE \
  END_LINE
```

**Batch verification:**
```bash
python scripts/verify_report.py reports/<report>.md
```

## Configuration

**Environment variables:**
- `OPENAI_API_KEY`: Enable OpenAI as third LLM
- `GOOGLE_API_KEY`: Enable Gemini
- `LOCAL_LLM_BASE_URL`: Local LLM endpoint (default: `http://localhost:1234/v1`)

**Thresholds:**
- Text match: 80% (in `_check_quote_match`)
- Context lines: 5 before/after (in `_read_lines_with_context`)
