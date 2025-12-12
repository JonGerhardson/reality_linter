---
description: Scrapes a web page by first analyzing it with the browser, then automating extraction with a Python script.
---

# Scrape URL (Hybrid)

This workflow combines Agentic analysis (Browser) with efficiency (Python Script).

1.  **Analyze (Agent)**:
    *   **Action**: Use `browser_subagent` to visit the target URL.
    *   **Goal**: Identify the CSS Selector for the **Main Content** (e.g., `div.article-content` or `main`) and **Title** (e.g., `h1`).

2.  **Execute (Script)**:
    *   **Action**: Run the universal scraper script with your identified selectors.
    *   **Command**:
        ```bash
        python scripts/universal_scraper.py "<URL>" '{"content": "<CSS_SELECTOR>", "title": "<TITLE_SELECTOR>"}'
        ```
    *   **Fallback Protocol**: If `universal_scraper.py` returns empty or partial content:
        1.  **Try curl**: Attempt to fetch the raw HTML using curl if the site permits.
        2.  **Browser Copy**: Use `browser_subagent` to select all text on the page and save it directly to a file.
        3.  **User Request**: Explicitly ask the user to provide the raw text if automated tools are blocked by anti-bot measures.

3.  **Verify**:
    *   Check `data/canonical/` for the new `_baked.txt` file.
    *   **Anti-Summary Check**: Verify the `_baked.txt` file contains **raw, full-text content**, not a summary. If the file is a summary, delete it and retry with a different extraction method.

## Best Practices
*   **Input Hygiene**: When using the browser to fill forms (e.g., search bars), explicitly **clear the field** before sending keys to prevent concatenation errors with previous text.
