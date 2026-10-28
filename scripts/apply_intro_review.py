"""Apply the bounded visual intro review; preserve all previous source decisions."""

import copy
import hashlib
from itertools import pairwise
from pathlib import Path

from ootss.common import read_json, write_json
from ootss.exporting import validate
from ootss.maps import with_intro


def apply():
    plan_path = Path("data/intro_visits.json")
    plan = read_json(plan_path)
    digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    path = Path("results/p68/reviewed.json")
    review = read_json(path)
    catalog = with_intro(read_json("cache/map/catalog_all.json"))
    write_json("cache/map/catalog_all.json", catalog)
    if review.get("intro_review", {}).get("source_sha256") == digest:
        validate(review, catalog)
        return review
    if review.get("intro_review"):
        raise ValueError("Intro plan changed: explicitly re-review before replacing")
    review.setdefault("superseded_reviews", []).append(
        {
            "reason": "New independent upstream intro markers and explicit owner authorization",
            **copy.deepcopy(review),
        }
    )
    old = {e["event_id"]: e for e in review["events"]}
    events = []
    for entry in plan["events"]:
        a, b = entry["start"], entry["end"]
        event = copy.deepcopy(old.get(entry["event_id"], {}))
        event.update(
            event_id=entry["event_id"],
            level_id=entry["level_id"],
            puzzle_start_time=a,
            puzzle_end_time=b,
            entry_transition_time=a,
            exit_time=b,
            overworld_approach_time=None,
            review_status="confirmed",
            status="visited",
            outcome="unknown",
            reviewer="Codex bounded visual intro comparison",
            context="开发回顾：序章独立示例",
            map_layer="intro",
            intro_map_commit=plan["map_commit"],
            timing_uncertainty_seconds=1,
            overworld_match={
                "status": "no_overworld_context",
                "reason": "Video demonstrates the matching entry in the intro development gallery, not its original physical-world entrance.",
            },
            puzzle_match={
                "status": "visually_confirmed",
                "level_id": entry["level_id"],
            },
            evidence=[
                {
                    "type": "intro_layout_and_continuity",
                    "time": entry["sample_time"],
                    "image": entry["evidence_image"],
                    "source_level_id": entry["source_level_id"],
                    "reason": entry["reason"],
                },
                {
                    "type": "cached_timeline_review",
                    "scan": plan["scan"],
                    "reason": "All cached 5-second contact sheets inspected; bounded 1-second exit checks exclude return-to-gallery and menus. Early textures can differ; identity uses geometry, roles, mechanism placement and gallery order. No old-world coordinates reused.",
                },
            ],
        )
        events.append(event)
    events.sort(key=lambda e: e["puzzle_start_time"])
    if any(a["puzzle_end_time"] > b["puzzle_start_time"] for a, b in pairwise(events)):
        raise ValueError("Overlapping intro visits")
    review["events"] = events
    # Gaps include gallery navigation, transitions and settings, never new puzzles.
    gaps = []
    start = 0
    for e in events:
        if start < e["puzzle_start_time"]:
            gaps.append(
                {
                    "start": start,
                    "end": e["puzzle_start_time"],
                    "kind": "world",
                    "reason": "Gallery navigation / transition / menu; not another Level_Entry",
                }
            )
        start = e["puzzle_end_time"]
    gaps.append(
        {
            "start": start,
            "end": review["duration"],
            "kind": "world",
            "reason": "World tour, development diagrams and hidden recording; no additional independent intro entry.",
        }
    )
    review["excluded_segments"] = gaps
    review["review_note"] = (
        "序章新标记专项校对：复用已缓存全时间轴及正式版10段审核，补充开发版14段。24个入口仅归入序章，同构正式版不再投射回旧三地图。P67既有人工排除的大世界片段保持排除。"
    )
    review["intro_review"] = {
        "source": "data/intro_visits.json",
        "source_sha256": digest,
        "map_commit": plan["map_commit"],
        "authorization": plan["authorization"],
    }
    validate(review, catalog)
    write_json(path, review)
    return review


if __name__ == "__main__":
    print(f"Intro review: {len(apply()['events'])} visits")
