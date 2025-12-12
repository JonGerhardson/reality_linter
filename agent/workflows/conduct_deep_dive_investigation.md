---
description: Conduct a deep dive investigation by searching the corpus with specific queries.
---

# Conduct Deep Dive Investigation

This workflow guides the agent to use the internal **Search Engine** to find evidence.

1.  **Define Query**:
    *   Agent: Identify the key terms or entities to search for.
    *   Context: "What specific keywords will reveal the connections?"

2.  **Execute Search**:
    *   Agent: Run the search engine CLI.
    *   Command: `python -m research_engine.search_engine "YOUR QUERY"`
    *   Output: A list of file snippets and ranks.

3.  **Synthesize**:
    *   Agent: Read the full content of the top-ranked files if the snippets are promising.
    *   Command: `view_file` (or `read_file`) on the best matches.
    *   Action: Compile findings into a report.
