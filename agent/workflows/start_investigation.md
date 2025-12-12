---
description: Starts a new Standard Investigation by guiding the agent through the defined task group.
---

# Start Investigation

This macro initializes the "Standard Investigation" Task Group.

1.  **Context**:
    *   Agent: Ask the user for the **Investigation Topic** (e.g., "Mayor's Budget 2024").

2.  **Initialize**:
    *   Agent: Read `.agent/task_groups/investigation_standard.md`.
    *   Agent: Propose the plan to the user.

3.  **Execute**:
    *   Agent: Begin executing the tasks in order (Ingest -> Research -> Discovery...).
