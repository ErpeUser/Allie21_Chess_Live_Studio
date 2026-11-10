#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v uv >/dev/null
command -v node >/dev/null
uv sync --frozen --extra quality
uv run --frozen python -m playwright install chromium
python3 tools/check_versions.py
