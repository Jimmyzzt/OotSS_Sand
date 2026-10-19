"""Session-specific decisions after visual review, not automatic labeling.

Never overwrites reviewed.json. If revising the review, edit that file explicitly.
"""

import hashlib
from itertools import groupby
from pathlib import Path

from ootss.common import read_json, stamp, write_json
from ootss.video import contact_sheet

DECISIONS = [
    ("heroes3_10", "长条草丛走廊、左上粉门、底部三个紫按钮。"),
    ("heroes3_11_v2", "金色雕像背景，竖向草丛分隔，右侧紫按钮及门柱。"),
    ("druid_and_dragon", "纵向窄室，中间折线高墙，左下粉门与双圆目标。"),
    ("wizard_and_druid_alt_5", "左侧双圆目标与黄门，上方蓝门、双高柱、右上水晶。"),
    ("heroes3_15_v4", "L形草丛/石块走廊，右侧两个圆目标，植物与火山墙体一致。"),
    ("heroes3_13_v2", "横向沙地，右侧粉门与三个紫按钮，四角人物配置及墙体一致。"),
    ("heroes3_druid_b_v2", "中央高台绕行，顶端粉门，右上蓝盆，左下三个石块。"),
    ("heroes3_druid_a", "开阔矩形平台，右侧三枚圆目标，左侧窄草地；非空白主世界。"),
    ("wizard_and_druid_alt", "下方双房间，上方横通道，中央蓝色能量栅栏和植物。"),
    ("heroes3_1_v3", "熔岩围绕，中间两枚灰石，L形围墙，左下人物与圆目标。"),
    ("heroes3_2_v4", "同色火山场景但变为U形内墙、右侧黄门；14:47切换后独立一关。"),
    ("heroes3_3_v2", "长方形盆地，左上粉光、中央横水渠和绿石，右侧吊臂。"),
    ("heroes3_4", "短暂沙地小关：中央单柱、右粉门和蓝圆按钮；16:03–16:18。"),
    ("heroes3_5", "沙地四角四角色、右侧上下两个蓝格及黄门。"),
    ("heroes3_8_thief", "方形棋盘，左侧两红块、右上黄门，中央金属踏板。"),
    ("heroes3_6_v3", "花园三条横向植槽，左上长竖通道和紫按钮，右侧圆柱。"),
    ("heroes3_7_v4", "纵向中央花槽/柱体，左右独立狭道，右侧黄门、左上粉门。"),
    ("heroes3_8_v4_alt", "多层方形回廊，右侧粉门、中央两个横向台座。"),
    ("heroes3_8_v3_alt3", "蓝紫方室，左下黄门，上方横隔墙与右侧竖通道。"),
    ("heroes3_14_v3", "横向紫色石台，中间竖列黄门，右侧竖列粉门，右下红按钮。"),
    ("heroes3_16_v4_alt", "暗蓝L形狭道，上方横通道和右端红圆目标，右侧熔岩。"),
    ("compactor_v2", "暗蓝长方室，中间四黄按钮，右侧粉/黄门和双圆目标。"),
    ("gatekeeping_v3", "上方三圆目标，中央竖向石室及草丛，下方横廊粉门。"),
    ("heroes3_21_condensed", "红色横向大室，左右各三圆目标，下方三个小室。"),
    ("side_slide_intro_v2", "双层绿石室，上层黄/蓝门，下层紫/绿门和双圆按钮。"),
    ("side_kick", "林地横向双室，右上三角障碍/粉门，左下绿门，紫圆按钮。"),
    ("multipush_for_me2", "林地纵向上下室，上方高台与黄门，中间竖列蓝门。"),
    ("dragon_on_the_wall", "大方格庭院，左上龙吐火，右侧黄门、左下粉门和黄门。"),
    ("victory_lap", "白色方格中央高台，四周八种人物/机关，右侧瀑布，图形布局唯一。"),
]


def main():
    target = Path("results/p4/reviewed.json")
    if target.exists():
        raise SystemExit(
            "Preserved existing review. Edit reviewed.json explicitly to revise decisions."
        )
    scan = read_json("runs/p4_check/scan.json")
    matched = read_json("runs/p4_check/matches.json")
    cat = read_json("cache/map/catalog.json")
    levels = {r["level_id"]: r for r in cat["levels"]}
    contexts = {r["level_id"]: r for r in read_json("runs/p4/world_checks.json")}
    groups = []
    for name, group in groupby(
        matched["samples"],
        key=lambda x: (
            x["candidates"][0]["level_id"]
            if x["candidates"][0]["sift_inliers"] >= 10
            else None
        ),
    ):
        samples = list(group)
        if name:
            groups.append((name, samples))
    assert [n for n, _ in groups] == [n for n, _ in DECISIONS], (
        "Unexpected candidates: review before curating"
    )
    events, pairs = [], []
    for i, ((name, samples), (_, reason)) in enumerate(
        zip(groups, DECISIONS, strict=True), 1
    ):
        first, last = samples[0]["time"], samples[-1]["time"]
        enter = max(
            (t for t in scan["transitions"] if t["end"] <= first),
            key=lambda t: t["end"],
        )
        leave = min(
            (t for t in scan["transitions"] if t["start"] >= last),
            key=lambda t: t["start"],
        )
        assert 0 <= first - enter["end"] <= 6 and 0 <= leave["start"] - last <= 6
        representative = max(samples, key=lambda s: s["candidates"][0]["sift_inliers"])
        world = contexts.get(name)
        best = representative["candidates"][0]
        evidence = [
            {
                "type": "puzzle_layout",
                "time": representative["time"],
                "image": representative["image"],
                "reference": levels[name]["reference"],
                "reason": reason,
            },
            {
                "type": "temporal",
                "entry_black": enter,
                "exit_black": leave,
                "sample_count": len(samples),
            },
        ]
        if world:
            close_path = Path(f"runs/p4/world_close/{name}/check.json")
            close = read_json(close_path)
            world_evidence = {
                **world,
                "status": "verified_by_agent",
                "verification_scope": "terrain_and_entry_cell",
                "close_frame": close["approach_image"],
                "close_time": close["time"],
                "reason": "地形对应关系已对齐；复看进入前较早帧和盾牌出现前后的近帧，玩家落在对应入口格。关卡入口是地面星形节点，不要求门框。",
                "reviewer": "Codex primary; Luna supplied conservative image-only second opinion",
            }
            evidence.append({"type": "overworld", **world_evidence})
        else:
            world_evidence = {
                "status": "no_overworld_context",
                "reason": "该次转场前直接是上一谜题；邻近30秒未显示主世界入口。",
            }
        events.append(
            {
                "event_id": f"p4-{i:02d}",
                "level_id": name,
                "overworld_approach_time": world["time"] if world else None,
                "entry_transition_time": enter["start"],
                "puzzle_start_time": enter["end"],
                "puzzle_end_time": leave["start"],
                "exit_time": leave["end"],
                "timing_uncertainty_seconds": 0.5,
                "status": "visited",
                "outcome": "unknown",
                "review_status": "confirmed",
                "reviewer": "Codex visual comparison (not user acceptance)",
                "candidate_levels": representative["candidates"],
                "confidence": None,
                "confidence_note": "未校准概率；按静态布局及连续样本确认，不能把SIFT内点数解释为置信百分比。",
                "puzzle_match": {
                    **best,
                    "status": "visually_confirmed",
                    "consistent_samples": len(samples),
                },
                "overworld_match": world_evidence,
                "speech_evidence": None,
                "evidence": evidence,
                "manual_corrections": [],
            }
        )
        pairs.extend(
            [
                (
                    f"{i:02d} VIDEO {stamp(representative['time'])} {name}",
                    representative["image"],
                ),
                (f"{i:02d} REFERENCE {name}", levels[name]["reference"]),
            ]
        )
    result = {
        "schema_version": 1,
        "video_bvid": "BV13FH96bE4m",
        "part_number": 4,
        "video": scan["video"],
        "video_sha256": hashlib.sha256(Path(scan["video"]).read_bytes()).hexdigest(),
        "duration": scan["duration"],
        "time_basis": "seconds from current part start; fade boundaries approximate +/-0.5s",
        "map_commit": cat["commit"],
        "events": events,
        "review_note": "身份经Codex静态布局对照及连续样本复核。完成/跳过结局未逐帧判读，保持unknown；用户尚未验收。",
        "non_target_intervals": [
            {"start": a, "end": b, "kind": "overworld", "level_id": None}
            for a, b in [
                (0, 11.375),
                (636.875, 645.375),
                (814.75, 824.75),
                (979.625, 986.875),
                (1432.5, 1515.375),
                (1703.375, 1726.625),
                (1891.375, 1901.75),
                (2026.75, 2033.75),
                (2155.125, 2271.125),
                (2445.25, 2514.25),
                (2582, 2589.25),
                (2697.875, 2705.5),
                (2814.25, 2859.75),
                (3005.75, scan["duration"]),
            ]
        ],
    }
    write_json(target, result)
    for o in range(0, len(pairs), 12):
        contact_sheet(
            pairs[o : o + 12],
            f"results/p4/evidence/identity_{o // 12:02d}.jpg",
            columns=2,
            cell_width=426,
        )
    print(
        f"Saved {len(events)} visually reviewed visits; {len(contexts)} Overworld checks"
    )


if __name__ == "__main__":
    main()
