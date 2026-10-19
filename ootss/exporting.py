import csv
import html
import math
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image, ImageDraw

from .common import read_json, stamp, write_json


def video_url(bvid, part, seconds):
    return f"https://www.bilibili.com/video/{bvid}/?" + urlencode(
        {"p": part, "t": math.floor(seconds)}
    )


def validate(review, catalog):
    names = {r["level_id"] for r in catalog["levels"]}
    ids = set()
    duration = review["duration"]
    for e in review["events"]:
        if e["event_id"] in ids:
            raise ValueError("Duplicate event_id")
        ids.add(e["event_id"])
        if e["level_id"] is not None and e["level_id"] not in names:
            raise ValueError(f"Not an Overworld level: {e['level_id']}")
        a, b = e["puzzle_start_time"], e["puzzle_end_time"]
        if not 0 <= a < b <= duration:
            raise ValueError(f"Invalid time interval: {e['event_id']}")
        if e.get("review_status") not in {
            "confirmed",
            "unknown",
            "candidate",
            "conflict",
        }:
            raise ValueError("Missing or invalid review status")
        if e.get("review_status") == "confirmed" and (
            e["level_id"] is None or not e.get("evidence")
        ):
            raise ValueError("Confirmed identity requires a level and evidence")
        for field in ("overworld_approach_time", "entry_transition_time", "exit_time"):
            value = e.get(field)
            if value is not None and not 0 <= value <= duration:
                raise ValueError(f"Invalid {field}")
    return review


def export(review_path, out, catalog="cache/map/catalog.json"):
    review, cat = read_json(review_path), read_json(catalog)
    validate(review, cat)
    by_name = {r["level_id"]: r for r in cat["levels"]}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for e in review["events"]:
        level = by_name.get(e["level_id"], {})
        rows.append(
            {
                **e,
                "video_bvid": review["video_bvid"],
                "part_number": review["part_number"],
                "map_layer": level.get("map_layer"),
                "map_entries": level.get("entries", []),
                "area": level.get("area"),
                "map_url": level.get("map_url"),
                "video_url": video_url(
                    review["video_bvid"], review["part_number"], e["puzzle_start_time"]
                ),
            }
        )
    result = {**review, "map_commit": cat["commit"], "events": rows}
    write_json(out / "index.json", result)
    fields = [
        "event_id",
        "level_id",
        "area",
        "puzzle_start_time",
        "puzzle_end_time",
        "overworld_approach_time",
        "entry_transition_time",
        "review_status",
        "outcome",
        "map_entries",
        "video_url",
        "map_url",
    ]
    with (out / "index.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        f"# P{review['part_number']} 关卡索引",
        "",
        "时间为本分 P 秒数；已确认指关卡身份经画面对照，不代表已独立人工验收。完成状态与入口位置核验单独记录。",
        "",
        "| # | 关卡 | 开始–结束 | 身份 | 地图 |",
        "|---|---|---|---|---|",
    ]
    for i, e in enumerate(rows, 1):
        lines.append(
            f"| {i} | {e['level_id'] or 'unknown'} | [{stamp(e['puzzle_start_time'])}]({e['video_url']})–{stamp(e['puzzle_end_time'])} | {e['review_status']} | [位置]({e['map_url']}) |"
        )
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    draw_map(rows, out)
    return result


def draw_map(rows, out):
    """Schematic uses actual game X/Y, without pretending it is terrain."""
    points = [
        (i, e, m["coordinates"])
        for i, e in enumerate(rows, 1)
        for m in e["map_entries"]
    ]
    if not points:
        return
    width, height = 1500, max(850, len(rows) * 27 + 100)
    xs, ys = [p[2][0] for p in points], [p[2][1] for p in points]
    left, right, bottom, top = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
    scale = min(760 / (right - left), (height - 160) / (top - bottom))

    def xy(c):
        return 60 + (c[0] - left) * scale, 90 + (top - c[1]) * scale

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#101b26"/>',
        '<g fill="#e1edf7" font-family="monospace" font-size="16">',
        '<text x="30" y="30">OotSS - video level coordinate schematic (X right, Y up)</text>',
        '<text x="30" y="56">Numbers follow video order. Terrain not shown. Click legend for video; dots for Joric map.</text>',
    ]
    image = Image.new("RGB", (width, height), "#101b26")
    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 25),
        "OotSS - video level coordinate schematic (X right, Y up)",
        fill="white",
        font_size=21,
    )
    draw.text(
        (30, 55),
        "Numbers follow video order; terrain not shown.",
        fill="white",
        font_size=17,
    )
    seen = {}
    for i, e, c in points:
        x, y = xy(c)
        svg.append(
            f'<a href="{html.escape(e["map_url"], quote=True)}"><circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#61d3d0"/><title>{html.escape(str(c))}</title></a>'
        )
        offset = seen.get(tuple(c), 0)
        seen[tuple(c)] = offset + 1
        svg.append(f'<text x="{x + 8:.1f}" y="{y - 8 + offset * 18:.1f}">{i}</text>')
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#61d3d0")
        draw.text((x + 8, y - 16 + offset * 18), str(i), fill="white", font_size=17)
    for i, e in enumerate(rows, 1):
        y = 95 + (i - 1) * 27
        label = f"{i:02d} {stamp(e['puzzle_start_time'])} {e['level_id'] or 'unknown'}"
        svg.append(
            f'<a href="{html.escape(e["video_url"], quote=True)}"><text x="850" y="{y}">{html.escape(label)}</text></a>'
        )
        draw.text((850, y - 17), label, fill="white", font_size=16)
    svg.append("</g></svg>")
    (out / "map.svg").write_text("\n".join(svg), encoding="utf-8")
    image.save(out / "map.png")
