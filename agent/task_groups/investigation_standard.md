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
    *   **Goal**: Search the corpus and generate a report.

5.  **Verify**:
    *   **Task**: "Verify Claims"
    *   **Workflow**: `/verify_claims`
    *   **Goal**: Use "The Jury" to fact-check the generated report.
