"""Apply the creator's six missing locations and bounded continuity checks."""

import copy
import hashlib
from collections import defaultdict
from pathlib import Path

from ootss.common import read_json, write_json
from ootss.exporting import validate


def apply_part(review, entries, adjustments, catalog, metadata):
    if (
        review.get("creator_review", {}).get("source_sha256")
        == metadata["source_sha256"]
    ):
        return review
    result = copy.deepcopy(review)
    by_id = {e["event_id"]: e for e in result["events"]}
    levels = {e["level_id"]: e for e in catalog["levels"]}
    for change in adjustments:
        event = by_id[change["event_id"]]
        if event["level_id"] != change["expected_level_id"]:
            raise ValueError("Source identity changed; reconcile the location plan")
        result.setdefault("superseded_events", []).append(
            {
                "event": copy.deepcopy(event),
                "replaced_by_review": metadata["source_sha256"],
            }
        )
        event.update(change["fields"])
        if change.get("replace_evidence"):
            event["evidence"] = []
            event["manual_corrections"] = []
        event.setdefault("evidence", []).append(
            {
                "type": "visual_comparison",
                "source": metadata["source"],
                **change["proof"],
            }
        )
        event["reviewer"] = "Creator locations and bounded visual continuity review"
    for entry in entries:
        if entry["event_id"] in by_id:
            raise ValueError("New event ID already exists")
        level = levels[entry["level_id"]]
        event = {
            "event_id": entry["event_id"],
            "level_id": entry["level_id"],
            "map_layer": level["map_layer"],
            "puzzle_start_time": entry["start"],
            "puzzle_end_time": entry["end"],
            "entry_transition_time": entry["start"],
            "exit_time": entry["end"],
            "overworld_approach_time": None,
            "review_status": "confirmed",
            "status": "visited",
            "outcome": "unknown",
            "timing_uncertainty_seconds": 1,
            "reviewer": "Creator locations and bounded visual continuity review",
            "puzzle_match": {
                "level_id": entry["level_id"],
                "status": "human_confirmed",
                "method": "creator_location_and_bounded_visual_review",
            },
            "overworld_match": {"status": "unverified"},
            "evidence": [
                {
                    "type": "creator_location",
                    "source": metadata["source"],
                    "item": entry["item"],
                    "reported_start": entry["reported_start"],
                    "reason": entry["reason"],
                },
                *[
                    {
                        "type": "visual_comparison",
                        "image": f"results/audit/evidence/{name}",
                    }
                    for name in entry["evidence"]
                ],
            ],
        }
        if entry.get("world_check"):
            event["overworld_match"] = entry["world_check"]
        result["events"].append(event)
    result["events"].sort(key=lambda e: e["puzzle_start_time"])
    validate(result, catalog)
    for a, b in zip(result["events"], result["events"][1:]):
        if a["puzzle_end_time"] > b["puzzle_start_time"]:
            raise ValueError(f"Overlapping events: {a['event_id']} / {b['event_id']}")
    result["creator_review"] = metadata
    result.setdefault("revision_history", []).append(metadata)
    return result


def main():
    plan = read_json("data/creator_locations.json")
    digest = hashlib.sha256(
        Path(plan["source"]).read_text(encoding="utf-8").encode()
    ).hexdigest()
    if digest != plan["source_sha256"]:
        raise ValueError("Creator notes changed; reconcile the location plan")
    catalog = read_json("cache/map/catalog_all.json")
    entries, adjustments = defaultdict(list), defaultdict(list)
    for entry in plan["entries"]:
        entries[entry["part"]].append(entry)
    for change in plan["adjustments"]:
        adjustments[change["part"]].append(change)
    metadata = {k: plan[k] for k in ("source", "source_sha256", "item_count")}
    pending = {
        part: apply_part(
            read_json(f"results/p{part}/reviewed.json"),
            entries[part],
            adjustments[part],
            catalog,
            metadata,
        )
        for part in entries.keys() | adjustments.keys()
    }
    for part, review in pending.items():
        write_json(f"results/p{part}/reviewed.json", review)
    print(f"Applied {len(plan['entries'])} missing locations to {len(pending)} parts")


if __name__ == "__main__":
    main()
