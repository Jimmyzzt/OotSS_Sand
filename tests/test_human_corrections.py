import pytest

from scripts.apply_human_corrections import apply_part


def fixture_review():
    return {
        "duration": 40,
        "events": [
            {
                "event_id": "a",
                "level_id": "known",
                "review_status": "confirmed",
                "puzzle_start_time": 2,
                "puzzle_end_time": 5,
                "evidence": [{"reason": "reference"}],
                "audit_note": "old suspicion",
                "outcome": "unknown",
            },
            {
                "event_id": "b",
                "level_id": None,
                "review_status": "unknown",
                "puzzle_start_time": 6,
                "puzzle_end_time": 20,
                "evidence": [{"reason": "unidentified room"}],
            },
            {
                "event_id": "c",
                "level_id": None,
                "review_status": "unknown",
                "puzzle_start_time": 25,
                "puzzle_end_time": 30,
                "evidence": [],
            },
        ],
    }


def fixture_actions():
    return [
        {
            "kind": "merge",
            "target_event_id": "a",
            "level_id": "known",
            "event_ids": ["a", "b"],
            "items": [2],
            "reason": "No level switch",
            "end": 20,
        },
        {
            "kind": "world",
            "target_event_id": None,
            "event_ids": ["c"],
            "items": [3],
            "reason": "In the world, no entry",
        },
    ]


CATALOG = {"levels": [{"level_id": "known", "map_layer": "underworld"}]}
META = {"source": "docs/校对.md", "source_sha256": "fixture"}


def test_human_continuity_merges_unknown_rooms_and_excludes_world_without_losing_sources():
    original = fixture_review()
    result = apply_part(original, fixture_actions(), CATALOG, META)
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert (event["puzzle_start_time"], event["puzzle_end_time"]) == (2, 20)
    assert event["source_event_ids"] == ["a", "b"]
    assert event["outcome"] == "unknown"
    assert "audit_note" not in event
    assert len(result["superseded_events"]) == 3
    assert result["excluded_segments"][0]["kind"] == "world"
    assert len(original["events"]) == 3
    assert apply_part(result, fixture_actions(), CATALOG, META) == result


def test_human_merge_rejects_an_interval_overlapping_an_unmerged_event():
    actions = fixture_actions()[:1]
    actions[0]["end"] = 28
    with pytest.raises(ValueError, match="Overlapping corrected events"):
        apply_part(fixture_review(), actions, CATALOG, META)


def test_a_source_event_cannot_be_silently_consumed_twice():
    actions = fixture_actions()
    actions.append({**actions[0]})
    with pytest.raises(ValueError, match="consumed twice"):
        apply_part(fixture_review(), actions, CATALOG, META)
