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
command -v uv >/dev/null
command -v node >/dev/null
uv sync --frozen --extra quality
uv run --frozen python -m playwright install chromium
python3 source/automation/check_versions.py
