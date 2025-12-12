---
description: Add a new investigation topic to the system.
---

# Add Investigation Topic

1.  **Ask User for Input**: Request the "Topic ID" (e.g., topic_10), "Topic Name", and "Keywords".
    *   Example: "topic_10_new_investigation", "New Investigation", "keyword1, keyword2"

2.  **Edit Script**:
    *   Open `scripts/investigate_topics.py`.
    *   Locate the `topics` dictionary.
    *   Insert the new topic entry preserving the JSON structure.
    *   Format:
        ```python
        "topic_id.md": {
            "keywords": ["kw1", "kw2"],
            "title": "Topic Name"
        },
        ```

3.  **Update Database**:
    *   Run a one-off python script to insert the topic into the `topics` table in `database/research.db`.
    *   Command: `python3 -c "import sqlite3; conn=sqlite3.connect('database/research.db'); conn.execute(\"INSERT OR IGNORE INTO topics (id, name) VALUES (?, ?)\", ('topic_id', 'Topic Name')); conn.commit();"`

4.  **Verification**:
    *   Run `python3 scripts/investigate_topics.py --help` (or check syntax) to ensure no syntax errors were introduced.
    *   Verify the topic exists in the DB: `python3 -c "import sqlite3; print(sqlite3.connect('database/research.db').execute('SELECT * FROM topics WHERE id=?', ('topic_id',)).fetchone())"`
