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

## Scenario: Complex Captcha / Bot Detection (e.g. MassCourts)

If the standard `browser_subagent` blocked by Cloudflare/Akamai or requires a complex captcha:

1.  **Launch Debug Browser for User**:
    *   Start Chrome with remote debugging enabled so the user can intervene.
    *   Command: `google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug "<URL>" &`
2.  **Request User Intervention**:
    *   Use `notify_user` to ask the user to solve the captcha and navigate to the target page.
3.  **Connect & Automate**:
    *   Use a Python script with `playwright` to connect to the existing session and perform the extraction.
    *   **Reference Script**: `scripts/masscourts_cdp_search.py`
    *   **Snippet**:
        ```python
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0]
            # Perform actions...
        ```
4.  **Complex Interactions**:
    *   For tasks requiring navigation (e.g., clicking search results, pagination):
    *   **Reference Script**: `scripts/masscourts_cdp_extract.py`
    *   **Technique**: Use `page.locator("...").click()` to navigate, then `page.wait_for_load_state` or `time.sleep` to handle AJAX transitions before extracting content.

## Best Practices
*   **Input Hygiene**: When using the browser to fill forms (e.g., search bars), explicitly **clear the field** before sending keys to prevent concatenation errors with previous text.
