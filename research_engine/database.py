
import sqlite3
import os

DB_PATH = "database/research.db"

SCHEMA = """
-- Tracks high-level investigation buckets
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,        -- e.g., "topic_8_servistar"
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stores specific evidence clips found by the agent
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT,
    claim_summary TEXT,         -- "Budget increased by 15%"
    source_file TEXT,           -- "minutes_2024_baked.txt"
    line_start INTEGER,
    line_end INTEGER,
    quoted_text TEXT,           -- The verbatim string relied upon
    confidence TEXT,            -- "High", "Medium", "Low"
    FOREIGN KEY(topic_id) REFERENCES topics(id)
);

-- An immutable log of every verification attempt
CREATE TABLE IF NOT EXISTS verification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER,
    check_lines_exist BOOLEAN,  -- Pass/Fail
    check_quote_matches BOOLEAN,-- Pass/Fail
    check_semantic_support JSON,-- The JSON output from the Judge LLM
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(finding_id) REFERENCES findings(id)
);

-- V4: Full Text Search Index
CREATE TABLE IF NOT EXISTS documents (
    filename TEXT PRIMARY KEY,
    content TEXT,
    baked_content TEXT -- Content with [Lxxxx] tags
);

-- Create FTS5 virtual table
-- Note: sqlite3 in python usually supports FTS5.
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(filename, content, baked_content);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
  INSERT INTO documents_fts(filename, content, baked_content) VALUES (new.filename, new.content, new.baked_content);
END;
CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
  INSERT INTO documents_fts(documents_fts, filename, content, baked_content) VALUES('delete', old.filename, old.content, old.baked_content);
END;
CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
  INSERT INTO documents_fts(documents_fts, filename, content, baked_content) VALUES('delete', old.filename, old.content, old.baked_content);
  INSERT INTO documents_fts(filename, content, baked_content) VALUES (new.filename, new.content, new.baked_content);
END;

-- V5: Chunk embeddings for semantic search
-- Serialization: embedding.astype(np.float32).tobytes() / np.frombuffer(blob, dtype=np.float32)
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    FOREIGN KEY(filename) REFERENCES documents(filename)
);

CREATE INDEX IF NOT EXISTS idx_chunk_filename ON chunk_embeddings(filename);
"""

def init_db(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

def insert_document_content(filename: str, content: str, baked_content: str, db_path=DB_PATH):
    """Inserts or replaces document content in the DB and FTS index."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO documents (filename, content, baked_content) VALUES (?, ?, ?)",
            (filename, content, baked_content)
        )
        conn.commit()
    finally:
        conn.close()

def insert_chunk_embedding(filename: str, start_line: int, end_line: int, 
                           chunk_text: str, embedding_blob: bytes, db_path=DB_PATH):
    """Inserts a chunk embedding. embedding_blob should be numpy.float32.tobytes()"""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO chunk_embeddings 
               (filename, start_line, end_line, chunk_text, embedding) 
               VALUES (?, ?, ?, ?, ?)""",
            (filename, start_line, end_line, chunk_text, embedding_blob)
        )
        conn.commit()
    finally:
        conn.close()

def delete_embeddings_for_file(filename: str, db_path=DB_PATH):
    """Removes all chunk embeddings for a file (before re-indexing)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM chunk_embeddings WHERE filename = ?", (filename,))
        conn.commit()
    finally:
        conn.close()

def get_all_embeddings(db_path=DB_PATH):
    """Returns all embeddings for vector search. Use np.frombuffer(blob, dtype=np.float32)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, filename, start_line, end_line, chunk_text, embedding FROM chunk_embeddings"
        ).fetchall()
        return rows
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
