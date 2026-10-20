"""Apply the owner's explicit continuity corrections, preserving replaced records."""

import copy
import hashlib
from collections import defaultdict
from pathlib import Path

from ootss.common import read_json, write_json
from ootss.exporting import validate


def apply_part(review, actions, catalog, metadata):
    if review.get("human_review", {}).get("source_sha256") == metadata["source_sha256"]:
        return review
    result = copy.deepcopy(review)
    originals = {e["event_id"]: e for e in review["events"]}
    by_name = {r["level_id"]: r for r in catalog["levels"]}
    consumed, replacements, exclusions = set(), [], []
    for action in actions:
        ids = action["event_ids"]
        if consumed.intersection(ids):
            raise ValueError("A source event was consumed twice")
        segments = [originals[i] for i in ids]
        consumed.update(ids)
        proof = {
            "type": "human_review",
            "source": metadata["source"],
            "source_sha256": metadata["source_sha256"],
            "items": action["items"],
            "reason": action["reason"],
        }
        if action["kind"] == "world":
            for i, source in enumerate(segments or [None]):
                start = action.get(
                    "start", source["puzzle_start_time"] if source else None
                )
                end = action.get("end", source["puzzle_end_time"] if source else None)
                if (
                    start is None
                    or end is None
                    or not 0 <= start < end <= review["duration"]
                ):
                    raise ValueError("Invalid world segment")
                exclusions.append(
                    {
                        "segment_id": action["target_event_id"] or f"world-{ids[i]}",
                        "kind": "world",
                        "start": start,
                        "end": end,
                        "source_event_ids": [source["event_id"]] if source else [],
                        "evidence": [proof],
                    }
                )
            continue
        if action["kind"] not in {"merge", "identify"}:
            raise ValueError("Unknown correction action")
        event = copy.deepcopy(originals[action["target_event_id"]])
        level = by_name[action["level_id"]]
        start = action.get("start", min(e["puzzle_start_time"] for e in segments))
        end = action.get("end", max(e["puzzle_end_time"] for e in segments))
        event.update(
            level_id=level["level_id"],
            map_layer=level["map_layer"],
            puzzle_start_time=start,
            puzzle_end_time=end,
            review_status="confirmed",
            status="visited",
            reviewer="User continuity/identity review (docs/校对.md)",
            source_event_ids=ids,
            outcome=event.get("outcome", "unknown"),
        )
        if (
            event.get("entry_transition_time") is not None
            and event["entry_transition_time"] > start
        ):
            event["entry_transition_time"] = None
        if start == 0:
            event["entry_transition_time"] = None
        event["exit_time"] = end if end < review["duration"] else None
        # A retracted match/old warning must not describe the newly confirmed visit.
        for key in ("audit_note", "audit_anchor", "superseded_identification"):
            event.pop(key, None)
        event["puzzle_match"] = {
            "level_id": level["level_id"],
            "status": "human_confirmed",
            "method": "owner_identity_and_continuity_review",
        }
        event.setdefault("evidence", []).append(proof)
        event.setdefault("manual_corrections", []).append(proof)
        replacements.append(event)
    kept = [copy.deepcopy(e) for e in review["events"] if e["event_id"] not in consumed]
    result["events"] = sorted(kept + replacements, key=lambda e: e["puzzle_start_time"])
    result.setdefault("superseded_events", []).extend(
        {"event": copy.deepcopy(e), "replaced_by_review": metadata["source_sha256"]}
        for e in review["events"]
        if e["event_id"] in consumed
    )
    result.setdefault("excluded_segments", []).extend(exclusions)
    result.setdefault("revision_history", []).append(
        {
            "previous_review_note": review.get("review_note"),
            "source": metadata["source"],
            "items": sorted({i for a in actions for i in a["items"]}),
        }
    )
    result["human_review"] = metadata
    result["review_note"] = (
        "已按用户docs/校对.md修订身份和连续区间。未切关的匹配窗合并为一次访问；"
        "明确未进关的大世界片段移入excluded_segments，不再列为未知关卡。"
        "原片段完整记录保存在superseded_events。具体依据见各事件human_review证据。"
    )
    validate(result, catalog)
    for a, b in zip(result["events"], result["events"][1:]):
        if a["puzzle_end_time"] > b["puzzle_start_time"]:
            raise ValueError(
                f"Overlapping corrected events: {a['event_id']} / {b['event_id']}"
            )
    return result


def main():
    plan = read_json("data/human_corrections.json")
    if (
        hashlib.sha256(
            Path(plan["source"]).read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        != plan["source_sha256"]
    ):
        raise ValueError(
            "The owner's notes changed; reconcile the action plan before applying"
        )
    metadata = {k: plan[k] for k in ("source", "source_sha256", "item_count")}
    catalog = read_json("cache/map/catalog_all.json")
    grouped = defaultdict(list)
    for action in plan["actions"]:
        grouped[action["part"]].append(action)
    pending = {}
    for part, actions in grouped.items():
        pending[part] = apply_part(
            read_json(f"results/p{part}/reviewed.json"), actions, catalog, metadata
        )
    # Validate every part before changing any source file.
    for part, review in pending.items():
        write_json(f"results/p{part}/reviewed.json", review)
    decisions = read_json("data/audit_decisions.json")
    for decision in decisions["decisions"]:
        for action in plan["actions"]:
            if (
                decision["event_id"] in action["event_ids"]
                and action["kind"] == "merge"
            ):
                decision.update(
                    action="merged_after_human_review",
                    level_id=action["level_id"],
                    candidates=[action["level_id"]],
                    merged_into=action["target_event_id"],
                    reason=action["reason"]
                    + " 用户已确认无切关，旧片段已并回连续访问。",
                )
    decisions["human_review"] = metadata
    for action in plan["actions"]:
        key = str(action["part"])
        old_notes = decisions.get("repeat_notes", {}).get(key, {})
        if action["kind"] == "merge":
            old_notes.pop(action["level_id"], None)
        if not old_notes:
            decisions.get("repeat_notes", {}).pop(key, None)
    write_json("data/audit_decisions.json", decisions)
    write_json("results/audit/human_review.json", plan)
    print(
        f"Applied {plan['item_count']} notes in {len(plan['actions'])} actions to {len(pending)} parts"
    )


if __name__ == "__main__":
    main()
