
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

if __name__ == "__main__":
    init_db()
