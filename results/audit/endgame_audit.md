# P43/P44 结局场景与跨层复用审计

本报告仅作人工校对清单。检查了 P43 全部 24 条 confirmed、P44 全部 11 条 confirmed，以及两分P全套抽样图册和候选图册；并用 reviewed 数据筛查 P61/P64/P65/P67。P68 按用户要求排除。

## 结论

这里将 catalog `map_layer`（物理地图：Overworld/Sky/Underworld）与 `area`（参考目录分组）分开。P43 的24条 confirmed 中，21条候选ID是 `map_layer=sky, area=endgame2`；p43-003、-005、-009 的候选ID是 `map_layer=overworld, area=heroes1`。P44 的11条 confirmed 全为 `map_layer=sky, area=endgame2`。原审核的 `overworld_approach_time` 均为空。有限入场帧显示 P43 470–475秒处于地图状枢纽，480秒已进入棋盘；P44 10–15秒有地图/标题画面，20秒进入棋盘。这能支持场景转场，但未能看清具体的 Level_Entry 标记或接近路径，无法证明每块局内板都是从 Sky 地图正式入口进入。结局大关内部复用板不能当成物理地图入口。

P43 的13:54与14:10片段夹在结局2天空大关内的棋盘/房间镜头序列中，画面更像同一上层大关的嵌入棋盘或内部视角切换，而不是独立 Overworld 入口；可撤销其主世界归属，但具体end2子关ID仍待核。16:41旧 `heroes1_5_v2` 前后可见天空棋盘、短暂内部房间画面和枢纽回切，倾向局内切换，但现有5秒图册不足以排除独立子关，因此标作存疑、真实ID为null。P44 两段结尾未知区保持 null；它们的候选 shortlist 混有 endgame2/endgame3，不能据此指定物理地图层。

P64 的 `mirror_1` 两次落在结局3（catalog map_layer=underworld, area=endgame3）上下文，属于目录ID的物理层冲突风险。P61/P65/P67 的 confirmed ID 在 catalog 中均为 `map_layer=underworld, area=endgame3`，筛查未见同等明显的早期层冲突。

## 人工校对项

| event_id | 时间 | 旧ID / map_layer / area | 撤销或存疑原因 | 可能真实ID / 场景 |
|---|---:|---|---|---|
| p43-003 | 834.12–845.0s | `heroes1_2_v2` / `overworld` / `heroes1` | 13:54处于同一结局2天空大关的棋盘/房间镜头序列，前后是 endgame2 关卡场景，未出现独立 Overworld 入口过程；旧候选的map_layer=overworld、area=heroes1与视频上下文冲突。高度怀疑是Sky大关内部嵌入棋盘/视角切换，撤销主世界入口识别。具体内部ID未核实。 | `null（局内棋盘ID待核）` / Sky / endgame2 内部场景 |
| p43-005 | 850.0–855.0s | `heroes1_2_v2` / `overworld` / `heroes1` | 14:10处于Sky大关内的棋盘/房间序列，未见返回地图后独立进入；候选的map_layer=overworld、area=heroes1与上下文冲突。静态候选并列（phash均12、SIFT内点均23），只能支持撤销主世界身份，不能据布局确定对应的end2子关。 | `null（end2_heroes_1_2待核）` / Sky / endgame2 内部场景 |
| p43-009 | 1001.12–1010.0s | `heroes1_5_v2` / `overworld` / `heroes1` | 16:40天空棋盘后，16:45出现封闭房间棋盘，17:10回到枢纽；倾向结局2大关内切换，但有界样本不足以排除独立子关。机器主世界候选弱（phash=18、SIFT内点43），end2候选距离更近（10），都不能单独裁决。 | `null（end2_heroes_1_5仅为候选）` / Sky / endgame2 内部场景 |
| p44-012 | 3100.0–3209.5s | `null` / `null` / `null` | 当前reviewed明确为unknown；图册显示大段无标注/连续棋盘操作，短窗口候选仅写endgame2或endgame3弱 shortlist。不要将候选名或切镜当作正式地图入口。 | `null` / 物理地图层与关卡身份均未定 |
| p44-013 | 3235.0–3710.0s | `null` / `null` / `null` | 当前reviewed明确为unknown；后段图册存在多块棋盘/移动镜头，候选仅为endgame2或endgame3弱 shortlist。不能把一个局内板块当作地图入口。 | `null` / 物理地图层与关卡身份均未定 |
| p64-010 | 1765.0–1793.12s | `mirror_1` / `overworld` / `mirror` | 旧ID mirror_1 属于早期 mirror 参考层，但该短片段夹在 end3_redundant_beams 与 p64-009 end2_mirror1 的结局3章节连续段中；参考候选层与所在大关冲突，旧ID可能是局内复用板块。没有主世界/天空入口前帧可验证。 | `end3内部ID或null（不得据旧 mirror_1 直接确认入口）` / endgame3 内部场景（物理世界入口未证明） |
| p64-012 | 2061.75–2080.0s | `mirror_1` / `overworld` / `mirror` | 旧ID mirror_1 再次出现于同一分P后段结局3连续上下文，且先后紧邻 end2_mirror1/end2_mirror_4_islands_v2（均被机器归endgame3）。高度怀疑早期ID布局复用导致跨层误匹配。 | `end3内部ID或null` / endgame3 内部场景（物理世界入口未证明） |

## 图片证据

证据图片均复制自本地 runs 图册或既有 evidence 候选图册；未访问/上传视频，也未使用外部识别服务。图册显示有限时间点，不能取代逐帧核对。

- P43 13:20–15:55 及 16:00–18:35 连续样本：[sheet 05](evidence/endgame_p43_sheet_05.jpg)、[sheet 06](evidence/endgame_p43_sheet_06.jpg)；匹配对照：[候选 00](evidence/endgame_p43_candidates_00.jpg)、[候选 01](evidence/endgame_p43_candidates_01.jpg)。
- P44 开头与结尾有限样本：[sheet 00](evidence/endgame_p44_sheet_00.jpg)、[sheet 01](evidence/endgame_p44_sheet_01.jpg)；候选：[候选 00](evidence/endgame_p44_candidates_00.jpg)、[候选 03](evidence/endgame_p44_candidates_03.jpg)。
- P64 跨层复用候选：[候选 01](evidence/endgame_p64_candidates_01.jpg)、[候选 02](evidence/endgame_p64_candidates_02.jpg)。
- 入场帧：[P43 470秒](evidence/endgame_p43_before_entry_470.jpg)、[475秒](evidence/endgame_p43_before_entry_475.jpg)、[480秒](evidence/endgame_p43_after_entry_480.jpg)；[P44 10秒](evidence/endgame_p44_map_010.jpg)、[15秒](evidence/endgame_p44_before_entry_015.jpg)、[20秒](evidence/endgame_p44_after_entry_020.jpg)。

P43/P44 confirmed event 的旧ID、catalog map_layer 与 area逐条记录在 `endgame_audit.json` 的 `reviewed_confirmed_events`。候选ID的物理地图归属不能替代视频中的入口证据；结果未改写既有 reviewed 数据。
