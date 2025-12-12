---
description: Verify specific claims against source documents using "The Jury" (Multi-Model Consensus).
---

# Verify Claims

This workflow uses the **Verification Engine** to fact-check a report or a specific claim.

1.  **Identify Claim**:
    *   Agent: Select a specific claim that needs verification.
    *   Inputs needed:
        *   **Claim**: The statement to check (e.g., "Budget increased by 15%").
        *   **Quote**: The supporting text from the document.
        *   **File**: The baked filename (e.g., `minutes_2024_baked.txt`).
        *   **Lines**: Start and End line numbers.

2.  **Execute Judge**:
    *   Agent: Run the Judge CLI.
    *   Command: 
        ```bash
        python -m research_engine.judge "CLAIM" "QUOTE" "FILENAME" START_LINE END_LINE
        ```
    *   Example: `python -m research_engine.judge "Budget up 15%" "budget increase of 15%" "doc_baked.txt" 10 12`

3.  **Interpret Result**:
    *   Output: JSON with `verification_result` ("VERIFIED", "REFUTED", "UNVERIFIED") and `confidence_score`.
    *   Action: If REFUTED, flag the claim in the report.
