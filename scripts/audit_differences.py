"""Publish a bounded, traceable manual-review list; never infer new identities."""

import csv
import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

from ootss.common import read_json, write_json
from ootss.exporting import validate, video_url

WORLD = {"overworld": "主世界", "sky": "天空世界", "underworld": "地下世界"}


def clock(t):
    return f"{int(t) // 60:02}:{int(t) % 60:02}"


def generate(out="results/worlds", catalog="cache/map/catalog_all.json"):
    out = Path(out)
    source = Path("results/audit")
    out.mkdir(parents=True, exist_ok=True)
    catalog = read_json(catalog)
    by_id = {r["level_id"]: r for r in catalog["levels"]}
    decisions = read_json("data/audit_decisions.json")
    bvid = read_json("results/series/manifest.json")["bvid"]
    remapping = read_json("data/video_links.json").get("parts", {})

    def url(part, start):
        target = remapping.get(str(part), {})
        return video_url(target.get("bvid", bvid), target.get("part", part), start)

    groups, missing_identity, observed = defaultdict(list), [], set()
    world_segments, human_visits = [], []
    human_metadata = decisions.get("human_review")
    confirmed_count = 0
    for part in range(1, 68):
        review = read_json(f"results/p{part}/reviewed.json")
        validate(review, catalog)
        for segment in review.get("excluded_segments", []):
            if segment.get("kind") == "world":
                world_segments.append(
                    {**segment, "part": part, "url": url(part, segment["start"])}
                )
        for e in sorted(review["events"], key=lambda x: x["puzzle_start_time"]):
            row = {
                "part": part,
                "event_id": e["event_id"],
                "start": e["puzzle_start_time"],
                "end": e["puzzle_end_time"],
                "url": url(part, e["puzzle_start_time"]),
                "review_status": e["review_status"],
                "level_id": e["level_id"],
                "note": e.get("audit_note", ""),
            }
            if e["review_status"] == "confirmed":
                observed.add(e["level_id"])
                groups[e["level_id"]].append(row)
                confirmed_count += 1
                if review.get("human_review") and e.get("source_event_ids"):
                    human_visits.append(row)
            else:
                reasons = [
                    item.get("reason", "")
                    for item in e.get("evidence", [])
                    if isinstance(item, dict) and item.get("reason")
                ]
                row["reason"] = (
                    reasons[-1]
                    if e["review_status"] == "conflict"
                    else " / ".join(reasons)
                )
                row["previous_level_id"] = e.get("superseded_identification", {}).get(
                    "level_id"
                )
                missing_identity.append(row)

    repeated = [
        {"level_id": name, "map_layer": by_id[name]["map_layer"], "events": events}
        for name, events in groups.items()
        if len(events) > 1
    ]
    repeated.sort(
        key=lambda r: (
            not any(e["note"] for e in r["events"]),
            r["events"][0]["part"],
            r["events"][0]["start"],
        )
    )
    absent = []
    for name in sorted(set(by_id) - observed):
        r = by_id[name]
        preview = f"assets/previews/{name}.webp"
        dest = out / preview
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(r["reference"]) as im:
            im.thumbnail((480, 270))
            im.save(dest, quality=78)
        # Nearest *known* entrances are a navigation aid, never identity evidence.
        x, y, _ = r["entries"][0]["coordinates"]
        near = sorted(
            (
                other
                for other in by_id.values()
                if other["level_id"] in observed
                and other["map_layer"] == r["map_layer"]
            ),
            key=lambda other: min(
                (p["coordinates"][0] - x) ** 2 + (p["coordinates"][1] - y) ** 2
                for p in other["entries"]
            ),
        )[:2]
        absent.append(
            {
                "level_id": name,
                "map_layer": r["map_layer"],
                "area": r["area"],
                "coordinates": [e["coordinates"] for e in r["entries"]],
                "map_url": r["map_url"],
                "preview": preview,
                "nearby_known_videos": [groups[other["level_id"]][0] for other in near],
            }
        )

    fixes = [{**d, "url": url(d["part"], d["start"])} for d in decisions["decisions"]]
    result = {
        "scope": "P1–67；P68隐藏题目已排除。入口身份、连续片段与独立进入次数分别核对。",
        "map_commit": catalog["commit"],
        "counts": {
            "catalog_entries": len(by_id),
            "mapped_entries": len(observed),
            "time_records": confirmed_count,
            "unlocated_segments": len(missing_identity),
            "absent_catalog_entries": len(absent),
            "repeated_identity_groups": len(repeated),
            "world_segments_excluded": len(world_segments),
        },
        "decisions": fixes,
        "repeated_identities": repeated,
        "unlocated_segments": missing_identity,
        "absent_catalog_entries": absent,
        "human_review": human_metadata,
        "human_confirmed_visits": human_visits,
        "excluded_world_segments": world_segments,
    }
    write_json(source / "differences.json", result)
    write_json(out / "audit.json", result)
    evidence = out / "assets/audit"
    evidence.mkdir(parents=True, exist_ok=True)
    for p in (source / "evidence").glob("*.jpg"):
        shutil.copyfile(p, evidence / p.name)

    esc = lambda s: html.escape(str(s))

    def link(url, text):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>'

    def times(e):
        return link(e["url"], f"P{e['part']:02} {clock(e['start'])}–{clock(e['end'])}")

    def table(headers, rows):
        return (
            '<div class="table-scroll"><table><thead><tr>'
            + "".join(f"<th>{esc(h)}</th>" for h in headers)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows
            )
            + "</tbody></table></div>"
        )

    fix_rows = []
    for d in fixes:
        images = " · ".join(
            link("assets/audit/" + name, "对照图") for name in d["evidence"]
        )
        action = (
            f"已改为 {d['level_id']}"
            if d["action"] == "corrected"
            else (
                f"用户确认未切关；已并入 {d['level_id']}"
                if d["action"] == "merged_after_human_review"
                else "已撤销错误坐标；归属待人工核对"
            )
        )
        candidates = "、".join(d["candidates"])
        fix_rows.append(
            [
                times(d)
                + f"<small>{esc(d['event_id'])} · 原序号 {d['old_ordinal']}</small>",
                esc(d["previous_level_id"]),
                esc(action),
                esc(d["reason"])
                + "<small>候选："
                + esc(candidates)
                + "</small>"
                + images,
            ]
        )

    repeat_rows = []
    for r in repeated:
        name = r["level_id"]
        note = next(
            (e["note"] for e in r["events"] if e["note"]),
            "仅检测出重复ID，尚未逐段裁决；可能为回访、重试、连续内部视角，或同构变体错认。请比较进关前位置和初始角色，不能仅凭地形。",
        )
        gallery = (
            "repeat_p50_magnitudes_boundaries.jpg"
            if name == "magnitudes_v3"
            else "repeat_p5_mirror14_bounded.jpg"
            if name == "mirror_14"
            else "repeat_p5_mirror.jpg"
            if name == "mirror_4"
            else "repeat_p24_end1.jpg"
            if name == "end1"
            else None
        )
        repeat_rows.append(
            [
                f'<span id="repeat-{esc(name)}">{esc(name)}</span><small>{WORLD[r["map_layer"]]} · {len(r["events"])} 个匹配窗</small>',
                "<br>".join(
                    times(e) + f"<small>{esc(e['event_id'])}</small>"
                    for e in r["events"]
                ),
                esc(note)
                + (
                    "<br>" + link("assets/audit/" + gallery, "边界对照图")
                    if gallery
                    else ""
                ),
            ]
        )

    unknown_rows = [
        [
            times(e) + f"<small>{esc(e['event_id'])}</small>",
            esc(e["previous_level_id"] or "未匹配"),
            esc(e["reason"]),
        ]
        for e in missing_identity
    ]
    absent_rows = []
    for e in absent:
        nearby = "<br>".join(
            times(v) + " · " + esc(v["level_id"]) for v in e["nearby_known_videos"]
        )
        absent_rows.append(
            [
                link(e["map_url"], e["level_id"])
                + f"<small>{WORLD[e['map_layer']]} · {esc(e['coordinates'])}</small>",
                f'<a href="{esc(e["preview"])}"><img src="{esc(e["preview"])}" alt="{esc(e["level_id"])}参考布局" loading="lazy" width="200"></a>',
                nearby,
            ]
        )

    human_rows = [
        [times(e), esc(e["level_id"]), "身份或连续区间已按用户确认更新"]
        for e in human_visits
    ]
    world_rows = [
        [times(e), "大世界；不计关卡", esc(e["evidence"][0]["reason"])]
        for e in world_segments
    ]
    owner_section = (
        (
            f'<section id="human"><h2>用户校对已应用 · {human_metadata["item_count"]} 条</h2>'
            '<p>依据 <a href="https://github.com/Jimmyzzt/OotSS_Sand/blob/master/docs/校对.md" target="_blank" rel="noopener">用户校对原文</a>，内部切换并回同一次访问；明确未进关的片段移出未知关卡清单。旧事件及证据保存在审核文件的superseded_events。</p>'
            + table(["当前连续区间", "入口ID", "处理"], human_rows)
            + "<details><summary>查看已排除的大世界片段</summary>"
            + table(["视频区间", "分类", "依据"], world_rows)
            + "</details></section>"
        )
        if human_metadata
        else ""
    )
    intro = (
        f"目录 {len(by_id)} 个入口；当前已映射 {len(observed)} 个，差集 {len(absent)} 个；"
        f"{len(missing_identity)} 段尚未定位，{len(repeated)} 组重复ID待核。P68已排除。"
    )
    body = f"""<header><a href="index.html">← 返回地图</a><h1>入口差异与人工校对清单</h1><p>{intro}</p><p>“未定位”不等于“原地图不存在”；“目录未出现”不等于“视频一定没拍到”。重复ID也不直接等于重复关卡。这里只纠正有位置、角色、物理世界或用户确认依据的错配，其他保留待核。</p><nav><a href="#human">用户校对</a> · <a href="#fixes">历史纠正</a> · <a href="#repeats">重复ID</a> · <a href="#unlocated">未定位片段</a> · <a href="#absent">目录差集</a> · <a href="audit.csv">下载CSV</a> · <a href="audit.json">JSON</a></nav></header>
{owner_section}
<section id="fixes"><h2>本轮纠正与撤销</h2>{table(["视频 / 原编号", "旧匹配", "处理", "证据与待核点"], fix_rows)}</section>
<section id="repeats"><h2>其余重复ID待核</h2><p>用户已确认未切关的片段不再列为重复记录。其余组仍保留，优先检查带具体疑点的组；重复可能为正常重试或回访，不应仅由布局变化判定进出关卡。</p>{table(["入口ID", "全部时间窗", "疑点与核对方法"], repeat_rows)}</section>
<section id="unlocated"><h2>剩余未定位片段</h2><p>已归入原关卡和明确在大世界的片段已移出此表。剩余片段仍需定位，不能据此宣布原图没有这些关。</p>{table(["视频", "旧ID（如有）", "原因"], unknown_rows)}</section>
<section id="absent"><h2>原图有、当前尚无可靠记录的入口</h2><p>下面的就近视频仅按同一地图的空间距离排列，方便找进关前的位置；不是该关出现的证据，也没有据此自动填入地图。</p>{table(["原地图入口 / 坐标", "参考布局", "就近已知入口的视频（仅导航线索）"], absent_rows)}</section>
<footer>固定原地图提交：{esc(catalog["commit"])}。本轮有界复核：P02、P05、P24、P43/P44、P50、P64；P61/P65/P67补做跨世界筛查。完整系列仅做目录差集与重复规则检查，未声称逐帧重审全部视频。数据与截图为公开攻略/原图的核对证据。</footer>"""
    css = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5efdf;color:#303c38;font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif}header,section,footer{max-width:1280px;margin:auto;padding:18px 24px}header{padding-top:26px}h1{font-size:25px}h2{font-size:19px;margin-top:10px}p{max-width:1000px;color:#657067}a{color:#366956}nav a{display:inline-block;margin:3px 0}section{scroll-margin-top:12px}small{display:block;color:#69756b;font-size:11px}table{border-collapse:collapse;width:100%;background:#fbf7ec}th,td{text-align:left;vertical-align:top;padding:10px 12px;border:1px solid #d6cfbd;overflow-wrap:anywhere}th{background:#e5ecdf;white-space:nowrap}td:first-child{min-width:180px}td:nth-child(2){min-width:170px}img{max-width:100%;border-radius:4px}.table-scroll{overflow-x:auto}footer{font-size:12px;color:#69756b}span[id]{scroll-margin-top:20px}@media(max-width:760px){header,section,footer{padding:12px}h1{font-size:21px}table{font-size:12px}th,td{padding:7px}}"""
    page = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>入口差异与人工校对清单</title><style>'
        + css
        + "</style><body>"
        + body
        + "</body></html>"
    )
    (out / "audit.html").write_text(page, encoding="utf-8")

    csv_rows = []
    for e in human_visits:
        csv_rows.append(
            {
                "type": "用户已确认连续访问",
                "id": e["event_id"],
                "part": e["part"],
                "start": e["start"],
                "end": e["end"],
                "level_id": e["level_id"],
                "reason": "用户校对已应用，片段合并",
                "url": e["url"],
            }
        )
    for e in world_segments:
        csv_rows.append(
            {
                "type": "大世界（已排除）",
                "id": e["segment_id"],
                "part": e["part"],
                "start": e["start"],
                "end": e["end"],
                "reason": e["evidence"][0]["reason"],
                "url": e["url"],
            }
        )
    for d in fixes:
        csv_rows.append(
            {
                "type": "纠正/撤销",
                "id": d["event_id"],
                "part": d["part"],
                "start": d["start"],
                "end": d["end"],
                "level_id": d["level_id"],
                "previous_level_id": d["previous_level_id"],
                "reason": d["reason"],
                "url": d["url"],
            }
        )
    for r in repeated:
        for e in r["events"]:
            csv_rows.append(
                {
                    "type": "重复ID待核",
                    "id": e["event_id"],
                    "part": e["part"],
                    "start": e["start"],
                    "end": e["end"],
                    "level_id": r["level_id"],
                    "reason": e["note"] or "规则筛查，需比较入口位置/初始角色/连续性",
                    "url": e["url"],
                }
            )
    for e in missing_identity:
        csv_rows.append(
            {
                "type": "未定位",
                "id": e["event_id"],
                "part": e["part"],
                "start": e["start"],
                "end": e["end"],
                "previous_level_id": e["previous_level_id"],
                "reason": e["reason"],
                "url": e["url"],
            }
        )
    for e in absent:
        csv_rows.append(
            {
                "type": "目录差集",
                "id": e["level_id"],
                "level_id": e["level_id"],
                "reason": f"{WORLD[e['map_layer']]} {e['coordinates']}；未证明视频未出现",
                "url": e["map_url"],
            }
        )
    fields = [
        "type",
        "id",
        "part",
        "start",
        "end",
        "level_id",
        "previous_level_id",
        "reason",
        "url",
    ]
    for target in (source / "differences.csv", out / "audit.csv"):
        with target.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(csv_rows)
    md = [
        "# 入口差异与人工校对清单",
        "",
        intro,
        "",
        "在线清单：https://sand.zzt.si/audit.html",
        "",
        "## 已纠正/撤销",
        "",
    ]
    if human_metadata:
        md[6:6] = [
            f"已应用用户[{human_metadata['source']}](../../{human_metadata['source']})的{human_metadata['item_count']}条校对；{len(human_visits)}条连续访问已合并/确认，{len(world_segments)}段大世界记录不再视作未知关卡。",
            "",
        ]
    for d in fixes:
        md.append(
            f"- [{d['event_id']} {clock(d['start'])}]({d['url']})：`{d['previous_level_id']}` → `{d['level_id'] or '未定位'}`。{d['reason']}"
        )
    md += [
        "",
        "重复ID、未定位片段及原图差集的完整逐项列表见 differences.csv / differences.json，网页附参考图和就近视频导航。",
        "",
        "未定位不等于原图不存在；目录差集不等于视频没出现。P68隐藏内容不参加统计。",
    ]
    (source / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return result


if __name__ == "__main__":
    generate()
