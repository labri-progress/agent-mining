#!/bin/bash
set -e

AGENTS_DIR="${1:-agents}"
AGENTS_MD_DIR="${2:-agents_md}"

echo "Generating..."
python3 generate_agent_jsons.py "$AGENTS_DIR"
python3 generate_agent_mds.py "$AGENTS_DIR" "$AGENTS_MD_DIR"
python3 generate_heuristics_table.py "$AGENTS_DIR" heuristics.md "$AGENTS_MD_DIR"
echo "✓ Done"
