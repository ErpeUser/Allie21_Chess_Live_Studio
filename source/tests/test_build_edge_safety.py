from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from source.automation.build_edge import build


def make_source(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "manifest.json").write_text('{"version":"1.2.3.0"}\n', encoding="utf-8")
    (path / "background.js").write_bytes(b"self.ok = true;\n")
    return path


def files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def symlink(link: Path, target: Path, *, directory: bool = True) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


@pytest.mark.parametrize(("source_name", "output_name", "archive_name"), [
    ("browser", "browser", None),
    ("browser", "browser/EdgeOverlay", None),
    ("parent/browser", "parent", None),
    ("browser", "EdgeOverlay", "browser"),
    ("browser", "EdgeOverlay", "browser/manifest.json"),
    ("browser", "EdgeOverlay", "browser/archive.zip"),
    ("parent/browser", "EdgeOverlay", "parent"),
    ("browser", "EdgeOverlay", "EdgeOverlay"),
    ("browser", "EdgeOverlay", "EdgeOverlay/archive.zip"),
    ("browser", "archives/EdgeOverlay", "archives"),
])
def test_build_rejects_overlapping_paths_without_changes(
    tmp_path: Path, source_name: str, output_name: str, archive_name: str | None,
) -> None:
    source = make_source(tmp_path / source_name)
    output = tmp_path / output_name
    archive = tmp_path / archive_name if archive_name else None
    before = files(tmp_path)
    entries = set(tmp_path.rglob("*"))

    with pytest.raises(ValueError, match="overlap"):
        build(source, output, archive, "test")

    assert files(tmp_path) == before
    assert set(tmp_path.rglob("*")) == entries


@pytest.mark.parametrize("destination", ["output", "output-child", "archive-child"])
def test_build_rejects_source_alias_destinations(tmp_path: Path, destination: str) -> None:
    source = make_source(tmp_path / "browser")
    alias = tmp_path / "alias"
    symlink(alias, source)
    output = alias if destination == "output" else tmp_path / "EdgeOverlay"
    archive = alias / "bundle.zip" if destination == "archive-child" else None
    if destination == "output-child":
        output = alias / "EdgeOverlay"
    before = files(source)

    with pytest.raises(ValueError):
        build(source, output, archive, "test")

    assert files(source) == before
    assert alias.is_symlink()


@pytest.mark.parametrize("script_bytes", [b"self.ok = true;\n", b"self.ok = true;\r\n"],
                         ids=["lf", "crlf"])
def test_build_accepts_disjoint_symlinked_source(tmp_path: Path, script_bytes: bytes) -> None:
    source = make_source(tmp_path / "browser")
    (source / "background.js").write_bytes(script_bytes)
    alias = tmp_path / "alias"
    symlink(alias, source)
    output = tmp_path / "EdgeOverlay"

    build(alias, output, None, "test")

    assert (output / "background.js").read_bytes() == script_bytes
    assert (source / "background.js").read_bytes() == script_bytes
    assert alias.is_symlink()


@pytest.mark.parametrize("destination", ["output", "archive"])
def test_build_rejects_symlinked_destinations(tmp_path: Path, destination: str) -> None:
    source = make_source(tmp_path / "browser")
    target = tmp_path / "user-data"
    target.mkdir()
    private_file = target / "notes.txt"
    private_file.write_bytes(b"preserve user data")
    link = tmp_path / "link"
    symlink(link, target if destination == "output" else private_file,
            directory=destination == "output")
    output = link if destination == "output" else tmp_path / "EdgeOverlay"
    archive = link if destination == "archive" else None

    with pytest.raises(ValueError):
        build(source, output, archive, "test")

    assert private_file.read_bytes() == b"preserve user data"
    assert link.is_symlink()


def test_cli_does_not_resolve_away_output_symlink(tmp_path: Path) -> None:
    source = make_source(tmp_path / "browser")
    target = tmp_path / "user-data"
    target.mkdir()
    (target / "notes.txt").write_bytes(b"preserve user data")
    link = tmp_path / "output-link"
    symlink(link, target)
    script = Path(__file__).resolve().parents[1] / "automation" / "build_edge.py"
    assert script.is_file(), 'The symlink safety test must invoke the real CLI'

    result = subprocess.run([
        sys.executable, str(script), "--source", str(source), "--output", str(link),
        "--archive", str(tmp_path / "EdgeOverlay.zip"), "--commit", "test",
    ], capture_output=True, text=True, check=False)

    assert result.returncode != 0
    assert (target / "notes.txt").read_bytes() == b"preserve user data"
    assert link.is_symlink()


@pytest.mark.parametrize("stamp", [None, "not JSON", "[]", '{}'])
def test_build_preserves_unrecognized_output(tmp_path: Path, stamp: str | None) -> None:
    source = make_source(tmp_path / "browser")
    output = tmp_path / "EdgeOverlay"
    output.mkdir()
    (output / "notes.txt").write_bytes(b"preserve user data")
    if stamp is not None:
        (output / "allie-build.json").write_text(stamp, encoding="utf-8")
    before = files(output)

    with pytest.raises(ValueError):
        build(source, output, None, "test")

    assert files(output) == before


@pytest.mark.parametrize("modified_path", ["background.js", "notes.txt", "nested/allie-build.json"])
def test_build_preserves_modified_previous_output(tmp_path: Path, modified_path: str) -> None:
    source = make_source(tmp_path / "browser")
    output = tmp_path / "EdgeOverlay"
    build(source, output, None, "old")
    modified = output / modified_path
    modified.parent.mkdir(parents=True, exist_ok=True)
    modified.write_bytes(b"preserve local changes")
    before = files(output)

    with pytest.raises(ValueError):
        build(source, output, None, "new")

    assert files(output) == before


def test_rebuild_replaces_previous_generated_output_and_archive(tmp_path: Path) -> None:
    source = make_source(tmp_path / "browser")
    (source / "obsolete.js").write_bytes(b"old content")
    output = tmp_path / "release" / "EdgeOverlay"
    archive = tmp_path / "archives" / "EdgeOverlay.zip"
    build(source, output, archive, "old")
    (source / "obsolete.js").unlink()
    (source / "background.js").write_bytes(b"self.ok = 'new';\n")

    stamp = build(source, output, archive, "new")

    assert (output / "background.js").read_bytes() == b"self.ok = 'new';\n"
    assert not (output / "obsolete.js").exists()
    assert json.loads((output / "allie-build.json").read_text(encoding="utf-8")) == stamp
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == {
            "EdgeOverlay/manifest.json", "EdgeOverlay/background.js", "EdgeOverlay/allie-build.json",
        }
        assert bundle.read("EdgeOverlay/background.js") == b"self.ok = 'new';\n"
        assert json.loads(bundle.read("EdgeOverlay/allie-build.json")) == stamp
    assert set(output.parent.iterdir()) == {output}
    assert set(archive.parent.iterdir()) == {archive}


def test_copy_failure_preserves_previous_build_and_archive(tmp_path: Path) -> None:
    source = make_source(tmp_path / "browser")
    output = tmp_path / "release" / "EdgeOverlay"
    archive = tmp_path / "release" / "EdgeOverlay.zip"
    build(source, output, archive, "old")
    before = files(output.parent)
    symlink(source / "broken.js", source / "missing.js", directory=False)

    with pytest.raises(shutil.Error):
        build(source, output, archive, "new")

    assert files(output.parent) == before
    assert set(output.parent.iterdir()) == {output, archive}


def test_zip_failure_preserves_previous_build_and_archive(tmp_path: Path) -> None:
    source = make_source(tmp_path / "browser")
    output = tmp_path / "release" / "EdgeOverlay"
    archive = tmp_path / "release" / "EdgeOverlay.zip"
    build(source, output, archive, "old")
    before = files(output.parent)
    os.utime(source / "background.js", (0, 0))

    with pytest.raises(ValueError, match="timestamps before 1980"):
        build(source, output, archive, "new")

    assert files(output.parent) == before
    assert set(output.parent.iterdir()) == {output, archive}
