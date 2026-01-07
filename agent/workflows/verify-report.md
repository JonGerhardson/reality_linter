---
description: Run citation verification on a report and review results with user
---

# Verify report citations

This workflow verifies all citations in a markdown report against source documents.

> [!IMPORTANT]
> This is a **human-in-the-loop** checkpoint. After running verification, you MUST stop and present results to the user. Do NOT proceed with edits until the user has reviewed the verification report and provided feedback.

## Steps

### 1. Run the verifier

// turbo
```bash
source .venv/bin/activate && python scripts/verify_report.py reports/<report_name>.md
```

The script will:
- Extract all citations from the report
- Verify each claim against its cited source
- Generate a verification report at `reports/verification_reports/verification_<report_name>.md`
- Make the verification report **read-only** for audit trail integrity

### 2. Present results to user

After verification completes:
1. Report the verification rate (e.g., "15/22 citations verified (68%)")
2. Summarize categories of issues found (wrong line numbers, unsupported claims, etc.)
3. Ask user to review the full verification report
4. **STOP and wait for user feedback**

Do NOT proceed with edits until the user has reviewed the verification report.

### 3. Address issues (after user review)

Only after user has reviewed the verification report and provided direction:
- Fix incorrect line numbers in citations
- Add missing citations for unsupported claims
- Reword claims that misrepresent sources
- Remove claims that cannot be verified from available sources

### 4. Re-run verification (user will run manually)

The user will run verification again after edits to confirm improvements.

## Interpreting verdicts

| Verdict | Meaning | Action |
|---------|---------|--------|
| VALID | Source supports the claim | None needed |
| INSUFFICIENT | Source text too limited | Check if line number is wrong; expand citation range |
| UNSUPPORTED | Source doesn't contain claimed info | Find correct source or remove claim |
| MISLEADING | Source contradicts the claim | Correct the claim to match source |
| QUOTE_NOT_FOUND | Claim text not found in source | Usually means wrong line number; search file for correct line |

## Common issues

**Wrong line number:** The cited line exists but doesn't contain the relevant text. Search the same file for the correct line.

**File not found:** The filename in the citation doesn't match any baked file. Check for typos or hash suffix differences.

**Fragment claim:** The extracted claim is a sentence fragment. The rolling context window should provide enough context, but if verification fails, consider rewriting for clarity.

**Table data:** If a table row fails verification, ensure the table header row is being captured. The verifier should automatically detect and include headers.

## How claims are extracted

The verifier extracts claims by:
1. Finding all citations in the document (pattern: `[filename:Lxxxx](path)`)
2. For each citation, extracting all text between it and the previous citation
3. Including a rolling context window (up to 200 characters from before the previous citation) to capture grammatical subjects
4. Including the current section header for context
5. Detecting and including table headers if the claim contains table data

This ensures every piece of information between citations is verified against the source.
