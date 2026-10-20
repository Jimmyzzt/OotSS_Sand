# 三地图索引：用户连续性校对后

已应用[用户校对原文](../../docs/校对.md)全部19条，影响11个分P。P1–67参与地图，P68隐藏题目仍排除。当前914个不同入口、941条关卡时间记录；未定位由48段减为2段（均在P44），原图目录差集由8个减为6个。

| 地图 | 不同入口 | 时间记录 | 区域 |
| --- | ---: | ---: | ---: | ---: |
| 主世界 | 463 | 470 | 99 |
| 天空世界 | 233 | 236 | 55 |
| 地下世界 | 218 | 235 | 80 |

## 已应用的主要变化

- P37新增promesst2.5_deeper（01:45–25:20）；P61新增best_beam_colors（36:03–42:32）。坐标来自固定目录，身份依据用户确认。
- P38合并为两条连续访问，后续内部房间不再作为未知片段。
- P43将13:54、14:10、16:41及重复参考匹配并回所属结局关卡；前两关交界保留有界14:17–14:24图册作为辅助证据。P64的两条旧mirror_1错配并回end2_mirror1。
- P50开头至29:45合为magnitudes_v3一次连续访问，取消十次重复开始时间和14条内部未知片段。
- P51首关修为00:25–04:10；P51/P52/P53/P67共13条大世界时间段记录移入排除清单，不再认为进了未知关卡。
- P53的22:25–25:55并回monster_promesst_v3；P65合并为5条连续关卡，时间范围按用户逐项确认。

旧事件原文保存在各审核文件superseded_events，明确的大世界片段在excluded_segments（kind=world）。[人工清单](https://sand.zzt.si/audit.html)已经移除解决的问题，并显示用户确认后的连续区间及世界片段。剩余21组重复ID尚未在这19条中全部裁决，可能是回访/重试；未擅自合并。

## 剩余差异

未定位：P44 51:40–53:29.5、53:55–61:50。它们未被本次用户校对覆盖，继续保留未知身份。

| 目录ID | 地图 | 坐标 |
| --- | --- | --- |
| arcadia_surprise_big | overworld | [[-24.0, 116.0, 0.0]] |
| design_fts | underworld | [[21.0, 131.0, -24.0]] |
| end3_pipeline_setup | underworld | [[-15.0, 117.0, -24.0]] |
| save_for_later | underworld | [[42.0, 83.0, -19.0]] |
| snipperclips_diagonal | overworld | [[11.0, 77.0, 0.0]] |
| snipperclips_square | overworld | [[11.0, 79.0, 0.0]] |

目录差集不是视频未出现的证明；未定位也不直接表示原图没有该关。入口位置、身份和完成状态分开记录，用户确认没有切关不代表确认通关。

## 复现与验证

```powershell
python scripts/apply_human_corrections.py
python -m ootss atlas --all-worlds
python scripts/audit_differences.py
python scripts/package_site.py
```

应用脚本核对用户笔记的规范化文本SHA256，重复执行不会再次合并，已对11份真实审核文件验证幂等。22项Python测试、8项Node测试、Ruff通过；另验证全67份审核及区间无重叠。原视频和逐帧缓存不入Git。

Joric固定提交：`4ff82651f7af3859a16ebce6197fe363ac40d9a1`，地图Unlicense，Leaflet BSD。
