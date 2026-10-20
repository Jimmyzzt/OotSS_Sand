# 全阶段三地图录入与校对报告

当前范围：P1–67；P68隐藏题目已按用户要求从地图排除，下载/历史证据保留。作者P1–24/P25–44/P45起的阶段边界不变，地图按物理世界而非阶段划分。

当前映射 **912个不同入口、956段时间记录**；**48段未定位、8个目录差集、28组重复ID待核**。时间窗不等于独立进入次数，未定位也不等于原图缺失。逐项理由、全部时间链接、固定参考图及CSV/JSON见[人工校对清单](https://sand.zzt.si/audit.html) / [仓库审计记录](../audit/REPORT.md)。

| 地图 | 不同入口 | 时间记录 | 区域 |
| --- | ---: | ---: | ---: |
| 主世界 | 462 | 469 | 99 |
| 天空世界 | 233 | 240 | 55 |
| 地下世界 | 217 | 247 | 80 |

## 本轮修订

- P02 p2-006（02:16–02:32）：heroes1_1 → heroes1_4.5。入场前地表走到右上排最右格(86,86)，初始绿色角色/目标与参考吻合。相同桥面并不表示相同关卡。
- P43 p43-003/005/009：撤销主世界heroes1_2_v2、heroes1_5_v2的坐标归属。画面在结局二上层关卡内部，具体子关ID待人工核对，保留时间。
- P64 p64-010/012：撤销主世界mirror_1的坐标归属。画面处于结局三地下关卡内部，具体归属待核。
- P05 mirror_4、mirror_14，P24 end1，P50 magnitudes_v3：已检查有界连续帧，存在内部切换/重试/讲解窗误拆风险。保留时间导航并显式标注入口次数待核，没有把它们自动强合并或臆定为不同入口。
- P68的10段示例从地图范围与统计排除；它们未增加独有目录ID。

## 仍需人工核对的原图差集

| 目录ID | 地图 | 坐标 |
| --- | --- | --- |
| arcadia_surprise_big | overworld | [[-24.0, 116.0, 0.0]] |
| best_beam_colors | underworld | [[2.0, 132.0, -24.0]] |
| design_fts | underworld | [[21.0, 131.0, -24.0]] |
| end3_pipeline_setup | underworld | [[-15.0, 117.0, -24.0]] |
| promesst2.5_deeper | overworld | [[-3.0, 73.0, 0.0]] |
| save_for_later | underworld | [[42.0, 83.0, -19.0]] |
| snipperclips_diagonal | overworld | [[11.0, 77.0, 0.0]] |
| snipperclips_square | overworld | [[11.0, 79.0, 0.0]] |

## 方法与限制

全系列已做目录差集、重复ID及结局跨世界规则筛查；本轮有界视觉复核集中在P02、P05、P24、P43/P44、P50、P64，并补查P61/P65/P67。没有声称逐帧重审全部43小时视频。只有静态布局相似、没有角色或入口位置证据时不能据此独立定位。

unknown区间可能包含相连内部房间，不应理解为48个不同漏关。目录差集表示没有可靠已确认记录，不直接证明该关未出现在视频中。重复ID是筛查条件，可能是正常回访/重试，也可能是同构错认；其余24组尚待用户对照。

固定Joric提交：`4ff82651f7af3859a16ebce6197fe363ac40d9a1`；地图Unlicense，Leaflet BSD。原视频和逐帧缓存不入Git，公开证据图册留在results/audit/evidence。大星星来自原图Hero样式，多存档只允许手动标记。

```powershell
python -m ootss import-map --all-worlds
python -m ootss atlas --all-worlds
python scripts/audit_differences.py
python scripts/package_site.py
```
