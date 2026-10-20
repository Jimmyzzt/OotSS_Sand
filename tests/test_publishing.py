from scripts.package_site import package
from scripts.update_video_links import link_map


def test_inserted_index_parts_remap_by_cid():
    original = {
        "parts": [{"part_number": 1, "cid": 111}, {"part_number": 2, "cid": 222}]
    }
    pages = [{"page": 1, "cid": 999}, {"page": 2, "cid": 111}, {"page": 3, "cid": 222}]
    assert link_map(original, pages)["parts"] == {"1": {"part": 2}, "2": {"part": 3}}


def test_public_package_excludes_unrelated_source_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in [
        "index.html",
        "index.json",
        "atlas.css",
        "atlas.js",
        "atlas-ui.js",
        "visits.csv",
        "raw.mp4",
        ".env",
    ]:
        (source / name).write_text("fixture")
    (source / "assets").mkdir()
    (source / "assets/map.webp").write_bytes(b"fixture")
    out = tmp_path / "out"
    package(source, out)
    assert not (out / "raw.mp4").exists()
    assert not (out / ".env").exists()
    assert (out / "assets/map.webp").exists()
    assert (out / "atlas-ui.js").read_text() == "fixture"
