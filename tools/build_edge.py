"""Build a reproducible unpacked Edge extension bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import ExitStack
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path


def source_revision(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != root / "allie-build.json"):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def validate_previous_output(output: Path) -> None:
    """Only replace an unchanged directory produced by this builder."""
    if not output.exists():
        return
    try:
        stamp = json.loads((output / "allie-build.json").read_text(encoding="utf-8"))
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        valid = (isinstance(stamp, dict) and isinstance(manifest, dict)
                 and bool(stamp.get("version"))
                 and stamp["version"] == str(manifest.get("version", ""))
                 and stamp.get("revision") == source_revision(output))
    except (OSError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"refusing to replace unrecognized or modified extension output: {output}")


def build(source: Path, output: Path, archive: Path | None, commit: str | None) -> dict[str, str]:
    for destination in [output, *([archive] if archive is not None else [])]:
        if destination.is_symlink() or destination.is_junction():
            raise ValueError(f"extension destination must not be a symlink or junction: {destination}")
    source, output = source.resolve(), output.resolve()
    archive = archive.resolve() if archive is not None else None
    paths = [source, output, *([archive] if archive is not None else [])]
    for first, second in combinations(paths, 2):
        if first.is_relative_to(second) or second.is_relative_to(first):
            raise ValueError(f"extension source, output and archive must not overlap: {first}, {second}")
    if not source.is_dir():
        raise FileNotFoundError(f"extension source directory missing: {source}")
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    if not version:
        raise ValueError("extension manifest has no version")
    validate_previous_output(output)
    if archive is not None and archive.exists() and not archive.is_file():
        raise ValueError(f"extension archive must be a file: {archive}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        stage_root = stack.enter_context(tempfile.TemporaryDirectory(prefix="edge-build-", dir=output.parent))
        stage = Path(stage_root) / "extension"
        shutil.copytree(source, stage, ignore=shutil.ignore_patterns("allie-build.json", "__pycache__"))
        stamp = {
            "revision": source_revision(stage),
            "commit": commit or git_revision(),
            "version": version,
            "built_at_utc": datetime.now(UTC).isoformat(),
        }
        (stage / "allie-build.json").write_text(
            json.dumps(stamp, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        staged_archive = None
        if archive is not None:
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive_root = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="edge-archive-", dir=archive.parent)
            )
            staged_archive = Path(archive_root) / "bundle.zip"
            with zipfile.ZipFile(staged_archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        bundle.write(path, Path(output.name) / path.relative_to(stage))
        # Finish copying, hashing and archiving before replacing a previous build.
        # Publishing the directory and ZIP is not an atomic transaction.
        if output.exists():
            shutil.rmtree(output)
        stage.replace(output)
        if staged_archive is not None and archive is not None:
            staged_archive.replace(archive)
    return stamp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("browser"))
    parser.add_argument("--output", type=Path, default=Path("release/Allie21-EdgeOverlay"))
    parser.add_argument("--archive", type=Path, default=Path("release/Allie21-EdgeOverlay.zip"))
    parser.add_argument("--commit")
    args = parser.parse_args()
    stamp = build(args.source, args.output, args.archive, args.commit)
    print(json.dumps(stamp, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
