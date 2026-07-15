#!/usr/bin/env python3
"""Run the public deterministic evidence-brief fixture without an LLM or network."""

import json
from dataclasses import asdict
from pathlib import Path

from agent_control_plane.knowledge import build_context_packet, load_nodes
from agent_control_plane.pipeline import run_research_brief


REPOSITORY_ROOT = Path(__file__).parents[1]
VAULT = REPOSITORY_ROOT / "examples" / "demo_vault"


def main() -> None:
    nodes = load_nodes(VAULT)
    packet = build_context_packet(
        task_id="demo-research-brief-001",
        project_id="demo-research",
        objective="Create an evidence brief from public authored fixtures.",
        nodes=nodes,
    )
    run = run_research_brief(packet=packet, nodes=nodes)
    print(json.dumps(asdict(run), indent=2, default=str))


if __name__ == "__main__":
    main()
