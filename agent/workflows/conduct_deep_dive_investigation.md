---
description: Conduct a deep dive investigation by searching the corpus with specific queries.
---

# Conduct Deep Dive Investigation

This workflow uses the **Search Engine** to find evidence in ingested documents.

## Search modes

| Mode | Use When | Command |
|------|----------|---------|
| `bm25` | Known keywords, exact terms | `--mode bm25` |
| `hybrid` | Conceptual queries, related terms | `--mode hybrid` |
| `vector` | Pure semantic similarity | `--mode vector` |
| `exhaustive` | Need all matches, not ranked | `--exhaustive` |

## Steps

1.  **Define Query**:
    *   Identify key terms or entities to search for.
    *   Consider synonyms and related concepts for hybrid search.

2.  **Execute Search**:
    *   // turbo
    *   Command: `python -m research_engine.search_engine "YOUR QUERY" --mode hybrid`
    *   Output includes: filename, line number `[Lxxxx]`, match type, content preview.

3.  **Read Context**:
    *   For promising results, read surrounding lines:
    *   Command: `sed -n 'START,ENDp' data/canonical/FILENAME`
    *   Example: `sed -n '10630,10660p' data/canonical/doc_baked.txt`

4.  **Synthesize**:
    *   Compile findings into a report in `reports/`.
    *   **Citation format**: `[filename:Lxxxx](../data/canonical/filename#Lxxxx)`
    *   Every claim must have a linked citation, not just `[Lxxxx]`

## Notes

*   Hybrid search loads embedding model on first call (~5s on GPU)
*   Filenames may have `_extracted_` prefix for PDF-derived content
*   Results capped at 10 by default; adjust with `--top-k N`
