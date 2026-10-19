"""Reproduce this session's evidence packets; not a generic video recognizer."""

from ootss.common import read_json, write_json
from ootss.overworld import check
from ootss.video import contact_sheet


def main():
    contexts = [
        (9, "heroes3_10", "heroes3"),
        (643, "wizard_and_druid_alt", "heroes3"),
        (822, "heroes3_1_v3", "heroes3"),
        (985, "heroes3_5", "heroes3"),
        (1513, "heroes3_14_v3", "heroes3"),
        (1724, "compactor_v2", "heroes3"),
        (1900, "gatekeeping_v3", "heroes3"),
        (2032, "heroes3_21_condensed", "heroes3"),
        (2269, "side_slide_intro_v2", "side"),
        (2512, "side_kick", "side"),
        (2587, "multipush_for_me2", "side"),
        (2703, "dragon_on_the_wall", "side"),
        (2858, "victory_lap", "victory"),
    ]
    bounds = {
        "heroes3": [69, 113, 90, 129],
        "side": [53, 104, 69, 117],
        "victory": [75, 73, 85, 83],
    }
    rows = []
    for time, level, region in contexts:
        rows.append(
            check(
                "runs/p4",
                time,
                level,
                f"runs/p4/terrain_{region}_raw.jpg",
                bounds[region],
                f"runs/p4/world/{level}",
            )
        )
    write_json("runs/p4/world_checks.json", rows)
    items = [(r["level_id"], r.get("overlay", r["approach_image"])) for r in rows]
    for o in range(0, len(items), 6):
        contact_sheet(
            items[o : o + 6],
            f"runs/p4/world_{o // 6:02d}.jpg",
            columns=2,
            cell_width=640,
        )
    cat = read_json("cache/map/catalog.json")
    write_json(
        "runs/p4/provenance.json",
        {"catalog_commit": cat["commit"], "contexts": contexts, "bounds": bounds},
    )
    print([(r["level_id"], r["inliers"], r["status"]) for r in rows])


if __name__ == "__main__":
    main()
