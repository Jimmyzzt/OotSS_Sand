# 全阶段三地图录入报告

范围：塞德莎同一合集P1–68；作者标题界定P1–24/P25–44/P45–68三个阶段。三张地图按物理世界归类，阶段二、三回访主世界的关卡仍在主世界。原P1–24快照保留在results/stage1。

68/68分P已有独立reviewed.json。收录911个不同Level_Entry、971段确认画面访问/示例；另有43段未可靠定位，保留视频起止时间并单列，不绘制猜测坐标。固定参考目录920个入口中，9个尚无可靠观察记录；这不等于视频中一定没出现。

| 地图 | 已确认不同入口 | 时间记录 | 涉及网格 |
| --- | ---: | ---: | ---: |
| 主世界 | 461 | 478 | 99 |
| 天空世界 | 233 | 246 | 55 |
| 地下世界 | 217 | 247 | 80 |

编号按每个源分P不同level_id首次出现顺序，跨地图仍使用全片统一编号。重复访问沿用编号、保留各自时间；多入口保留全部坐标。P68属于开发回顾，其中10段正式版对照示例带context说明，原型棋盘、博物馆、外部地图游览与隐藏录音不冒充正式版入口。P1为前言、P60为外部地图机制操作，没有独立Level_Entry记录。

## 复核与限制

- 全部5秒时间轴联系表、机器候选对照图由Codex/Luna看图；存在缺口时使用局部恢复图册和有界高分辨率帧。机器proposed与人工reviewed分开保存，重复运行不覆盖审核。
- 静态布局确认不等于外部入口核验。未核实的overworld_match仍为unverified；未证实的完成状态仍为unknown。后续阶段部分视频的精确入场边界只有约5秒采样精度，弹窗保留各条uncertainty。
- 大型连续棋盘、重复拼接场景与结局附赠房间有未定位片段，尤其P37/P38/P50；unknown区间可能包含连续内部房间，不能把43段理解为43个不同漏关。
- 所有68份审核通过目标目录校验、事件ID唯一性与时间范围检查；同一分P事件区间无重叠。18项Python测试、8项Node测试、Ruff与浏览器三地图切换/桌面/390px窄屏/名称导入导出核验通过。
- 大星星初值来自原地图Hero mesh，多存档仅手动标记；区域中文名为便于浏览的归纳名，可本地修改。

## 分P统计

| 源分P | 阶段 | 已确认入口 | 确认时间记录 | 未定位片段 |
| --- | ---: | ---: | ---: | ---: |
| P01 | 1 | 0 | 0 | 0 |
| P02 | 1 | 20 | 21 | 0 |
| P03 | 1 | 30 | 30 | 0 |
| P04 | 1 | 29 | 29 | 0 |
| P05 | 1 | 27 | 30 | 0 |
| P06 | 1 | 1 | 1 | 0 |
| P07 | 1 | 3 | 3 | 0 |
| P08 | 1 | 2 | 2 | 0 |
| P09 | 1 | 10 | 10 | 0 |
| P10 | 1 | 29 | 29 | 0 |
| P11 | 1 | 20 | 20 | 0 |
| P12 | 1 | 14 | 14 | 0 |
| P13 | 1 | 28 | 28 | 0 |
| P14 | 1 | 16 | 16 | 0 |
| P15 | 1 | 16 | 16 | 0 |
| P16 | 1 | 27 | 27 | 0 |
| P17 | 1 | 29 | 29 | 0 |
| P18 | 1 | 15 | 15 | 0 |
| P19 | 1 | 9 | 9 | 0 |
| P20 | 1 | 27 | 27 | 0 |
| P21 | 1 | 15 | 15 | 0 |
| P22 | 1 | 14 | 14 | 0 |
| P23 | 1 | 13 | 13 | 0 |
| P24 | 1 | 1 | 5 | 0 |
| P25 | 2 | 8 | 8 | 0 |
| P26 | 2 | 20 | 20 | 0 |
| P27 | 2 | 10 | 10 | 0 |
| P28 | 2 | 21 | 21 | 0 |
| P29 | 2 | 14 | 14 | 0 |
| P30 | 2 | 14 | 14 | 0 |
| P31 | 2 | 31 | 32 | 0 |
| P32 | 2 | 16 | 16 | 0 |
| P33 | 2 | 16 | 16 | 0 |
| P34 | 2 | 15 | 15 | 0 |
| P35 | 2 | 14 | 14 | 0 |
| P36 | 2 | 12 | 13 | 0 |
| P37 | 2 | 2 | 2 | 1 |
| P38 | 2 | 2 | 2 | 2 |
| P39 | 2 | 15 | 15 | 0 |
| P40 | 2 | 18 | 18 | 0 |
| P41 | 2 | 17 | 17 | 0 |
| P42 | 2 | 27 | 27 | 0 |
| P43 | 2 | 19 | 24 | 0 |
| P44 | 2 | 10 | 11 | 2 |
| P45 | 3 | 1 | 1 | 0 |
| P46 | 3 | 7 | 9 | 0 |
| P47 | 3 | 14 | 14 | 0 |
| P48 | 3 | 20 | 22 | 0 |
| P49 | 3 | 16 | 19 | 0 |
| P50 | 3 | 2 | 11 | 14 |
| P51 | 3 | 12 | 13 | 4 |
| P52 | 3 | 7 | 7 | 2 |
| P53 | 3 | 11 | 12 | 4 |
| P54 | 3 | 7 | 8 | 0 |
| P55 | 3 | 15 | 15 | 0 |
| P56 | 3 | 10 | 10 | 0 |
| P57 | 3 | 23 | 26 | 0 |
| P58 | 3 | 15 | 15 | 0 |
| P59 | 3 | 20 | 20 | 0 |
| P60 | 3 | 0 | 0 | 0 |
| P61 | 3 | 7 | 10 | 1 |
| P62 | 3 | 5 | 5 | 0 |
| P63 | 3 | 6 | 6 | 0 |
| P64 | 3 | 7 | 9 | 0 |
| P65 | 3 | 5 | 8 | 9 |
| P66 | 3 | 3 | 4 | 0 |
| P67 | 3 | 5 | 5 | 4 |
| P68 | 3 | 10 | 10 | 0 |

## 未定位片段

选择对应分P可在网页右栏下方看到时间链接；完整理由和截图索引保存在各reviewed.json。

| 分P | 开始 | 结束 |
| --- | --- | --- |
| P37 | [01:45](https://www.bilibili.com/video/BV13FH96bE4m/?p=37&t=105) | 25:20 |
| P38 | [02:55](https://www.bilibili.com/video/BV13FH96bE4m/?p=38&t=175) | 38:10 |
| P38 | [38:50](https://www.bilibili.com/video/BV13FH96bE4m/?p=38&t=2330) | 42:44 |
| P44 | [51:40](https://www.bilibili.com/video/BV13FH96bE4m/?p=44&t=3100) | 53:29 |
| P44 | [53:55](https://www.bilibili.com/video/BV13FH96bE4m/?p=44&t=3235) | 61:50 |
| P50 | [01:10](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=70) | 03:40 |
| P50 | [04:05](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=245) | 04:45 |
| P50 | [05:15](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=315) | 07:00 |
| P50 | [08:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=480) | 09:15 |
| P50 | [10:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=600) | 11:55 |
| P50 | [13:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=780) | 14:15 |
| P50 | [15:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=900) | 15:39 |
| P50 | [15:50](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=950) | 17:25 |
| P50 | [19:15](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1155) | 21:30 |
| P50 | [21:45](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1305) | 23:00 |
| P50 | [23:05](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1385) | 25:20 |
| P50 | [25:25](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1525) | 26:45 |
| P50 | [26:50](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1610) | 28:30 |
| P50 | [28:35](https://www.bilibili.com/video/BV13FH96bE4m/?p=50&t=1715) | 29:45 |
| P51 | [00:14](https://www.bilibili.com/video/BV13FH96bE4m/?p=51&t=14) | 00:24 |
| P51 | [00:35](https://www.bilibili.com/video/BV13FH96bE4m/?p=51&t=35) | 04:25 |
| P51 | [16:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=51&t=960) | 16:55 |
| P51 | [24:50](https://www.bilibili.com/video/BV13FH96bE4m/?p=51&t=1490) | 25:20 |
| P52 | [02:45](https://www.bilibili.com/video/BV13FH96bE4m/?p=52&t=165) | 03:30 |
| P52 | [15:20](https://www.bilibili.com/video/BV13FH96bE4m/?p=52&t=920) | 15:45 |
| P53 | [03:05](https://www.bilibili.com/video/BV13FH96bE4m/?p=53&t=185) | 03:22 |
| P53 | [13:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=53&t=780) | 13:20 |
| P53 | [22:25](https://www.bilibili.com/video/BV13FH96bE4m/?p=53&t=1345) | 25:55 |
| P53 | [28:15](https://www.bilibili.com/video/BV13FH96bE4m/?p=53&t=1695) | 28:50 |
| P61 | [36:03](https://www.bilibili.com/video/BV13FH96bE4m/?p=61&t=2163) | 42:32 |
| P65 | [02:35](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=155) | 07:00 |
| P65 | [07:15](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=435) | 08:50 |
| P65 | [09:15](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=555) | 10:52 |
| P65 | [11:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=660) | 12:28 |
| P65 | [13:10](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=790) | 21:30 |
| P65 | [22:10](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=1330) | 25:00 |
| P65 | [25:20](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=1520) | 28:25 |
| P65 | [28:45](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=1725) | 31:10 |
| P65 | [31:28](https://www.bilibili.com/video/BV13FH96bE4m/?p=65&t=1888) | 34:30 |
| P67 | [19:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=67&t=1140) | 21:10 |
| P67 | [21:25](https://www.bilibili.com/video/BV13FH96bE4m/?p=67&t=1285) | 26:30 |
| P67 | [26:40](https://www.bilibili.com/video/BV13FH96bE4m/?p=67&t=1600) | 30:30 |
| P67 | [31:00](https://www.bilibili.com/video/BV13FH96bE4m/?p=67&t=1860) | 32:04 |

尚无可靠观察记录的目录ID：`arcadia_surprise_big`, `best_beam_colors`, `design_fts`, `end3_pipeline_setup`, `heroes1_4.5`, `promesst2.5_deeper`, `save_for_later`, `snipperclips_diagonal`, `snipperclips_square`。

## 来源与复现

地图/参考图：Joric OotSS，固定提交`4ff82651f7af3859a16ebce6197fe363ac40d9a1`，地图Unlicense；Leaflet 1.9.4 BSD许可随assets保存。原视频已公开，原视频、逐帧缓存和下载参考不入Git。仓库仅保存审核、候选证据图册与可浏览结果。

```powershell
python -m ootss import-map --all-worlds
python -m ootss atlas --all-worlds
python scripts/package_site.py
```

右上选择主世界/天空世界/地下世界；`?map=sky&p=25`或`?map=underworld&p=45`可直达。区域名和关卡标注使用version=2 JSON本地保存、导入导出；不同地图同网格互不覆盖。
