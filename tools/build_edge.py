"""Build a reproducible unpacked Edge extension bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def source_revision(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "allie-build.json"):
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


def build(source: Path, output: Path, archive: Path | None, commit: str | None) -> dict[str, str]:
    if not source.is_dir():
        raise FileNotFoundError(f"extension source directory missing: {source}")
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    if not version:
        raise ValueError("extension manifest has no version")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output, ignore=shutil.ignore_patterns("allie-build.json", "__pycache__"))
    stamp = {
        "revision": source_revision(output),
        "commit": commit or git_revision(),
        "version": version,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "allie-build.json").write_text(
        json.dumps(stamp, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    if archive:
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(output.rglob("*")):
                if path.is_file():
                    bundle.write(path, Path(output.name) / path.relative_to(output))
    return stamp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("browser"))
    parser.add_argument("--output", type=Path, default=Path("release/Allie21-EdgeOverlay"))
    parser.add_argument("--archive", type=Path, default=Path("release/Allie21-EdgeOverlay.zip"))
    parser.add_argument("--commit")
    args = parser.parse_args()
    stamp = build(args.source.resolve(), args.output.resolve(), args.archive.resolve(), args.commit)
    print(json.dumps(stamp, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
