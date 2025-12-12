---
description: Conducts web research on a topic by searching, filtering, and ingesting relevant pages.
---

# Research Topic

This workflow allows the agent to build the knowledge base by researching a specific topic on the web.

1.  **Search**:
    *   Agent: Use `search_web` to find information on the topic.
    *   **Source Hierarchy**: Before general web searching, determine if an **Official Government Database** exists for the topic (e.g., SEC for lobbyists, OCPF for donations, Legislature for bills). Prioritize navigating these specific portals over generic keywords.
    *   Action: Review the search snippets to identify high-quality sources (Docs, News, Gov Reports).

2.  **Select & Ingest**:
    *   Agent: For each relevant URL:
        *   Run `python scripts/universal_scraper.py "<URL>" "{}"` (Empty JSON triggers Smart Discovery).
        *   *Fallback*: If the script fails (403/Empty), use the `browser_subagent` to visit the page and manually pipe text to `scripts/bake_text.py`.

3.  **Synthesize**:
    *   (Optional) If requested, the Agent can now query the baked documents to answer the user's question.
    *   Resources: `data/canonical/` now contains the research.
