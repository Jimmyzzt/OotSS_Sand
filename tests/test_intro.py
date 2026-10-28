from pathlib import Path

from ootss.common import read_json
from ootss.exporting import validate
from ootss.maps import with_intro

ROOT = Path(__file__).resolve().parents[1]


def test_intro_review_covers_new_entries_without_reusing_old_world_visits(monkeypatch):
    monkeypatch.chdir(ROOT)
    supplement = read_json("data/intro_map.json")
    base = {
        "commit": "base-snapshot",
        "levels": [{"level_id": "heroes1_7_v2", "map_layer": "overworld"}],
    }
    catalog = with_intro(base, fetch=False)
    assert catalog["commit"] == "base-snapshot"
    assert len(catalog["levels"]) == 27
    assert catalog["levels"][0] == base["levels"][0]
    # Re-importing is idempotent and leaves both namespaced identities present.
    assert with_intro(catalog, fetch=False) == catalog
    intro = {l["level_id"]: l for l in supplement["levels"]}
    p68 = read_json("results/p68/reviewed.json")
    assert len(p68["events"]) == 24
    validate(p68, catalog={"levels": list(intro.values())})
    assert all(e["map_layer"] == "intro" for e in p68["events"])
    assert len(p68["superseded_reviews"][0]["events"]) == 10
    p44 = read_json("results/p44/reviewed.json")
    found = {e["level_id"] for e in p44["events"] if e["level_id"] in intro}
    assert found == {"jenga_dispenser", "wizards_true_nature"}
    assert {e["level_id"] for e in p68["events"]} | found == set(intro)
    assert all(l["save_level_id"] is None for l in intro.values())
    assert not any(
        e["level_id"] in {"heroes1_7_v2", "triple_gate"} for e in p68["events"]
    )
    assert supplement["bounds"] == [-50, -63, 140, 126]
