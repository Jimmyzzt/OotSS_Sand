"""Presentation metadata derived from the original Joric grid and reviewed visits."""

import math
from collections import Counter, defaultdict

from .exporting import video_url

GRID = {
    "width": 19,
    "height": 13,
    "center": [80, 69],
    "source": "joric/ootss index.html gridLayer: gw=19, gh=13, cx=80, cy=69",
}


def cell_for(coordinates):
    x, y = coordinates[:2]
    return math.floor((x - 70.5) / 19), math.floor((y - 62.5) / 13)


def cell_id(col, row):
    return f"{col},{row}"


def direction(col, row):
    return (
        (f"北{row}" if row > 0 else f"南{-row}" if row < 0 else "")
        + (f"东{col}" if col > 0 else f"西{-col}" if col < 0 else "")
    ) or "中心"


def theme_for(levels, first_part, col, row):
    areas = Counter(l["area"] for l in levels if l["area"] != "worlds_collide")
    area = areas.most_common(1)[0][0] if areas else "worlds_collide"
    names = {
        "heroes1": "搬运英雄",
        "heroes2": "英雄2·怪物",
        "heroes3": "英雄3·吟游诗人与德鲁伊",
        "sideways_gates": "能量门方向",
        "mirror": "镜之群岛",
        "skipping_stones": "飞石成径",
        "heroes_and_water": "英雄与水",
        "heroes_and_mirrors": "英雄与魔镜",
        "mirrors_and_stones": "魔镜与飞石",
        "mirrorable_stones": "魔镜与飞石",
        "beams_and_stones": "光照之石",
        "worlds_collide": "黄金谜题",
        "endgame1": "对映之地·出口",
    }
    if area == "promesst1_and_2":
        return "光束发射器之库" if row == 0 else "推车与短杖" if row > 0 else "项环"
    if area in {"beams_and_basic_heroes", "heroes_and_artifacts", "beaming_objects"}:
        return (
            "英雄与神器"
            if first_part == 15
            else "英雄与光·进阶"
            if first_part == 17
            else "英雄与光"
        )
    if area == "heroes_and_stones":
        return (
            "英雄与水·北部"
            if row >= 5 and col >= 0 and first_part == 20
            else "英雄与飞石"
        )
    if area == "beams_and_mirrors":
        return "映照之光" if col < 0 and row > 0 else "反射光束"
    return names.get(area, area)


def enrich(data, marker_features=(), editorial=None, links=None):
    editorial, links = editorial or {}, links or {}
    metadata = {
        f["properties"].get("name"): f["properties"].get("entity_properties", {})
        for f in marker_features
        if f["properties"].get("type") == "Level_Entry"
    }
    levels = {l["level_id"]: l for l in data["levels"]}
    parts = {p["part"]: p for p in data["parts"]}
    all_visits = sorted(
        [(v, l) for l in levels.values() for v in l["visits"]],
        key=lambda pair: (pair[0]["part"], pair[0]["start"]),
    )
    grouped = defaultdict(list)
    for level in levels.values():
        entry_cells = sorted({cell_for(e["coordinates"]) for e in level["entries"]})
        level["region_ids"] = [cell_id(*c) for c in entry_cells]
        for c in entry_cells:
            grouped[c].append(level)
        props = metadata.get(level["level_id"], {})
        annotation = editorial.get("levels", {}).get(level["level_id"], {})
        level["manual"] = annotation
        level["tags"] = {
            "big_star": annotation.get(
                "big_star", "Entry_Hero_" in props.get("mesh", "")
            ),
            "multi_save": bool(annotation.get("multi_save", False)),
            "notes": annotation.get("notes", ""),
        }
        level["tag_source"] = {
            "big_star": "editorial"
            if "big_star" in annotation
            else "Joric Level_Entry Hero mesh",
            "multi_save": "manual only",
        }
    unique_by_part, routes = defaultdict(dict), defaultdict(list)
    for visit, level in all_visits:
        part = visit["part"]
        ordinal = unique_by_part[part].setdefault(
            level["level_id"], len(unique_by_part[part]) + 1
        )
        target = links.get("parts", {}).get(str(part), {})
        display_part = target.get("part", part)
        visit.update(
            ordinal=ordinal,
            source_part=part,
            display_part=display_part,
            url=video_url(
                target.get("bvid", data["bvid"]), display_part, visit["start"]
            ),
        )
        region_id = level["region_ids"][0]
        if not routes[part] or routes[part][-1]["region_id"] != region_id:
            routes[part].append(
                {
                    "region_id": region_id,
                    "start": visit["start"],
                    "first_ordinal": ordinal,
                }
            )
    regions = []
    for (col, row), members in grouped.items():
        visits = [v for l in members for v in l["visits"]]
        first = min((v["part"], v["start"]) for v in visits)
        left, bottom = 70.5 + col * 19, 62.5 + row * 13
        regions.append(
            {
                "id": cell_id(col, row),
                "col": col,
                "row": row,
                "direction": direction(col, row),
                "theme": theme_for(members, first[0], col, row),
                "bounds": [left, bottom, left + 19, bottom + 13],
                "parts": sorted({v["part"] for v in visits}),
                "first": list(first),
                "level_ids": [l["level_id"] for l in members],
            }
        )
    regions.sort(key=lambda r: r["first"])
    theme_count = Counter()
    for i, region in enumerate(regions, 1):
        theme_count[region["theme"]] += 1
        region.update(
            order=i, title=region["theme"] + str(theme_count[region["theme"]])
        )
        override = editorial.get("regions", {}).get(region["id"], {})
        if isinstance(override.get("title"), str):
            region["title"] = override["title"]
        for l in grouped[(region["col"], region["row"])]:
            l.setdefault("region_titles", []).append(region["title"])
    for part, row in parts.items():
        target = links.get("parts", {}).get(str(part), {})
        row.update(
            display_part=target.get("part", part),
            level_count=len(unique_by_part[part]),
            route=routes[part],
        )
    data.update(grid=GRID, regions=regions, annotation_version=1)
    return data
