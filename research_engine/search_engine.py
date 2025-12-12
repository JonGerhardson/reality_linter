
import sqlite3
from research_engine.database import DB_PATH

class SearchEngine:
    def __init__(self, canonical_dir=None):
        # canonical_dir is legacy param, unused now in v4
        self.db_path = DB_PATH

    def search(self, query: str, top_k: int = 5):
        """
        Executes a Full Text Search (FTS5) query against the database.
        Returns snippets with [Lxxxx] tags from the baked_content.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # FTS5 Query Syntax: MATCH 'keyword'
        # We can implement simple boolean search or phrase search.
        # For robustness with spaces, we wrap in double quotes or standard parser handling.
        
        try:
            # We want to find the file, then extract relevant lines (snippets).
            # SQLite FTS snippet() function is powerful but works on the indexed column.
            # We indexed 'baked_content'.
            # snippet(documents_fts, 2, '<b>', '</b>', '...', 64) -> column 2 is baked_content
            
            # Note: snippet() returns a small chunk. 
            # If we want the *line* with the tag, FTS snippet is okay but might cut off the tag [Lxxxx] if it's far away?
            # Actually, since [Lxxxx] is at the start of every line, standard snippet algorithm might catch it if the keyword is near.
            # Let's try simple snippet first.
            
            sql = """
                SELECT 
                    filename, 
                    snippet(documents_fts, 2, '>>>', '<<<', '...', 10) as snippet_text,
                    rank
                FROM documents_fts 
                WHERE documents_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """
            
            # Simple sanitization for FTS match query
            # A phrase search is "query".
            fts_query = f'"{query}"' 
            
            cursor = conn.execute(sql, (fts_query, top_k))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "score": row['rank'], # FTS rank is usually lower is better (more relevant negative magnitude?) No, BM25 inverse.
                    # Actually FTS5 rank is a score.
                    "file": row['filename'],
                    "content": row['snippet_text']
                })
                
            return results

        except Exception as e:
            print(f"FTS Search Error: {e}")
            return []
        finally:
            conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m research_engine.search_engine <query>")
        sys.exit(1)
        
    query = sys.argv[1]
    se = SearchEngine()
    results = se.search(query)
    
    print(f"[*] Found {len(results)} matches for '{query}':")
    for r in results:
        print(f"File: {r['file']}")
        print(f"Content: {r['content']}")
        print("-" * 20)
