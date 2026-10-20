"""Higher-resolution spot checks of gaps left by low-resolution retrieval."""

from pathlib import Path

from .common import read_json, stamp, write_json
from .matching import Matcher
from .video import contact_sheet, frame


def recover(part, step=25, catalog_path="cache/map/catalog.json"):
    run = Path(f"runs/p{part}")
    source = read_json(run / "scan.json")
    review_path = Path(f"results/p{part}/reviewed.json")
    review = read_json(
        review_path if review_path.exists() else Path(f"results/p{part}/proposed.json")
    )
    ranges = sorted(
        (e["puzzle_start_time"], e["puzzle_end_time"])
        for e in review["events"]
        if e["review_status"] == "confirmed"
    )
    gaps = []
    previous = 0
    for a, b in ranges + [(source["duration"], source["duration"])]:
        if a - previous > 8:
            gaps.append((previous, a))
        previous = max(previous, b)
    matcher = Matcher(catalog_path)
    by_name = {r["level_id"]: r for r in matcher.rows}
    records = []
    pairs = []
    for a, b in gaps:
        times = (
            [(a + b) / 2]
            if b - a < step
            else list(range(round(a + 5), round(b - 4), step))
        )
        for t in times:
            path = frame(
                source["video"], round(t, 3), run / f"recovery/{t:09.3f}.jpg", 640
            )
            cache = path.with_suffix(".match.json")
            result = (
                read_json(cache)
                if cache.exists()
                else matcher.search(path, top=5, refine=24)
            )
            write_json(cache, result)
            best = result["candidates"][0]
            record = {"time": t, "gap": [a, b], "image": str(path.resolve()), **result}
            records.append(record)
            if best["sift_inliers"] >= 20 and best["phash_distance"] <= 18:
                pairs.extend(
                    [
                        (
                            f"{stamp(t)} VIDEO {best['level_id']} sift={best['sift_inliers']}",
                            path,
                        ),
                        (
                            f"REF {best['level_id']}",
                            by_name[best["level_id"]]["reference"],
                        ),
                    ]
                )
    write_json(
        run / "recovery.json",
        {
            "part": part,
            "gaps": gaps,
            "samples": records,
            "note": "Unreviewed spot checks. Full timeline continuity and visual comparison still required.",
        },
    )
    for o in range(0, len(pairs), 12):
        contact_sheet(
            pairs[o : o + 12],
            f"results/p{part}/evidence/recovery_{o // 12:02d}.jpg",
            columns=2,
            cell_width=426,
        )
    print(
        f"P{part}: {len(gaps)} gaps, {len(records)} HQ spot checks, {len(pairs) // 2} strong candidate frames",
        flush=True,
    )
    return records


if __name__ == "__main__":
    import sys

    for part in sys.argv[1:]:
        recover(int(part))
