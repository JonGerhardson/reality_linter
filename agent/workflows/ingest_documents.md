---
description: Ingests raw documents (PDF, Audio, Text) from `raw_documents/` into the baked canonical dataset.
---

# Ingest Documents

This workflow triggers the ingestion pipeline to process files in the `raw_documents` directory.

## Prerequisites

Ensure required directories and database exist:

```bash
# // turbo
mkdir -p raw_documents database data/canonical
python -m research_engine.database
```

## Steps

1.  **Place Files**:
    *   Move new files (`.pdf`, `.mp3`, `.txt`, `.docx`, `.xlsx`) into `raw_documents/`.

2.  **Run Ingestion**:
    *   // turbo
    *   Command: `python -m research_engine.ingest raw_documents`
    *   For a single file: `python -m research_engine.ingest raw_documents/filename.pdf`
    *   **CRITICAL**: The "Baker" extracts **verbatim text**. Do NOT summarize or reformat.

3.  **Verify Output**:
    *   Check `data/canonical/` for new `*_baked.txt` or `*_extracted_baked.txt` files.
    *   Check `data/document_metadata.json` for updated entries.
    *   Confirm embeddings: `sqlite3 database/research.db "SELECT COUNT(*) FROM chunk_embeddings;"`

## Troubleshooting

*   **"unable to open database file"**: Run `mkdir -p database && python -m research_engine.database`
*   **"Already processed"**: Delete the existing `_baked.txt` file to reprocess
*   **OCR issues**: Ensure LM Studio is running at configured URL for VLM fallback
