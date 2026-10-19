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
        location = f"[位置]({e['map_url']})" if e.get("map_url") else "unknown"
        lines.append(
            f"| {i} | {e['level_id'] or 'unknown'} | [{stamp(e['puzzle_start_time'])}]({e['video_url']})–{stamp(e['puzzle_end_time'])} | {e['review_status']} | {location} |"
        )
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    draw_map(rows, out)
    write_report(result, out)
    return result


def write_report(result, out):
    esc = html.escape
    lines = [
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>OotSS 视频关卡索引</title>",
        "<style>body{font:16px/1.6 system-ui;margin:24px auto;padding:0 20px;max-width:1200px;background:#101b26;color:#e1edf7}a{color:#73e3df}table{border-collapse:collapse;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid #375064}img,svg{max-width:100%;height:auto}details{margin:18px 0}code{overflow-wrap:anywhere} .scroll{overflow:auto}</style>",
        f"<h1>P{result['part_number']} · {len(result['events'])} 次关卡访问</h1>",
        "<p>点击时间跳转视频，点击地图位置打开 Joric 地图。关卡身份由 Codex 对照画面确认，尚待用户验收；完成或跳过状态未确认。时间边界约 ±0.5 秒。</p>",
        "<p><a href='index.json'>JSON</a> · <a href='index.csv'>CSV</a> · <a href='index.md'>Markdown</a> · <a href='map.svg'>SVG 坐标示意图</a> · <a href='map.png'>PNG</a></p>",
    ]
    if (out / "map.svg").exists():
        lines.append((out / "map.svg").read_text(encoding="utf-8"))
    lines.append(
        "<div class='scroll'><table><tr><th>#</th><th>关卡 ID</th><th>视频区间</th><th>坐标 X/Y/Z</th><th>进入前核验</th></tr>"
    )
    for i, e in enumerate(result["events"], 1):
        coords = "; ".join(str(m["coordinates"]) for m in e["map_entries"])
        status = e.get("overworld_match", {}).get("status", "unverified")
        status = {
            "verified_by_agent": "已对照地形及入口格",
            "no_overworld_context": "连续换关，无主世界画面",
        }.get(status, status)
        map_link = (
            f'<a href="{esc(e["map_url"], quote=True)}">{esc(coords)}</a>'
            if e.get("map_url")
            else "unknown"
        )
        lines.append(
            f'<tr id="{esc(e["event_id"])}"><td>{i}</td><td><code>{esc(e["level_id"] or "unknown")}</code></td><td><a href="{esc(e["video_url"], quote=True)}">{stamp(e["puzzle_start_time"])}–{stamp(e["puzzle_end_time"])}</a></td><td>{map_link}</td><td>{esc(status)}</td></tr>'
        )
    lines.append("</table></div>")
    for item in result.get("galleries", []):
        lines.append(
            f'<details><summary>{esc(item["label"])}</summary><img loading="lazy" src="{esc(item["path"], quote=True)}" alt="{esc(item["label"], quote=True)}"></details>'
        )
    lines.append(
        "<p>数据来源：<a href='https://github.com/joric/ootss'>Joric OotSS / Unlicense</a>。此文件为本地静态导出，无服务或模型调用。</p></html>"
    )
    (out / "index.html").write_text("\n".join(lines), encoding="utf-8")


def draw_map(rows, out):
    """Separate distant coordinate clusters so adjacent entrance labels stay legible."""
    points = [
        (i, e, m["coordinates"])
        for i, e in enumerate(rows, 1)
        for m in e["map_entries"]
    ]
    if not points:
        (out / "map.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="150"><text x="20" y="60">No confirmed coordinates</text></svg>',
            encoding="utf-8",
        )
        im = Image.new("RGB", (600, 150), "white")
        ImageDraw.Draw(im).text(
            (20, 40), "No confirmed coordinates", fill="black", font_size=24
        )
        im.save(out / "map.png")
        return
    remaining, clusters = points.copy(), []
    while remaining:
        cluster = [remaining.pop(0)]
        changed = True
        while changed:
            changed = False
            for p in remaining.copy():
                if any(
                    (p[2][0] - q[2][0]) ** 2 + (p[2][1] - q[2][1]) ** 2 <= 49
                    for q in cluster
                ):
                    cluster.append(p)
                    remaining.remove(p)
                    changed = True
        clusters.append(cluster)
    clusters.sort(key=len, reverse=True)
    width, height = 1700, max(1100, len(rows) * 28 + 130)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#101b26"/>',
        '<g fill="#e1edf7" font-family="monospace" font-size="16">',
        '<text x="30" y="30">OotSS - video level coordinate schematic (X right, Y up)</text>',
        '<text x="30" y="56">Local panels use independent scales. X right, Y up. Click dots or legend for video.</text>',
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
        "Local panels use independent scales. Numbers follow video order; terrain not shown.",
        fill="white",
        font_size=17,
    )
    if len(clusters) >= 3:
        columns = min(3, len(clusters) - 1)
        panel_width = (930 - 20 * (columns - 1)) / columns
        panel_height = (height - 750) / math.ceil((len(clusters) - 1) / columns)
        boxes = [(30, 90, 930, 620)] + [
            (
                30 + i % columns * (panel_width + 20),
                750 + i // columns * panel_height,
                panel_width,
                panel_height - 20,
            )
            for i in range(len(clusters) - 1)
        ]
    else:
        columns = 1 if len(clusters) == 1 else 2
        panel_height = (height - 150) / math.ceil(len(clusters) / columns)
        boxes = [
            (
                30 + i % columns * 470,
                90 + i // columns * panel_height,
                930 if columns == 1 else 450,
                panel_height - 20,
            )
            for i in range(len(clusters))
        ]
    for panel, (cluster, box) in enumerate(zip(clusters, boxes, strict=True), 1):
        bx, by, bw, bh = box
        xs, ys = [p[2][0] for p in cluster], [p[2][1] for p in cluster]
        left, right, bottom, top = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
        scale = min((bw - 100) / (right - left), (bh - 100) / (top - bottom))
        ox, oy = bx + 55, by + 50
        title = (
            f"Panel {panel}: X {min(xs):g}..{max(xs):g} / Y {min(ys):g}..{max(ys):g}"
        )
        svg.append(
            f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" stroke="#375064"/>'
        )
        svg.append(f'<text x="{bx + 12}" y="{by + 26}">{title}</text>')
        draw.rectangle((bx, by, bx + bw, by + bh), outline="#375064")
        draw.text((bx + 12, by + 10), title, fill="white", font_size=18)
        for x in range(math.ceil(left), math.floor(right) + 1):
            px = ox + (x - left) * scale
            svg.append(
                f'<path d="M {px:.1f} {oy} v {(top - bottom) * scale:.1f}" stroke="#26394b"/><text x="{px - 8:.1f}" y="{oy + (top - bottom) * scale + 25:.1f}" font-size="12">{x}</text>'
            )
            draw.line((px, oy, px, oy + (top - bottom) * scale), fill="#26394b")
            draw.text(
                (px - 8, oy + (top - bottom) * scale + 8),
                str(x),
                fill="#a1b4c7",
                font_size=12,
            )
        for y in range(math.ceil(bottom), math.floor(top) + 1):
            py = oy + (top - y) * scale
            svg.append(
                f'<path d="M {ox} {py:.1f} h {(right - left) * scale:.1f}" stroke="#26394b"/><text x="{ox - 35}" y="{py + 5:.1f}" font-size="12">{y}</text>'
            )
            draw.line((ox, py, ox + (right - left) * scale, py), fill="#26394b")
            draw.text((ox - 35, py - 8), str(y), fill="#a1b4c7", font_size=12)
        seen = {}
        for i, e, c in cluster:
            x, y = ox + (c[0] - left) * scale, oy + (top - c[1]) * scale
            svg.append(
                f'<a href="{html.escape(e["video_url"], quote=True)}"><circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#61d3d0"/><title>{html.escape(e["level_id"] + " " + str(c))}</title></a>'
            )
            offset = seen.get(tuple(c), 0)
            seen[tuple(c)] = offset + 1
            svg.append(
                f'<text x="{x + 10:.1f}" y="{y - 10 + offset * 20:.1f}" font-size="20">{i}</text>'
            )
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#61d3d0")
            draw.text(
                (x + 10, y - 24 + offset * 20), str(i), fill="white", font_size=20
            )
    for i, e in enumerate(rows, 1):
        y = 115 + (i - 1) * 28
        label = f"{i:02d} {stamp(e['puzzle_start_time'])} {e['level_id'] or 'unknown'}"
        svg.append(
            f'<a href="{html.escape(e["video_url"], quote=True)}"><text x="1020" y="{y}">{html.escape(label)}</text></a>'
        )
        draw.text((1020, y - 18), label, fill="white", font_size=17)
    svg.append("</g></svg>")
    (out / "map.svg").write_text("\n".join(svg), encoding="utf-8")
    image.save(out / "map.png")
