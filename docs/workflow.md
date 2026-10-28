# 给后续 Codex 的操作流程

1. 确认用户视频、BVID、分 P。处理完整系列时运行 `python -m ootss import-map --all-worlds`（主世界/上方/下方/序章参考目录写入catalog_all.json）；处理一阶段旧快照可用 `python -m ootss import-map`（默认复用已固定版本，不自动拉取）。
2. `python -m ootss scan --video "inputs/xxx.mp4" --out runs/p4`。默认 8fps 黑屏扫描、15s 图册采样，一次低分辨率解码。scan.json 保存来源签名和元数据。先查看所有 sheet，防止忽略没有黑屏的连续关卡。
3. `python -m ootss match --run runs/p4` 生成机器候选，不写已确认事件。逐项看参考图，必要时用 `packet` 在短窗口密集抽帧。不要把主世界探索当独立谜题。
4. 关卡确认需检查静态布局、角色或机关位置关系。低 pHash 距离不足以确认。SIFT 内点也只是候选证据，重复地砖会误匹配。
5. 在进入前 10–30s 抽帧，将主世界地标和候选局部地图并排看。无法核验时写 `unverified` 或 `no_overworld_context`。不要凭同一检索候选自行循环证明。
6. 把判断写入独立 reviewed.json：关卡 ID、起止时间、时间误差范围、接近与转场时间、截图路径、理由、未知/冲突。一次访问一条记录，可多次访问同关卡。完成状态仅依据视频，无法确认则 unknown。
7. 可用 Luna 子 agent 对有界图册复核；明确要求返回 evidence/unknown/conflicts，不发送全视频，不调用外部模型 API。
8. `python -m ootss export --review results/p4/reviewed.json --out results/p4`，生成 JSON/CSV/Markdown 和静态 SVG/PNG 坐标图。地图跳转使用上游 `#level_id`。

主世界核验示例（坐标顺序 LEFT BOTTOM RIGHT TOP；先用参考图候选缩小地图范围）：

```powershell
python -m ootss terrain --bounds 69 113 90 129 --out runs/p4/terrain_heroes3_raw.jpg --raw
python -m ootss world-check --run runs/p4 --time 9 --level heroes3_10 --terrain runs/p4/terrain_heroes3_raw.jpg --bounds 69 113 90 129 --out runs/p4/check_001
```

查看 overlay.jpg；地形对齐充分仍不等于关卡验证完成。红圈应在可见入口格，角色接近/进入前的连续帧也应对应。分数不足时改用较早、未被盾牌遮挡的帧；不要降低阈值强行接受。多入口的关卡必须先消除歧义。

审核文件最小结构（真实关卡替换 null；身份未确认可保持 null 和 unknown）：

```json
{
  "video_bvid": "BV...",
  "part_number": 5,
  "duration": 120,
  "events": [{
    "event_id": "p5-01",
    "level_id": null,
    "puzzle_start_time": 10,
    "puzzle_end_time": 30,
    "entry_transition_time": 9.5,
    "overworld_approach_time": null,
    "exit_time": 30.5,
    "review_status": "unknown",
    "outcome": "unknown",
    "evidence": []
  }]
}
```

完整字段和本次判断理由可参考 `results/p4/reviewed.json`。`scripts/curate_p4.py` 只保存本次已完成的视觉判断，并拒绝覆盖现有审核；不可把它当自动确认器用于新视频。`scripts/p4_evidence.py` 复现本次主世界图包；`scripts/snapshot_p4.py` 保存机器候选和固定版本素材核验。

全部时间为当前分 P 开始后的秒数。扫描时间为 fps 采样近似值；不能用平均 FPS 推算可变帧率视频的精确帧号。必要时从 FFmpeg 输出 PTS 复查。更换视频、采样参数或算法版本会失效扫描缓存；不要在同一个输出目录处理不同视频。机器重跑永远不写 reviewed.json。

## 整个系列与真实地图

`python -m ootss series --discover-only` 更新作者的68个分P元数据；`python -m ootss series` 默认两路并发，yt-dlp下载最高480p与低码率音频，FFmpeg流复制合并。作者标题确定P1–24/P25–44/P45–68的阶段边界。`results/series/manifest.json`是可续传台账，记录实际路径、CID、完成状态及ffprobe时长；重跑保留同CID已有修复文件的路径，不要随意改名破坏抽帧来源。普通提取失败时，使用公开playurl授权返回的普通备用CDN，仍用yt-dlp下载；失败保留为failed，不伪造完成。

已下载后 `python -c "from ootss.batch import propose; propose(25, catalog_path='cache/map/catalog_all.json')"` 可以为指定分P做5秒采样、检索与候选对照图册，但只写proposed.json。看完全部时间轴图册后再写reviewed.json；不要将稀疏匹配的最后一帧当作关卡结束。大幅滚屏或内部房间切换会让pHash/局部特征失效，`python -c "from ootss.recovery import recover; recover(25, catalog_path='cache/map/catalog_all.json')"` 可在审核未覆盖区间请求640宽局部帧，不自动裁决。

同一入口可能通往多个相连房间。需检查进出黑场、世界画面、箭头连续移动及返回起始参考布局的证据，再决定是否为一次Level_Entry访问；既不要把风格一致的所有房间强配成一张棋盘，也不要把每次镜头滚动当成一个新地表入口。不能确定则保留unknown。

`python -m ootss atlas` 读取P1–24审核JSON，生成 `results/stage1/index.html`、index.json和visits.csv。默认只标confirmed且属于目标目录的ID，不填入未出现的入口；同关多次访问共用地图点。HTML内嵌数据，Leaflet、0–3级地图瓦片及关卡缩略图本地保存，直接双击可用，更高倍率瓦片联网加载。`?p=22`可直接筛选分P。`export`的SVG/PNG默认也使用真实地形背景。

若需要5秒增密和允许短黑场，使用 `scan --interval 5 --black-min 0.125`。P4 的01:59转场只有一个8fps采样，0.25秒默认过滤会漏掉；允许单帧后应看前后截图过滤误报。扫描留存 `black_scores.npz`，无需重新解码即可试验黑场合并规则。图像样本损坏/缺失会触发重算；同目录换成另一个视频版本则报错，防止局部图包混用。

原 starting_guide.md 已由上述工作流及实际结果说明替代：不实现 ASR 服务、Web 审核平台、复杂 Agent Adapter、自动训练、GitHub Issue 工程管理。GitHub CLI 凭证失效时继续本地提交。

综合发布使用 `python -m ootss atlas --all-worlds`，读取P1–68和catalog_all.json，输出results/worlds。地图按物理世界命名，阶段二/三回访主世界仍归Overworld；同一分P跨地图时保留全片统一的首次出现序号。未定位片段以时间链接单列，不能只因参考目录有坐标就纳入地图。2026-10-28 用户明确要求将源P68（现P69）的序章示例重新收录；仅允许新 markers_intro.json 中的独立入口，禁止把开发版／现行版演示复用到旧三地图。世界游览、画廊和隐藏录音仍排除。

复核同构关时先对比初始角色/机关，再看入场前10–20秒地表位置与固定入口坐标。结局篇内部棋盘复用不等于回到早期世界。若只有相似布局但世界/角色冲突，撤销旧ID、保留候选与时间，交人工核对。运行 `python scripts/audit_differences.py` 生成在线audit.html、CSV和JSON；目录差集不直接证明视频没出现，重复ID也不直接证明多次进入。

用户对连续片段的明确校对优先于相似布局检索结果。`docs/校对.md` 的19条已转为 `data/human_corrections.json`，由 `python scripts/apply_human_corrections.py` 应用；同一份校对重复运行不重复合并。旧事件保存在superseded_events，大世界片段存入excluded_segments（kind=world），不再列为未定位关卡。不要再次用稀疏参考命中把用户确认的长关拆开。

作者后续补充的6个位置记录在`docs/缺失录像位置.md`和`data/creator_locations.json`，用`python scripts/apply_creator_locations.py`应用；脚本同样校验文本散列、拒绝区间重叠并保留旧事件。P39作者提供的00:56实际属于已有0_square，diagonal按录像位置修正为03:47。不要用旧的稀疏候选覆盖这三关的完整连续区间，也不要为了清空差集在同一时间添入两个ID。新资料若与已应用计划不同，先核对并更新计划，不能只重复执行旧脚本。

序章使用 `data/intro_map.json` 固定补充源与独立投影，保留旧主目录版本。`data/intro_visits.json` 是本次有界画面对照计划，`python -m scripts.apply_intro_review` 幂等应用并保存旧审核。复用旧缓存5秒图册与10段正式版审核，新增14段开发示例；仅对退场等疑点补1秒局部帧。现P68的序章走动不覆盖 docs/校对.md 确认的大世界排除。详见 [序章专项校对](../results/upstream/INTRO.md)。
