"""
Search engine with multiple modes: exhaustive, bm25, vector, hybrid.
"""

import re
import sqlite3
from typing import List, Dict, Optional
from research_engine.database import DB_PATH, get_all_embeddings


class SearchEngine:
    def __init__(self, canonical_dir=None):
        self.db_path = DB_PATH

    def search(self, query: str, mode: str = "hybrid", top_k: int = 10, 
               exhaustive: bool = False) -> List[Dict]:
        """
        Main entry point supporting multiple search modes.
        
        Args:
            query: Search query
            mode: "exhaustive", "bm25", "vector", "hybrid"
            top_k: Max results (ignored if exhaustive=True)
            exhaustive: If True, return ALL matches (FTS only)
        
        Returns:
            List of result dicts with file, citation, match_type, etc.
        """
        if exhaustive:
            return self.search_exhaustive(query)
        
        if mode == "bm25" or mode == "keyword":
            return self.search_bm25(query, top_k)
        elif mode == "vector" or mode == "semantic":
            return self.search_vector(query, top_k)
        elif mode == "hybrid":
            return self.search_hybrid(query, top_k)
        else:
            # Default to hybrid
            return self.search_hybrid(query, top_k)

    def search_exhaustive(self, query: str) -> List[Dict]:
        """
        FTS5 search returning ALL matches across all documents.
        No limit, for "find every mention of X" queries.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get all matching documents
            sql = """
                SELECT filename, baked_content
                FROM documents_fts
                WHERE documents_fts MATCH ?
            """
            fts_query = f'"{query}"'
            rows = conn.execute(sql, (fts_query,)).fetchall()
            
            results = []
            for row in rows:
                # Extract every line containing the query
                lines = self._extract_matching_lines(row['baked_content'], [query])
                for line_info in lines:
                    results.append({
                        "file": row['filename'],
                        "citation": f"[L{line_info['line_num']:04d}]",
                        "match_type": "exact_match",
                        "content": line_info['content']
                    })
            
            return results
            
        except Exception as e:
            print(f"FTS Exhaustive Search Error: {e}")
            return []
        finally:
            conn.close()

    def search_bm25(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        FTS5 BM25 ranked search with improved line extraction.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            sql = """
                SELECT filename, baked_content, rank
                FROM documents_fts 
                WHERE documents_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """
            fts_query = f'"{query}"'
            rows = conn.execute(sql, (fts_query, top_k * 2)).fetchall()
            
            results = []
            for row in rows:
                lines = self._extract_matching_lines(row['baked_content'], [query])
                for line_info in lines[:3]:  # Top 3 lines per doc
                    results.append({
                        "file": row['filename'],
                        "citation": f"[L{line_info['line_num']:04d}]",
                        "match_type": "exact_match",
                        "content": line_info['content'],
                        "score": row['rank']
                    })
            
            return results[:top_k]
            
        except Exception as e:
            print(f"FTS BM25 Search Error: {e}")
            return []
        finally:
            conn.close()

    def search_vector(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Pure vector/semantic search on chunk embeddings.
        """
        from research_engine.embeddings import encode_text, vector_search
        
        # Encode query
        query_embedding = encode_text(query)
        
        # Get all embeddings from DB
        embeddings = get_all_embeddings(self.db_path)
        
        if not embeddings:
            return []
        
        # Vector search
        results = vector_search(query_embedding, embeddings, top_k)
        
        return [{
            "file": r['filename'],
            "citation": f"[L{r['start_line']:04d}-L{r['end_line']:04d}]",
            "match_type": "semantic_context",
            "preview": r['chunk_text'][:300],
            "score": r['score']
        } for r in results]

    def search_hybrid(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Hybrid search: Vector discovery → keyword pinpointing.
        Returns exact_match when keywords found, semantic_context otherwise.
        """
        from research_engine.embeddings import encode_text, vector_search, extract_key_terms
        
        # Stage 1: Vector search to find relevant chunks
        query_embedding = encode_text(query)
        embeddings = get_all_embeddings(self.db_path)
        
        if not embeddings:
            # Fallback to BM25 if no embeddings
            return self.search_bm25(query, top_k)
        
        vector_results = vector_search(query_embedding, embeddings, top_k=20)
        
        # Stage 2: Extract key terms (filters stop words)
        query_terms = extract_key_terms(query)
        
        results = []
        for chunk in vector_results:
            # Try keyword extraction within chunk
            lines = self._extract_matching_lines(chunk['chunk_text'], query_terms)
            
            if lines:
                # EXACT MATCH: Found keywords in chunk
                for line_info in lines[:2]:  # Top 2 lines per chunk
                    results.append({
                        "file": chunk['filename'],
                        "citation": f"[L{chunk['start_line'] + line_info['line_num'] - 1:04d}]",
                        "match_type": "exact_match",
                        "content": line_info['content'],
                        "score": chunk['score']
                    })
            else:
                # SEMANTIC CONTEXT: Relevant chunk but no keyword match
                results.append({
                    "file": chunk['filename'],
                    "citation": f"[L{chunk['start_line']:04d}-L{chunk['end_line']:04d}]",
                    "match_type": "semantic_context",
                    "preview": chunk['chunk_text'][:300],
                    "action": "MANUAL_REVIEW",
                    "score": chunk['score']
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:top_k]

    def _extract_matching_lines(self, content: str, query_terms: List[str]) -> List[Dict]:
        """
        Extract lines containing query terms, preserving [Lxxxx] tags.
        """
        if not query_terms:
            return []
        
        results = []
        for i, line in enumerate(content.split('\n'), start=1):
            line_lower = line.lower()
            
            # Check if any query term is in this line
            matched_terms = [t for t in query_terms if t.lower() in line_lower]
            
            if matched_terms:
                # Try to extract line number from [Lxxxx] tag
                line_match = re.match(r'\[L(\d{4})\]', line)
                line_num = int(line_match.group(1)) if line_match else i
                
                results.append({
                    "line_num": line_num,
                    "content": line,
                    "matched_terms": matched_terms
                })
        
        return results


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Search the corpus")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--mode", default="hybrid", 
                        choices=["exhaustive", "bm25", "vector", "hybrid"],
                        help="Search mode")
    parser.add_argument("--exhaustive", action="store_true",
                        help="Return ALL matches (overrides --mode)")
    parser.add_argument("-n", "--top-k", type=int, default=10,
                        help="Max results")
    
    args = parser.parse_args()
    
    se = SearchEngine()
    results = se.search(args.query, mode=args.mode, top_k=args.top_k, 
                        exhaustive=args.exhaustive)
    
    print(f"\n[*] Found {len(results)} results for '{args.query}' (mode={args.mode}):\n")
    
    for r in results:
        print(f"📄 {r['file']} {r['citation']}")
        print(f"   Type: {r['match_type']}")
        if 'content' in r:
            print(f"   {r['content'][:100]}...")
        elif 'preview' in r:
            print(f"   {r['preview'][:100]}...")
        if r.get('action'):
            print(f"   ⚠️ {r['action']}")
        print()

