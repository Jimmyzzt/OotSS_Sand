from ootss.regions import cell_for, direction, enrich


def test_original_grid_and_mirror_cells():
    assert cell_for([80, 69]) == (0, 0)
    assert cell_for([94, 68]) == (1, 0)
    assert cell_for([109, 80]) == (2, 1)
    assert cell_for([70.5, 75.5]) == (0, 1)
    assert direction(-2, 3) == "北3西2"


def test_unique_part_ordinals_revisits_remap_and_manual_tags():
    def level(name, x, times):
        return {
            "level_id": name,
            "area": "mirror",
            "entries": [{"coordinates": [x, 68, 0]}],
            "visits": [{"part": 5, "start": t, "end": t + 1} for t in times],
        }

    data = {
        "bvid": "BVsource",
        "parts": [{"part": 5}],
        "levels": [level("one", 94, [10, 30]), level("two", 110, [20])],
    }
    features = [
        {
            "properties": {
                "type": "Level_Entry",
                "name": "one",
                "entity_properties": {"mesh": "GAME_OVER_Entry_Hero_Available_A"},
            }
        }
    ]
    enrich(
        data,
        features,
        {"levels": {"two": {"multi_save": True}}},
        {"parts": {"5": {"part": 6}}},
    )
    one, two = data["levels"]
    assert [v["ordinal"] for v in one["visits"]] == [1, 1]
    assert two["visits"][0]["ordinal"] == 2
    assert one["visits"][0]["url"].endswith("p=6&t=10")
    assert one["visits"][0]["source_part"] == 5
    assert one["tags"]["big_star"] and not one["tags"]["multi_save"]
    assert two["tags"]["multi_save"]
    assert data["parts"][0]["level_count"] == 2
    assert [r["region_id"] for r in data["parts"][0]["route"]] == ["1,0", "2,0", "1,0"]


def test_owner_confirmed_end1_chapters_keep_one_ordinal_and_the_old_evidence():
    import json
    from pathlib import Path

    review = json.loads(Path("results/p24/reviewed.json").read_text(encoding="utf-8"))
    events = [e for e in review["events"] if e["level_id"] == "end1"]
    assert [e["puzzle_start_time"] for e in events] == [63, 359, 654, 946]
    assert [e["chapter"] for e in events] == [1, 2, 3, 4]
    assert len(review["superseded_events"]) >= 5
    assert all(e["entry_transition_time"] is None for e in events)
    data = {
        "bvid": "BVsource",
        "parts": [{"part": 24}],
        "levels": [
            {
                "level_id": "end1",
                "area": "endgame1",
                "entries": [{"coordinates": [-15, 147, 0]}],
                "visits": [
                    {
                        "part": 24,
                        "start": e["puzzle_start_time"],
                        "end": e["puzzle_end_time"],
                        "chapter": e["chapter"],
                    }
                    for e in events
                ],
            }
        ],
    }
    enrich(data, links={"parts": {"24": {"part": 25}}})
    visits = data["levels"][0]["visits"]
    assert [v["ordinal"] for v in visits] == [1] * 4
    assert [v["chapter"] for v in visits] == [1, 2, 3, 4]
    assert [v["url"].split("t=")[-1] for v in visits] == ["63", "359", "654", "946"]
