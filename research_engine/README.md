# Research Engine

An auditable RAG (Retrieval-Augmented Generation) system for investigative research. Documents are ingested, indexed for both keyword and semantic search, and findings can be verified against source material.

## Architecture overview

```
raw_documents/          # Input: PDFs, audio, text, spreadsheets
       ↓
    ingest.py           # Orchestrates all ingestion
       ↓
data/canonical/         # Output: _baked.txt files with [Lxxxx] line tags
       ↓
database/research.db    # FTS5 index + chunk embeddings
       ↓
search_engine.py        # Query interface (BM25, vector, hybrid)
       ↓
    judge.py            # Claim verification (3-step)
```

## File index

### Core configuration

| File | Purpose |
|------|---------|
| `config.py` | Paths (`DATA_DIR`, `CANONICAL_DIR`, `DB_PATH`) and API keys (OpenAI, Anthropic, Google, Local LLM). Reads from environment variables with fallback defaults. |
| `database.py` | SQLite schema and access functions. Tables: `topics`, `findings`, `verification_log`, `documents` (with FTS5 virtual table), `chunk_embeddings`. Provides `init_db()`, `insert_document_content()`, `insert_chunk_embedding()`, `get_all_embeddings()`. |

### Ingestion pipeline

| File | Purpose |
|------|---------|
| `ingest.py` | Main entry point for document processing. Handles `.txt`, `.md`, `.pdf`, `.docx`, `.xlsx/.csv`, and audio files. Calls specialized ingestors, then "bakes" output with `[Lxxxx]` line tags. Stores content in FTS index and generates chunk embeddings. Run via `python ingest.py <directory>`. |
| `ingest_audio.py` | Transcribes audio files (`.wav`, `.mp3`, `.m4a`) using Gemini API. Outputs timestamped, diarized transcripts. Requires `GOOGLE_API_KEY`. |
| `ingest_ocr.py` | PDF text extraction. Uses `pdftotext` for native text; falls back to Tesseract OCR with Qwen3-VL-2B (via LM Studio) for tables/forms. Heuristics detect when VLM is needed. |
| `embeddings.py` | Semantic search support. Loads `Qwen/Qwen3-Embedding-0.6B` model (singleton pattern, GPU preferred). Provides `encode_text()`, `create_chunks()`, `vector_search()`, and `extract_key_terms()` for stop-word filtering. |

### Search and verification

| File | Purpose |
|------|---------|
| `search_engine.py` | Multi-mode search interface. Modes: `exhaustive` (all FTS matches), `bm25` (ranked keyword), `vector` (pure semantic), `hybrid` (vector discovery → keyword pinpointing). Returns results with `match_type` ("exact_match" or "semantic_context") and `[Lxxxx]` citations. CLI: `python -m research_engine.search_engine "query" --mode hybrid`. |
| `judge.py` | Three-step claim verification: (1) Existence check (do lines exist?), (2) Quote match (fuzzy matching with ellipsis support), (3) Semantic check (LLM consensus from Local/OpenAI/Gemini). Returns structured JSON verdict. CLI: `python -m research_engine.judge "claim" "quote" "file.txt" start end`. |
| `deprecated/` | Deprecated components (`mcp_server.py` - FastMCP server exposing tools to AI agents: `search_hybrid`, `read_lines`, `verify_claim`, `log_finding`. Run via `python -m research_engine.mcp_server` or configure in MCP client.) |

### Other

| File | Purpose |
|------|---------|
| `__init__.py` | Empty; marks directory as Python package. |
| `scrapers/` | Empty subdirectory (placeholder for future scrapers). |

## Data flow

1. **Ingestion**: Raw files → `ingest.py` → Baked `.txt` files with line tags + FTS index + embeddings
2. **Search**: Query → `search_engine.py` → Results with file/line citations and match type
3. **Verification**: Claim + citation → `judge.py` → Structured verdict (verified/refuted/unverified)
4. **Logging**: Verified findings → `log_finding()` → SQLite `findings` table

## Dependencies

- **Required**: `sqlite3`, `pathlib`, `hashlib`, `json`, `re`
- **PDF processing**: `pdf2image`, `pytesseract`, `pdftotext` (poppler)
- **Audio**: `google-generativeai`
- **Embeddings**: `sentence-transformers`, `torch`, `numpy`
- **Spreadsheets**: `pandas`, `openpyxl`
- **Word docs**: `python-docx`
- **MCP server** (deprecated): `fastmcp`

## Usage

```bash
# Initialize database
python -m research_engine.database

# Ingest documents
python -m research_engine.ingest ./raw_documents

# Search
python -m research_engine.search_engine "budget allocation" --mode hybrid

# Verify a claim
python -m research_engine.judge "Budget increased 15%" "budget increase" "doc_baked.txt" 10 15
```
