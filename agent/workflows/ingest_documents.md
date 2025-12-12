---
description: Ingests raw documents (PDF, Audio, Text) from `raw_documents/` into the baked canonical dataset.
---

# Ingest Documents

This workflow triggers the "Baker", "Seer" (OCR), and "Listener" (Audio) pipelines to process new files in the `raw_documents` directory.

1.  **Check for New Files**:
    *   Ensure you have placed your new files (`.pdf`, `.mp3`, `.txt`) into `raw_documents/`.

2.  **Run Ingestion**:
    *   Executes the multimodal ingestion script.
    *   // turbo
    *   Command: `python -m research_engine.ingest raw_documents`
    *   **CRITICAL**: The "Baker" process must extract **verbatim text**. DO NOT summarize, paraphrase, or reformat the content. The goal is a line-by-line accessible copy of the original.

3.  **Verify Output**:
    *   Check `data/canonical/` for new `_baked.txt` files.
    *   Check `data/document_metadata.json` for updated entries.
