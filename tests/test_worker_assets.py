import base64
import io
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import scripts.package_worker as hosting


def test_packed_tile_keeps_original_bytes_and_quadrant_positions():
    originals = [b"original-one", b"original-two"]
    root = ET.fromstring(
        hosting.tile_svg([(0, 0, originals[0]), (512, 512, originals[1])], 1024)
    )
    assert root.attrib["viewBox"] == "0 0 1024 1024"
    images = list(root)
    assert [(i.attrib["x"], i.attrib["y"]) for i in images] == [
        ("0", "0"),
        ("512", "512"),
    ]
    assert [
        base64.b64decode(i.attrib["href"].split(",", 1)[1]) for i in images
    ] == originals
    assert len(ET.fromstring(hosting.tile_svg([], 512))) == 0


def test_packing_uses_pinned_archive_and_ignores_non_tiles_and_archive_paths(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hosting, "WORLDS", ("sky",))
    revision = "a" * 40
    archive = Path("cache/map/archives") / f"{revision}.tar.gz"
    archive.parent.mkdir(parents=True)
    with tarfile.open(archive, "w:gz") as out:
        for name, content in [
            ("repo/tiles/sky_64k/7/0/0.webp", b"northwest"),
            ("repo/tiles/sky_64k/7/1/1.webp", b"southeast"),
            ("repo/tiles/sky_64k/4/0/0.webp", b"overview"),
            ("repo/../../unexpected.txt", b"not-a-tile"),
            ("repo/images/levels/preview.webp", b"not-a-tile"),
        ]:
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            out.addfile(entry, io.BytesIO(content))
    tiles = hosting.prepare_tiles(revision)
    root = ET.fromstring((tiles / "sky/6/0/0.svg").read_text())
    assert [base64.b64decode(i.attrib["href"].split(",", 1)[1]) for i in root] == [
        b"northwest",
        b"southeast",
    ]
    assert root.attrib["width"] == "1024"
    assert not Path("unexpected.txt").exists()
    assert len(list(tiles.rglob("*.svg"))) == 256 + 1024 + 4096
    archive.unlink()
    assert hosting.prepare_tiles(revision) == tiles  # cached build needs no network
    with pytest.raises(ValueError, match="revision"):
        hosting.prepare_tiles("../outside")


def test_worker_package_routes_and_data_stay_public_and_rebuild_safely(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    Path("data/map_assets.json").write_text('{"tileset_revision":"' + "a" * 40 + '"}')

    def public_package(destination):
        destination.mkdir(parents=True)
        (destination / "index.html").write_text("<script>const DATA={};</script>")

    monkeypatch.setattr(hosting, "package", public_package)
    packed = Path("cache/tiles")
    packed.mkdir(parents=True)
    (packed / "tile.svg").write_text(hosting.tile_svg([], 1024))
    monkeypatch.setattr(hosting, "prepare_tiles", lambda revision: packed)
    hosting.package_worker(complete=True)
    out = Path("dist/worker")
    assert "ATLAS_HOSTING" in (out / "index.html").read_text()
    assert '"maxNativeZoom": 6' in (out / "index.html").read_text()
    assert (
        "https://jimmyzzt.github.io/OotSS_Sand/ 302" in (out / "_redirects").read_text()
    )
    assert "immutable" in (out / "_headers").read_text()
    assert not (out / "feedback-admin").exists()
    (out / "old.svg").write_text("stale")
    hosting.package_worker(complete=True)
    assert not (out / "old.svg").exists()
    Path("keep").mkdir()
    with pytest.raises(ValueError, match="dedicated directory"):
        hosting.package_worker("keep")
    assert Path("keep").exists()


def test_intro_packing_does_not_emit_empty_tiles_or_exceed_free_file_budget(
    tmp_path, monkeypatch
):
    import json

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hosting, "WORLDS", ("intro",))
    revision = "b" * 40
    archive = Path("cache/map/archives") / f"{revision}.tar.gz"
    archive.parent.mkdir(parents=True)
    with tarfile.open(archive, "w:gz") as out:
        for name in ["4/2/3", "5/4/6", "7/16/24", "7/17/25"]:
            content = b"original"
            entry = tarfile.TarInfo(f"repo/tiles/intro_64k/{name}.webp")
            entry.size = len(content)
            out.addfile(entry, io.BytesIO(content))
    tiles = hosting.prepare_tiles(revision)
    assert sorted(p.relative_to(tiles).as_posix() for p in tiles.rglob("*.svg")) == [
        "intro/4/2/3.svg",
        "intro/5/4/6.svg",
        "intro/6/8/12.svg",
    ]
    coverage = json.loads((tiles.parent / "complete.json").read_text())["tileCoverage"]
    assert coverage == {"intro": {"4": ["2/3"], "5": ["4/6"], "6": ["8/12"]}}
