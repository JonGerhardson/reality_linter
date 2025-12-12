# Trust-But-Verify Investigation Engine (v3)

**A "Baked Truth" Research Engine for High-Integrity Investigations.**

This system transforms a folder of raw documents into a verifiable, line-tagged "Source of Truth" and provides an AI agent with tools to search, read, and rigorously verify claims before satisfying user requests.

## 🏗 System Architecture

The system operates on three core principles:
1.  **Baked Truth**: Files are pre-processed to have permanent line numbers (`[Lxxxx]`). This prevents "hallucinated" citations.
2.  **Stateful Research**: A SQLite database (`research.db`) tracks every finding and verification attempt.
3.  **The Judge**: A strict 3-step verification process (Existence, Quote Match, Semantic Check) is enforced before data is trusted.

### Components

*   **The Baker (`ingest.py`)**: Ingests raw text/PDFs, adds line tags, computes hashes, and saves to `data/canonical/`.
*   **The Search Engine (`search_engine.py`)**: A BM25 hybrid searcher that indexes the *baked* files.
*   **The Judge (`judge.py`)**: The core logic that verifies if a claim is supported by a specific file line range and quote.
*   **The Server (`mcp_server.py`)**: An MCP (Model Context Protocol) server that exposes these tools to Claude or other agents.

---

## 🚀 Installation

### Prerequisites
*   Python 3.10+
*   `uv` (recommended) or `pip`

### Steps

1.  **Clone/Navigate** to the project root.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Dependencies include: `mcp`, `fastmcp`, `rank-bm25`, `numpy`, `openai`, `pypdf`.*

3.  **Environment Setup**:
    Set your API keys (needed for the semantic verification step).
    ```bash
    export OPENAI_API_KEY="sk-..."
    ```

---

## 📖 Usage Guide

### 1. Ingestion (The Baker)

Before the agent can search anything, you must "bake" your raw documents.

```bash
# Process all files in the 'raw_documents' directory
python research_engine/ingest.py raw_documents
```

*   **Input**: `raw_documents/*.txt` (or PDFs if implemented)
*   **Output**: `data/canonical/*.txt` (with `[Lxxxx]` tags) and `data/document_metadata.json`.

### 2. Initialization (Database)

Initialize the SQLite persistence layer.

```bash
python research_engine/database.py
```

*   **Output**: `database/research.db` created with tables `topics`, `findings`, `verification_log`.

### 3. Running the Server

You can run the MCP server in development mode or connect it to Claude Desktop.

**Development Mode (Test Tools):**
```bash
fastmcp dev research_engine/mcp_server.py
```

**Claude Desktop Integration:**
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "trust-but-verify": {
      "command": "uv",
      "args": ["run", "research_engine/mcp_server.py"],
      "cwd": "/absolute/path/to/reality_linter"
    }
  }
}
```

---

## 📚 Module Documentation

### `research_engine/ingest.py`
*   **`bake_file(input_path, output_dir)`**: Reads a file, prepends `[L0001]` style tags to every line, and saves it. Computing MD5 hashes of 10-line blocks allows for future "drift detection" (knowing if the source file changed).
*   **`process_directory(input_dir)`**: Batch orchestrator. Skips files that look like they are already baked.

### `research_engine/judge.py`
This is the heart of the system.
*   **`verify_claim(claim, quote, file, lines)`**:
    1.  **Existence Check**: Opens `data/canonical/{file}`, verifies lines `start` to `end` exist.
    2.  **Quote Match**: Uses `_normalize_text` to strip tags/newlines, then checks if the quote is a substring of the text. Uses `SequenceMatcher` for robust fuzzy matching if exact match fails.
    3.  **Semantic Check**: Sends the text + claim to an LLM (GPT-4o-mini) to ask "Does this text support this claim?" Returns a JSON verification result.

### `research_engine/search_engine.py`
*   **`_build_index()`**: Loads all `*_baked.txt` files from `data/canonical/`. Tokenizes them and builds a `BM25Okapi` index in memory.
*   **`search(query)`**: Returns top results. Crucially, the returned "content" includes the `[Lxxxx]` tag so the agent knows exactly where it came from.

### `research_engine/database.py`
*   **Schema**:
    *   `topics`: High-level investigation subjects.
    *   `findings`: Validated evidence clips.
    *   `verification_log`: Audit trail of every time the Judge was called.

---

## 🛠 Workflows

The system is designed to replace manual script execution with agentic tools.

**Old Workflow:**
1. Manually run `investigate_topics.py`.
2. Manually merge text files.
3. Manually write report.

**New Workflow (v3):**
1. **Agent** uses `search_hybrid` to find info.
2. **Agent** uses `verify_claim` to check its own findings.
3. **Agent** uses `log_finding` to save confirmed truths to the DB.
4. **Agent** reads the DB to synthesize the final report.
