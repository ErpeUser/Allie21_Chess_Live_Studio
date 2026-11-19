#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
export UV_PROJECT_ENVIRONMENT="$PWD/generated/environments/source"
export UV_CACHE_DIR="$PWD/generated/cache/uv"
export UV_TOOL_DIR="$PWD/generated/toolchains/uv"
export RUFF_CACHE_DIR="$PWD/generated/cache/ruff"
export MYPY_CACHE_DIR="$PWD/generated/cache/mypy"
export PYTHONPYCACHEPREFIX="$PWD/generated/cache/python"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/generated/cache/browser"
export HF_HOME="$PWD/generated/dependencies/models"
uv sync --frozen --extra quality
python3 source/automation/check_versions.py
node --test source/tests/test_extension_updates.js source/tests/test_worker_wakeup.js
uv run --frozen python -m unittest discover -s source/tests -p 'test_maintenance.py' -v
# GitHub writes require the explicit maintain.py command documented in AGENTS.md.
