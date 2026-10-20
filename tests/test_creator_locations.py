import pytest

from scripts.apply_creator_locations import apply_part


def test_missing_location_split_preserves_source_and_prior_owner_review():
    review = {
        "duration": 30,
        "human_review": {"source_sha256": "previous-owner-notes"},
        "excluded_segments": [{"kind": "world", "start": 25, "end": 30}],
        "events": [
            {
                "event_id": "old",
                "level_id": "first",
                "review_status": "confirmed",
                "puzzle_start_time": 0,
                "puzzle_end_time": 20,
                "evidence": [{"reason": "Mistaken continuity claim"}],
            }
        ],
    }
    catalog = {
        "levels": [
            {"level_id": name, "map_layer": "overworld"} for name in ["first", "second"]
        ]
    }
    metadata = {"source": "creator-notes", "source_sha256": "new-source"}
    additions = [
        {
            "event_id": "new",
            "level_id": "second",
            "start": 10,
            "end": 20,
            "reported_start": 10,
            "item": 1,
            "reason": "Different initial roles and visible exit/re-entry",
            "evidence": ["comparison.jpg"],
        }
    ]
    changes = [
        {
            "event_id": "old",
            "expected_level_id": "first",
            "fields": {"puzzle_end_time": 8},
            "replace_evidence": True,
            "proof": {"reason": "Visible return to world at 8"},
        }
    ]
    with pytest.raises(ValueError, match="Overlapping events"):
        apply_part(review, additions, [], catalog, metadata)
    result = apply_part(review, additions, changes, catalog, metadata)
    assert result["superseded_events"][0]["event"] == review["events"][0]
    assert result["human_review"] == review["human_review"]
    assert result["excluded_segments"] == review["excluded_segments"]
    assert review["events"][0]["puzzle_end_time"] == 20
    assert result["events"][1]["outcome"] == "unknown"
    assert apply_part(result, additions, changes, catalog, metadata) == result
