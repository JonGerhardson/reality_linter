---
description: A standard "Full Reality" investigation pipeline.
---

# Standard Investigation

This task group defines the standard operating procedure for a potentially complex investigation.

1.  **Ingest Data**:
    *   **Task**: "Ingest Documents"
    *   **Workflow**: `/ingest_documents`
    *   **Goal**: Ensure all local files in `raw_documents/` are baked.

2.  **Web Research (Optional)**:
    *   **Task**: "Research Topic"
    *   **Workflow**: `/research_topic`
    *   **Goal**: Gather external context if needed.

3.  **Discovery**:
    *   **Task**: "Add Topic"
    *   **Workflow**: `/add_topic`
    *   **Goal**: Define the specific entities/claims to investigate.

4.  **Deep Dive**:
    *   **Task**: "Conduct Deep Dive"
    *   **Workflow**: `/conduct_deep_dive_investigation`
    *   **Goal**: Search the corpus and generate a report in `reports/`.

5.  **Verify**:
    *   **Task**: "Verify Claims"
    *   **Workflow**: `/verify_claims`
    *   **Goal**: Use "The Jury" to fact-check the generated report.

6.  **Reporting Standards**:
    *   **Citation Format**: `[Source: FILENAME (Lxx-Lyy)](../data/canonical/FILENAME#Lxx)`
    *   **Quote Fidelity**: If the text in the report differs from the source (even slightly), mark it as "Paraphrased" or "based on". Do not present a near-match as a direct quote.
    *   **URL Encoding**: You MUST URL-encode spaces in the filename path (e.g., `My%20File.txt`).
    *   **Example**: `[Source: Annual Report 2024.txt (L10-L12)](../data/canonical/Annual%20Report%202024.txt#L10)`
