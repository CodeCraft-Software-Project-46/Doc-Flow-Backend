"""
Small helpers over the raw `definition` json blob.

This intentionally does NOT recompute the version diff — that logic lives
client-side in workflowDefinitionCompare.ts so there's one implementation
of the diffing rules. This file only totals SLA seconds, which is cheap
and useful to expose on the lightweight list endpoint (so the version
table can show SLA without fetching each full definition).
"""

from typing import Optional


def total_sla_seconds(definition: Optional[dict]) -> int:
    if not definition:
        return 0

    nodes = definition.get("nodes") or []
    total = 0

    for node in nodes:
        if node.get("type") != "task":
            continue
        config = node.get("config") or {}
        total += int(config.get("slaSeconds") or 0)

    return total


def step_count(definition: Optional[dict]) -> int:
    if not definition:
        return 0
    return len(definition.get("nodes") or [])