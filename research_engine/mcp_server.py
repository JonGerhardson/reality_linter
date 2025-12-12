
import asyncio
import json
import sqlite3
from typing import Optional, List
from fastmcp import FastMCP

from research_engine.search_engine import SearchEngine
from research_engine.judge import Judge
from research_engine.database import DB_PATH
import research_engine.config as config

# Initialize components
# Note: In a real persistent server, we might want to load these once or on demand efficiently.
# For this implementation, we initialize globally.

# We'll use a standard MCP server pattern if FastMCP isn't desired, but FastMCP is great for python.
# Let's assume standard mcp library usage for robustness if needed, 
# but FastMCP is the modern pythonic way in the toolkit.
# Based on common usage "mcp-python-sdk", often implies FastMCP.

mcp = FastMCP("TrustButVerify")

search_engine = SearchEngine(canonical_dir=config.CANONICAL_DIR)
judge = Judge(canonical_dir=config.CANONICAL_DIR)

@mcp.tool()
def search_hybrid(query: str, mode: str = "keyword") -> str:
    """
    Returns snippets including the [Lxxxx] tags. 
    Uses BM25 for keywords (names, entities) and Vector for concepts.
    Currently implements BM25 only as per Phase 2.1.
    """
    # Logic: "Critical: Returns snippets including the [Lxxxx] tags."
    results = search_engine.search(query, top_k=5)
    
    if not results:
        return "No results found."
    
    # Format output
    output = []
    for r in results:
        output.append(f"Source: {r['file']}\nScore: {r['score']:.2f}\nContent: {r['content']}\n")
    
    return "\n---\n".join(output)

@mcp.tool()
def read_lines(file: str, start: int, end: int) -> str:
    """
    Reads from data/canonical/. Returns raw text with [Lxxxx] tags.
    Throws error if lines out of bounds.
    """
    text, error = judge._read_lines(file, start, end)
    if error:
        raise ValueError(error)
    return text

@mcp.tool()
def verify_claim(claim: str, quote: str, file: str, lines: List[int]) -> str:
    """
    The Three-Step Judge.
    1. Existence: Do lines exist?
    2. Verbatim: Is quote in text? (Fuzzy match allowed)
    3. Semantic: Does text support claim? (LLM JSON)
    """
    if len(lines) != 2:
        return "Error: lines must be a list of two integers [start, end]"
    
    result = judge.verify_claim(claim, quote, file, lines)
    return json.dumps(result, indent=2)

@mcp.tool()
def log_finding(topic_id: str, claim: str, quote: str, source: str, line_start: int, line_end: int, confidence: str) -> str:
    """
    Saves the finding to SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if topic exists, if not create it (auto-create for usability?)
        # Spec says "topics" table has id, name. Let's just assume valid topic_id or insert if missing with dummy name?
        # Better to just insert finding.
        
        # Insert finding
        cursor.execute("""
            INSERT INTO findings 
            (topic_id, claim_summary, source_file, line_start, line_end, quoted_text, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (topic_id, claim, source, line_start, line_end, quote, confidence))
        
        finding_id = cursor.lastrowid
        conn.commit()
        return f"Finding saved with ID {finding_id}"
    except Exception as e:
        return f"Error saving finding: {e}"
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run()
