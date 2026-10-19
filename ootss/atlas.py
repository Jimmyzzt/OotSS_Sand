"""Build a local Leaflet atlas from reviewed visits; no server or recognition app."""

import concurrent.futures
import csv
import json
import shutil
from pathlib import Path

from PIL import Image

from .common import read_json, write_json
from .exporting import validate, video_url
from .maps import ASSETS, download


def build_atlas(out="results/stage1", parts=range(1, 25), offline_zoom=3):
    parts = list(parts)
    out = Path(out)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in ("leaflet.js", "leaflet.css"):
        cached = download(
            f"https://unpkg.com/leaflet@1.9.4/dist/{filename}",
            Path("cache/leaflet") / filename,
        )
        shutil.copyfile(cached, assets / filename)
    license_file = download(
        "https://raw.githubusercontent.com/Leaflet/Leaflet/v1.9.4/LICENSE",
        Path("cache/leaflet/LICENSE"),
    )
    shutil.copyfile(license_file, assets / "LEAFLET-LICENSE.txt")
    tiles = [
        (z, y, x)
        for z in range(offline_zoom + 1)
        for y in range(2**z)
        for x in range(2**z)
    ]

    def fetch(coords):
        z, y, x = coords
        relative = f"tiles/overworld_64k/{z}/{y}/{x}.webp"
        cached = download(f"{ASSETS}/{relative}", Path("cache/map") / relative)
        target = assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(cached, target)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, tiles))
    catalog = read_json("cache/map/catalog.json")
    by_name = {r["level_id"]: r for r in catalog["levels"]}
    manifest = read_json("results/series/manifest.json")
    part_rows = []
    levels = {}
    unknown = []
    for part in parts:
        row = next(r for r in manifest["parts"] if r["part_number"] == part)
        path = Path(f"results/p{part}/reviewed.json")
        review = read_json(path) if path.exists() else None
        part_rows.append(
            {
                "part": part,
                "title": row["title"],
                "duration": row["duration"],
                "download_status": row["download_status"],
                "reviewed": review is not None,
                "visits": len(review["events"]) if review else None,
            }
        )
        if not review:
            continue
        if review["part_number"] != part or review["video_bvid"] != manifest["bvid"]:
            raise ValueError(f"P{part} review belongs to a different video/part")
        validate(review, catalog)
        if review.get("map_commit", catalog["commit"]) != catalog["commit"]:
            raise ValueError(f"P{part} uses a different map snapshot")
        for event in review["events"]:
            name = event.get("level_id")
            if event["review_status"] != "confirmed" or name not in by_name:
                unknown.append({"part": part, **event})
                continue
            level = by_name[name]
            item = levels.setdefault(
                name,
                {
                    "level_id": name,
                    "area": level["area"],
                    "entries": level["entries"],
                    "map_url": level["map_url"],
                    "visits": [],
                },
            )
            item["visits"].append(
                {
                    "part": part,
                    "event_id": event["event_id"],
                    "start": event["puzzle_start_time"],
                    "end": event["puzzle_end_time"],
                    "url": video_url(
                        review["video_bvid"], part, event["puzzle_start_time"]
                    ),
                    "reviewer": event.get("reviewer"),
                    "uncertainty": event.get("timing_uncertainty_seconds"),
                }
            )
    for level in levels.values():
        reference = Path(by_name[level["level_id"]].get("reference", ""))
        if reference.is_file():
            relative = f"previews/{level['level_id']}.webp"
            target = assets / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with Image.open(reference) as image:
                    image.thumbnail((480, 270))
                    image.save(target, quality=78)
            level["preview"] = "assets/" + relative
    data = {
        "bvid": manifest["bvid"],
        "map_commit": catalog["commit"],
        "scope": f"塞德莎攻略 P{min(parts)}–P{max(parts)}，仅按经画面对照的实际访问收录；不把全部Overworld入口当作一阶段关卡。",
        "parts": part_rows,
        "levels": list(levels.values()),
        "unknown_events": unknown,
        "catalog_level_count": len(by_name),
        "not_observed": sorted(set(by_name) - set(levels)),
        "offline_zoom": offline_zoom,
        "tile_url": f"{ASSETS}/tiles/overworld_64k/{{z}}/{{y}}/{{x}}.webp",
    }
    write_json(out / "index.json", data)
    with (out / "visits.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "part",
                "event_id",
                "level_id",
                "area",
                "coordinates",
                "start",
                "end",
                "url",
                "map_url",
            ],
        )
        writer.writeheader()
        for level in data["levels"]:
            for visit in level["visits"]:
                writer.writerow(
                    {
                        **{
                            k: visit[k]
                            for k in ("part", "event_id", "start", "end", "url")
                        },
                        "level_id": level["level_id"],
                        "area": level["area"],
                        "coordinates": json.dumps(
                            [e["coordinates"] for e in level["entries"]]
                        ),
                        "map_url": level["map_url"],
                    }
                )
    template = (Path(__file__).parent / "templates/atlas.html").read_text(
        encoding="utf-8"
    )
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    (out / "index.html").write_text(
        template.replace("__ATLAS_DATA__", payload), encoding="utf-8"
    )
    print(
        f"Atlas: {len(levels)} levels, {sum(len(l['visits']) for l in levels.values())} visits, {sum(p['reviewed'] for p in part_rows)}/{len(part_rows)} parts reviewed",
        flush=True,
    )
    return data


if __name__ == "__main__":
    import sys

    build_atlas(
        sys.argv[1] if len(sys.argv) > 1 else "results/stage1",
        [4] if len(sys.argv) > 2 and sys.argv[2] == "p4" else range(1, 25),
    )
