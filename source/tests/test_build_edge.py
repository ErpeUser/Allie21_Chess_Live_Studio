from __future__ import annotations

import json
import zipfile
from pathlib import Path

from source.automation.build_edge import build


def test_build_edge_writes_stamp_and_archive(tmp_path: Path) -> None:
    source = tmp_path / "browser"
    source.mkdir()
    (source / "manifest.json").write_text('{"version":"1.2.3.0"}\n', encoding="utf-8")
    (source / "background.js").write_text("self.ok = true;\n", encoding="utf-8")
    output = tmp_path / "release" / "EdgeOverlay"
    archive = tmp_path / "release" / "EdgeOverlay.zip"

    stamp = build(source, output, archive, "abc123")

    assert len(stamp["revision"]) == 64
    assert json.loads((output / "allie-build.json").read_text(encoding="utf-8"))["version"] == "1.2.3.0"
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "EdgeOverlay/manifest.json" in names
    assert "EdgeOverlay/allie-build.json" in names
