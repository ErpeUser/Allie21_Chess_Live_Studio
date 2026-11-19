"""Fail closed if Git's index violates Allie's canonical source/output layout.

Read-only: no clean, reset, checkout, network call or branch manipulation.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
ROOT_FILES = frozenset({
    ".gitattributes", ".gitignore", ".gitleaks.toml", ".gitleaksignore",
    "AGENTS.md", "README_DE.md", "SECURITY.md", "LICENSE.txt",
    "pyproject.toml", "uv.lock", "START_HIER.bat", "UPDATE_ALLIE.cmd",
    "MODELL_EINRICHTEN.bat", "CHROME_OVERLAY_INSTALLIEREN.bat",
    "EDGE_OVERLAY_INSTALLIEREN.bat",
})
GITHUB_FILES = frozenset({
    ".github/CODEOWNERS", ".github/dependabot.yml",
    ".github/workflows/ci.yml", ".github/workflows/security.yml",
    ".github/workflows/windows-release.yml",
})
SOURCE_DIRS = frozenset({"automation", "docs", "resources", "tests"})
APP_DIRS = frozenset({"backend", "browser", "viewer"})
VENDOR_EXTENSIONS = frozenset({".py", ".csv", ".md", ".txt", ".json"})
TRANSIENT_SEGMENTS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "graphify-out", ".venv", ".build", ".git", ".github",
})
FORBIDDEN_NAMES = frozenset({"allie-build.json", ".coverage", "Thumbs.db"})


def allowed_path(path: str) -> bool:
    if not path or "\\" in path or path.startswith("/"):
        return False
    if path in ROOT_FILES or path in GITHUB_FILES:
        return True
    parts = PurePosixPath(path).parts
    if any(p in TRANSIENT_SEGMENTS for p in parts) or parts[-1] in FORBIDDEN_NAMES:
        return False
    if path.endswith((".pyc", ".pyo", ".log", ".safetensors", ".gguf", ".pt", ".pth")):
        return False
    if len(parts) >= 3 and parts[0] == "source":
        if parts[1] in SOURCE_DIRS:
            return True
        return parts[1] == "app" and len(parts) >= 4 and parts[2] in APP_DIRS
    if parts[:3] == ("generated", "dependencies", "vendor") and len(parts) >= 4:
        return PurePosixPath(path).suffix.lower() in VENDOR_EXTENSIONS
    return False


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)


def filesystem_link(path: str) -> bool:
    location = ROOT
    for part in PurePosixPath(path).parts:
        location = location / part
        if location.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(location)):
            return True
    return False


def validate_index(entries: bytes) -> list[str]:
    errors: list[str] = []
    for record in entries.split(b"\0"):
        if not record:
            continue
        metadata, sep, raw_name = record.partition(b"\t")
        if not sep:
            errors.append("Malformed Git index record")
            continue
        try:
            mode, _sha, stage = metadata.decode("ascii").split()
            name = raw_name.decode("utf-8", errors="replace")
        except ValueError:
            errors.append("Malformed Git index metadata")
            continue
        if stage != "0":
            errors.append(f"Unresolved merge conflict: {name}")
        if mode in {"120000", "160000"}:
            errors.append(f"Symlink or nested repository in Git index: {name}")
        if not allowed_path(name):
            errors.append(f"Disallowed tracked path: {name}")
        if allowed_path(name) and filesystem_link(name):
            errors.append(f"Filesystem symlink/junction in source path: {name}")
    return errors


def validate_ignore_rules() -> list[str]:
    errors = []
    probes = {
        "generated/dist/win/probe.exe": True,
        "generated/cache/probe.bin": True,
        "generated/environments/probe/file.py": True,
        "generated/dependencies/models/probe.safetensors": True,
        "generated/protected/git/HEAD": True,
        "source/app/browser/allie-build.json": True,
        "generated/dependencies/vendor/allie_model/model.py": False,
        "source/app/backend/live_server.py": False,
        "source/tests/test_chess.py": False,
    }
    for path, should_ignore in probes.items():
        result = git("check-ignore", "--no-index", "-q", "--", path)
        if result.returncode not in (0, 1):
            errors.append(f"Git ignore query failed: {path}")
        elif (result.returncode == 0) != should_ignore:
            errors.append(f"Wrong .gitignore rule: {path} (ignored={result.returncode == 0})")
    return errors


def main() -> int:
    index = git("ls-files", "--stage", "-z")
    if index.returncode:
        print("Repository policy FAIL: git ls-files failed")
        return 1
    errors = validate_index(index.stdout) + validate_ignore_rules()
    for item in errors:
        print("Repository policy FAIL:", item)
    if errors:
        return 1
    print("Repository policy PASS: canonical source, pinned vendor and generated isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
