"""Build a local Leaflet atlas from reviewed visits; no server or recognition app."""

import concurrent.futures
import csv
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from .common import read_json, write_json
from .exporting import validate, video_url
from .maps import download, layer, tile_asset_base
from .regions import enrich

WORLD_NAMES = {"overworld": "主世界", "sky": "上方", "underworld": "下方"}


def build_atlas(
    out="results/stage1",
    parts=range(1, 25),
    offline_zoom=3,
    catalog_path="cache/map/catalog.json",
    all_worlds=False,
):
    # P68 is hidden content and is excluded from this map by the owner.
    parts = [p for p in parts if p != 68]
    out = Path(out)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    asset_manifest = Path("data/map_assets.json")
    revision = (
        read_json(asset_manifest).get("tileset_revision")
        if asset_manifest.exists()
        else None
    )
    tile_base = tile_asset_base(revision)
    tile_cache = Path("cache/map")
    if revision:
        tile_cache = tile_cache / "versions" / revision
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
        (world, z, y, x)
        for world in (WORLD_NAMES if all_worlds else ["overworld"])
        for z in range(offline_zoom + 1)
        for y in range(2**z)
        for x in range(2**z)
    ]
    # Create shared parents before concurrent downloads (Windows directory ACL races).
    for world, z, y, _x in tiles:
        (tile_cache / f"tiles/{world}_64k/{z}/{y}").mkdir(parents=True, exist_ok=True)

    def fetch(coords):
        world, z, y, x = coords
        relative = f"tiles/{world}_64k/{z}/{y}/{x}.webp"
        cached = download(f"{tile_base}/{relative}", tile_cache / relative)
        target = assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached, target)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, tiles))
    catalog = read_json(catalog_path)
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
                "stage": row.get("stage", 1 if part <= 24 else 2 if part <= 44 else 3),
                "duration": row["duration"],
                "download_status": row["download_status"],
                "reviewed": review is not None,
                "visits": sum(
                    e["review_status"] == "confirmed" for e in review["events"]
                )
                if review
                else None,
                "unmapped_count": sum(
                    e["review_status"] != "confirmed" for e in review["events"]
                )
                if review
                else None,
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
                unknown.append(
                    {
                        "part": part,
                        "event_id": event["event_id"],
                        "start": event["puzzle_start_time"],
                        "end": event["puzzle_end_time"],
                        "review_status": event["review_status"],
                        "reason": " / ".join(
                            proof.get("reason", "")
                            for proof in event.get("evidence", [])
                            if isinstance(proof, dict)
                        ),
                    }
                )
                continue
            level = by_name[name]
            item = levels.setdefault(
                name,
                {
                    "level_id": name,
                    "area": level["area"],
                    "map_layer": level.get(
                        "map_layer", layer(level["entries"][0]["coordinates"][2])
                    ),
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
                    "context": event.get("context"),
                    "audit_note": event.get("audit_note"),
                    "audit_anchor": event.get("audit_anchor"),
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
        "scope": f"塞德莎攻略 P{min(parts)}–P{max(parts)}，按经画面对照的访问/示例收录，按物理地图归类；未确认坐标的片段单列。",
        "parts": part_rows,
        "levels": list(levels.values()),
        "unknown_events": unknown,
        "excluded_parts": [68],
        "catalog_level_count": len(by_name),
        "not_observed": sorted(set(by_name) - set(levels)),
        "offline_zoom": offline_zoom,
        "tile_url": f"{tile_base}/tiles/overworld_64k/{{z}}/{{y}}/{{x}}.webp",
        "tileset_revision": revision,
    }
    marker_file = Path("cache/map/upstream/data/markers.json")
    marker_features = read_json(marker_file)["features"] if marker_file.exists() else []
    editorial = (
        read_json("data/annotations.json")
        if Path("data/annotations.json").exists()
        else {}
    )
    links = (
        read_json("data/video_links.json")
        if Path("data/video_links.json").exists()
        else {}
    )
    for event in unknown:
        target = links.get("parts", {}).get(str(event["part"]), {})
        event["url"] = video_url(
            target.get("bvid", data["bvid"]),
            target.get("part", event["part"]),
            event["start"],
        )
    if all_worlds:
        # Preserve one video-wide ordinal sequence when a part visits multiple maps.
        seen = {}
        for visit, item in sorted(
            [(v, l) for l in levels.values() for v in l["visits"]],
            key=lambda pair: (pair[0]["part"], pair[0]["start"]),
        ):
            names = seen.setdefault(visit["part"], {})
            visit["ordinal"] = names.setdefault(item["level_id"], len(names) + 1)
        for row in part_rows:
            row["level_count"] = len(seen.get(row["part"], {}))
            row["display_part"] = (
                links.get("parts", {})
                .get(str(row["part"]), {})
                .get("part", row["part"])
            )
        maps = []
        for map_id, map_name in WORLD_NAMES.items():
            members = [l for l in levels.values() if l["map_layer"] == map_id]
            used_parts = {v["part"] for l in members for v in l["visits"]}
            map_data = {
                "bvid": data["bvid"],
                "map_commit": data["map_commit"],
                "map_id": map_id,
                "map_name": map_name,
                "levels": members,
                "parts": [{**p} for p in part_rows if p["part"] in used_parts],
                "offline_zoom": offline_zoom,
                "tile_url": f"{tile_base}/tiles/{map_id}_64k/{{z}}/{{y}}/{{x}}.webp",
                "tileset_revision": revision,
            }
            enrich(
                map_data,
                marker_features,
                editorial,
                links,
                map_id=map_id,
                preserve_ordinals=True,
            )
            maps.append(map_data)
        data.update(
            maps=maps,
            scope="塞德莎攻略全部阶段；按物理地图收录画面确认的Level_Entry访问，后续阶段回访主世界仍计入主世界。",
        )
    else:
        enrich(data, marker_features, editorial, links)
    write_json(out / "index.json", data)
    for filename in (
        "atlas.css",
        "atlas.js",
        "atlas-ui.js",
        "atlas-editor.js",
        "favicon.svg",
    ):
        shutil.copyfile(Path(__file__).parent / "templates" / filename, out / filename)
    with (out / "visits.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "part",
                "display_part",
                "ordinal",
                "event_id",
                "level_id",
                "map_layer",
                "context",
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
                            for k in (
                                "part",
                                "display_part",
                                "ordinal",
                                "event_id",
                                "context",
                                "start",
                                "end",
                                "url",
                            )
                        },
                        "level_id": level["level_id"],
                        "map_layer": level["map_layer"],
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
    # A new HTML response must not reuse a cached script or stylesheet from an older build.
    for filename in (
        "atlas.css",
        "atlas.js",
        "atlas-ui.js",
        "atlas-editor.js",
        "favicon.svg",
    ):
        version = hashlib.sha256((out / filename).read_bytes()).hexdigest()[:12]
        template = template.replace(f'"{filename}"', f'"{filename}?v={version}"')
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
        [4]
        if len(sys.argv) > 2 and sys.argv[2] == "p4"
        else range(1, 68)
        if "worlds" in sys.argv
        else range(1, 25),
        catalog_path="cache/map/catalog_all.json"
        if "worlds" in sys.argv
        else "cache/map/catalog.json",
        all_worlds="worlds" in sys.argv,
    )
