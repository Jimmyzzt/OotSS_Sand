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
