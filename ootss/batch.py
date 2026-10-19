"""Prepare bounded candidate packets. No machine proposal is auto-confirmed."""

from pathlib import Path

from .common import read_json, stamp, write_json
from .matching import match_run
from .video import contact_sheet, scan


def propose(part, manifest_path="results/series/manifest.json"):
    manifest = read_json(manifest_path)
    row = next(r for r in manifest["parts"] if r["part_number"] == part)
    if row["download_status"] != "complete":
        raise ValueError(f"P{part:02d} is not downloaded")
    run = Path(f"runs/p{part}")
    if part == 4:
        return read_json("results/p4/reviewed.json")
    scan_data = scan(row["file"], run, interval=5, black_min=0.125)
    matches = match_run(run)
    catalog = read_json("cache/map/catalog.json")
    levels = {r["level_id"]: r for r in catalog["levels"]}
    groups = []
    for sample in matches["samples"]:
        best = sample["candidates"][0]
        if best["sift_inliers"] < 12 or best["phash_distance"] > 18:
            continue
        if groups:
            previous = groups[-1][-1]
            gap_black = [
                t
                for t in scan_data["transitions"]
                if previous["time"] < t["start"] < sample["time"]
            ]
            if (
                previous["candidates"][0]["level_id"] == best["level_id"]
                and sample["time"] - previous["time"] <= 15
                and len(gap_black) < 2
            ):
                groups[-1].append(sample)
                continue
        groups.append([sample])
    events, pairs = [], []
    for i, group in enumerate(groups, 1):
        first, last = group[0]["time"], group[-1]["time"]
        representative = max(group, key=lambda s: s["candidates"][0]["sift_inliers"])
        name = representative["candidates"][0]["level_id"]
        entry = [t for t in scan_data["transitions"] if 0 <= first - t["end"] <= 10]
        exit = [t for t in scan_data["transitions"] if 0 <= t["start"] - last <= 10]
        enter, leave = entry[-1] if entry else None, exit[0] if exit else None
        start = enter["end"] if enter else max(0, first - 5)
        end = leave["start"] if leave else min(last + 5, scan_data["duration"])
        events.append(
            {
                "event_id": f"p{part}-{i:03d}",
                "level_id": name,
                "puzzle_start_time": start,
                "puzzle_end_time": end,
                "entry_transition_time": enter["start"] if enter else None,
                "exit_time": leave["end"] if leave else None,
                "overworld_approach_time": None,
                "review_status": "candidate",
                "status": "possible_visit",
                "outcome": "unknown",
                "timing_uncertainty_seconds": 0.5 if enter and leave else 5,
                "candidate_levels": representative["candidates"],
                "puzzle_match": {
                    **representative["candidates"][0],
                    "consistent_samples": len(group),
                },
                "overworld_match": {"status": "unverified"},
                "evidence": [
                    {
                        "type": "candidate_layout",
                        "image": representative["image"],
                        "time": representative["time"],
                        "reference": levels[name]["reference"],
                        "first_sample": first,
                        "last_sample": last,
                        "sample_count": len(group),
                    }
                ],
                "evidence_gallery": f"evidence/candidates_{(i - 1) // 5:02d}.jpg",
                "manual_corrections": [],
            }
        )
        pairs.extend(
            [
                (
                    f"{i:03d} VIDEO {stamp(representative['time'])} {name}",
                    representative["image"],
                ),
                (f"{i:03d} REF {name}", levels[name]["reference"]),
            ]
        )
    result = {
        "schema_version": 1,
        "video_bvid": manifest["bvid"],
        "part_number": part,
        "duration": scan_data["duration"],
        "video": row["file"],
        "title": row["title"],
        "stage": row["stage"],
        "map_commit": catalog["commit"],
        "review_note": "Unreviewed machine proposals; require bounded visual comparison, reject false matches, inspect unknown spans.",
        "events": events,
    }
    out = Path(f"results/p{part}")
    write_json(out / "proposed.json", result)
    for offset in range(0, len(pairs), 10):
        contact_sheet(
            pairs[offset : offset + 10],
            out / f"evidence/candidates_{offset // 10:02d}.jpg",
            columns=2,
            cell_width=426,
        )
    write_json(
        run / "proposal_summary.json",
        [
            {
                "event_id": e["event_id"],
                "level_id": e["level_id"],
                "start": e["puzzle_start_time"],
                "end": e["puzzle_end_time"],
                "samples": e["puzzle_match"]["consistent_samples"],
                "inliers": e["puzzle_match"]["sift_inliers"],
            }
            for e in events
        ],
    )
    print(f"P{part:02d}: {len(events)} proposals, awaiting visual review", flush=True)
    return result


if __name__ == "__main__":
    import sys

    for value in sys.argv[1:]:
        propose(int(value))
