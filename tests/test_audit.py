from pathlib import Path

from PIL import Image

from ootss.common import write_json
from scripts.audit_differences import generate


def test_audit_keeps_unknowns_out_of_observed_and_excludes_hidden_part(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    image = tmp_path / "reference.webp"
    Image.new("RGB", (160, 90)).save(image)
    levels = [
        {
            "level_id": name,
            "area": "area",
            "map_layer": "overworld",
            "entries": [{"coordinates": [x, 69, 0]}],
            "reference": str(image),
            "map_url": f"https://example.test/#{name}",
        }
        for name, x in [("seen", 80), ("candidate_only", 81), ("hidden_only", 82)]
    ]
    write_json("catalog.json", {"commit": "fixture", "levels": levels})
    write_json("data/audit_decisions.json", {"decisions": []})
    write_json(
        "data/creator_locations.json",
        {"source": "fixture", "source_sha256": "fixture", "entries": []},
    )
    write_json("data/video_links.json", {"parts": {"2": {"part": 3}}})
    write_json("results/series/manifest.json", {"bvid": "BVfixture"})
    for part in range(1, 69):
        events = []
        if part in [1, 68]:
            events = [
                {
                    "event_id": f"p{part}-{i}",
                    "level_id": "seen" if part == 1 else "hidden_only",
                    "review_status": "confirmed",
                    "puzzle_start_time": i * 5,
                    "puzzle_end_time": i * 5 + 3,
                    "evidence": [{"reason": "visual fixture"}],
                }
                for i in range(2)
            ]
        if part == 2:
            events = [
                {
                    "event_id": "pending",
                    "level_id": "candidate_only",
                    "review_status": "candidate",
                    "puzzle_start_time": 1,
                    "puzzle_end_time": 3,
                    "evidence": [],
                }
            ]
        write_json(f"results/p{part}/reviewed.json", {"duration": 30, "events": events})
    data = generate(catalog="catalog.json")
    assert data["counts"]["mapped_entries"] == 1
    assert data["counts"]["time_records"] == 2
    assert data["counts"]["repeated_identity_groups"] == 1
    assert {e["level_id"] for e in data["absent_catalog_entries"]} == {
        "candidate_only",
        "hidden_only",
    }
    assert data["unlocated_segments"][0]["url"].endswith("p=3&t=1")
    assert not any(
        e["part"] == 68 for r in data["repeated_identities"] for e in r["events"]
    )
    assert Path("results/worlds/audit.html").exists()
    # Chapters of one owner-confirmed visit are not suspicious repeated identities.
    review = {
        "duration": 30,
        "events": [
            {
                "event_id": f"chapter-{i}",
                "level_id": "seen",
                "review_status": "confirmed",
                "puzzle_start_time": i * 5,
                "puzzle_end_time": i * 5 + 3,
                "evidence": [{"reason": "owner confirmed chapter"}],
                "chapter_group": "seen",
            }
            for i in range(4)
        ],
    }
    write_json("results/p1/reviewed.json", review)
    data = generate(catalog="catalog.json")
    assert data["counts"]["time_records"] == 4
    assert data["counts"]["repeated_identity_groups"] == 0
