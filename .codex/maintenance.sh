#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv sync --frozen --extra quality
python3 tools/check_versions.py
node --test tests/test_extension_updates.js tests/test_worker_wakeup.js
uv run --frozen python -m unittest discover -s tests -p 'test_maintenance.py' -v
# GitHub writes require the explicit maintain.py command documented in AGENTS.md.
