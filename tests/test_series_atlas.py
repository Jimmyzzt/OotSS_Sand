import io
import json
from pathlib import Path

from PIL import Image

from ootss.atlas import build_atlas
from ootss.common import read_json, write_json
from ootss.exporting import draw_map
from ootss.series import discover, safe_title


def test_windows_part_names():
    assert safe_title('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"
    assert len(safe_title("长" * 150)) == 110
    assert safe_title(" title. ") == "title"


def test_rediscovery_preserves_existing_recovered_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    recovered = tmp_path / "P01__recovered.mp4"
    recovered.write_bytes(b"fixture")
    write_json(
        "manifest.json",
        {
            "parts": [
                {
                    "part_number": 1,
                    "cid": 123,
                    "file": str(recovered),
                    "download_status": "complete",
                }
            ]
        },
    )
    pages = [
        {"page": p, "cid": cid, "duration": 20, "part": title}
        for p, cid, title in [
            (1, 123, "intro"),
            (2, 124, "二阶段开始"),
            (3, 125, "三阶段开始"),
        ]
    ]
    body = json.dumps({"code": 0, "data": {"title": "test", "pages": pages}}).encode()
    monkeypatch.setattr(
        "ootss.series.urllib.request.urlopen", lambda *a, **kw: io.BytesIO(body)
    )
    data = discover("manifest.json")
    assert data["parts"][0]["file"] == str(recovered)
    assert data["parts"][0]["download_status"] == "complete"
    assert [p["stage"] for p in data["parts"]] == [1, 2, 3]


def test_atlas_uses_only_observed_confirmed_phase_visits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_download(url, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        return path

    monkeypatch.setattr("ootss.atlas.download", fake_download)
    write_json(
        "cache/map/catalog.json",
        {
            "commit": "test",
            "levels": [
                {
                    "level_id": "seen",
                    "area": "area",
                    "map_url": "https://example.test/#seen",
                    "entries": [{"coordinates": [2, 3, 0]}],
                },
                {
                    "level_id": "unseen",
                    "area": "area",
                    "map_url": "https://example.test/#unseen",
                    "entries": [{"coordinates": [4, 5, 0]}],
                },
            ],
        },
    )
    write_json(
        "results/series/manifest.json",
        {
            "bvid": "BVtest",
            "parts": [
                {
                    "part_number": 1,
                    "title": "phase 1",
                    "duration": 20,
                    "download_status": "complete",
                },
                {
                    "part_number": 25,
                    "title": "phase 2",
                    "duration": 20,
                    "download_status": "complete",
                },
            ],
        },
    )
    event = {
        "event_id": "one",
        "level_id": "seen",
        "review_status": "confirmed",
        "evidence": ["visual"],
        "puzzle_start_time": 1,
        "puzzle_end_time": 5,
    }
    write_json(
        "results/p1/reviewed.json",
        {
            "video_bvid": "BVtest",
            "part_number": 1,
            "duration": 20,
            "events": [
                event,
                {
                    **event,
                    "event_id": "two",
                    "puzzle_start_time": 10,
                    "puzzle_end_time": 15,
                },
            ],
        },
    )
    write_json(
        "results/p25/reviewed.json",
        {
            "video_bvid": "BVtest",
            "part_number": 25,
            "duration": 20,
            "events": [{**event, "level_id": "unseen"}],
        },
    )
    data = build_atlas("atlas", parts=[1], offline_zoom=0)
    assert [r["level_id"] for r in data["levels"]] == ["seen"]
    assert len(data["levels"][0]["visits"]) == 2
    assert data["levels"][0]["visits"][1]["url"].endswith("p=1&t=10")
    assert read_json("atlas/index.json")["map_commit"] == "test"


def test_static_map_contains_real_terrain_image(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_terrain(bounds, out, **kwargs):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (512, 512), "#654321").save(out)
        return out

    monkeypatch.setattr("ootss.exporting.terrain_crop", fake_terrain)
    rows = [
        {
            "level_id": "a",
            "puzzle_start_time": 1,
            "map_entries": [{"coordinates": [80, 120, 0]}],
            "video_url": "https://example.test/?p=1&t=1",
        }
    ]
    # Widely separated visits need enough panel height; P5 previously produced
    # a negative terrain resize with the fixed canvas height.
    rows.extend(
        {
            **rows[0],
            "level_id": f"far_{x}",
            "map_entries": [{"coordinates": [x, 30, 0]}],
        }
        for x in range(0, 160, 12)
    )
    draw_map(rows, tmp_path, background=True)
    assert "data:image/jpeg;base64," in (tmp_path / "map.svg").read_text()
    assert (
        'href="https://example.test/?p=1&amp;t=1"' in (tmp_path / "map.svg").read_text()
    )


def test_combined_atlas_groups_later_returns_by_map_and_keeps_video_ordinals(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def fake_download(url, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        return path

    monkeypatch.setattr("ootss.atlas.download", fake_download)
    levels = [
        {
            "level_id": name,
            "area": "area",
            "map_layer": world,
            "entries": [{"coordinates": [80, 69, z]}],
            "map_url": f"https://example.test/#{name}",
        }
        for name, world, z in [
            ("first", "overworld", 0),
            ("late", "overworld", 0),
            ("air", "sky", 33),
            ("below", "underworld", -24),
            ("unseen", "sky", 33),
        ]
    ]
    write_json("catalog.json", {"commit": "test", "levels": levels})
    write_json(
        "data/annotations.json",
        {
            "levels": {},
            "regions": {
                "overworld:0,0": {"title": "地面中心"},
                "sky:0,0": {"title": "天空中心"},
            },
        },
    )
    parts = [
        {
            "part_number": n,
            "stage": stage,
            "title": f"stage {stage}",
            "duration": 30,
            "download_status": "complete",
        }
        for n, stage in [(1, 1), (25, 2), (45, 3)]
    ]
    write_json("results/series/manifest.json", {"bvid": "BVtest", "parts": parts})
    for n, names in [(1, ["first"]), (25, ["air", "late"]), (45, ["below"])]:
        events = [
            {
                "event_id": f"p{n}-{i}",
                "level_id": name,
                "review_status": "confirmed",
                "evidence": ["fixture visual"],
                "context": "开发回顾示例" if n == 45 else None,
                "puzzle_start_time": 1 + i * 10,
                "puzzle_end_time": 5 + i * 10,
            }
            for i, name in enumerate(names)
        ]
        if n == 25:
            events.append(
                {
                    "event_id": "unknown",
                    "level_id": None,
                    "review_status": "unknown",
                    "puzzle_start_time": 22,
                    "puzzle_end_time": 25,
                    "evidence": ["unknown"],
                }
            )
        write_json(
            f"results/p{n}/reviewed.json",
            {
                "video_bvid": "BVtest",
                "part_number": n,
                "duration": 30,
                "events": events,
            },
        )
    data = build_atlas(
        "atlas",
        parts=[1, 25, 45, 68],
        offline_zoom=0,
        catalog_path="catalog.json",
        all_worlds=True,
    )
    assert all(p["part"] != 68 for p in data["parts"])
    maps = {m["map_id"]: m for m in data["maps"]}
    assert [l["level_id"] for l in maps["overworld"]["levels"]] == ["first", "late"]
    assert maps["overworld"]["levels"][1]["visits"][0]["ordinal"] == 2
    assert maps["sky"]["levels"][0]["visits"][0]["ordinal"] == 1
    assert maps["underworld"]["levels"][0]["level_id"] == "below"
    assert maps["overworld"]["regions"][0]["title"] == "地面中心"
    assert maps["sky"]["regions"][0]["title"] == "天空中心"
    assert len(data["unknown_events"]) == 1
    assert maps["underworld"]["levels"][0]["visits"][0]["context"] == "开发回顾示例"
    assert next(p for p in data["parts"] if p["part"] == 25)["visits"] == 2
    assert next(p for p in data["parts"] if p["part"] == 25)["unmapped_count"] == 1
    assert all(l["level_id"] != "unseen" for l in data["levels"])
    assert "sky_64k" in maps["sky"]["tile_url"]
    from hashlib import sha256

    page = (Path("atlas") / "index.html").read_text(encoding="utf-8")
    for filename in ("atlas.css", "atlas.js", "atlas-ui.js"):
        token = sha256((Path("atlas") / filename).read_bytes()).hexdigest()[:12]
        assert f'"{filename}?v={token}"' in page
    assert "map_layer" in (Path("atlas") / "visits.csv").read_text(encoding="utf-8-sig")
