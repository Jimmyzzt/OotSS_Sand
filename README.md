# 沉星之序：视频关卡笔记工具

用途：把本地攻略视频交给 Codex，利用抽帧图册、转场和参考图候选，完成关卡时间及地图坐标记录。以可核对的实际结果为目标，不建设全自动平台。

Python 3.13、FFmpeg/ffprobe、Git；依赖用 uv 管理。无需 API Key。原视频不上传。

```powershell
$env:UV_CACHE_DIR = 'F:\Video\.cache\uv'
# 若 Windows 沙箱临时目录拒绝访问，将 TEMP 和 TMP 指向项目 cache/tmp
uv sync
uv run python -m ootss --help
```

你以后直接把视频路径、BVID 和分 P 给 Codex 即可，不需要自己逐条操作。操作步骤见 [docs/workflow.md](docs/workflow.md)。

**在线入口：[sand.zzt.si](https://sand.zzt.si/) · [GitHub Pages](https://jimmyzzt.github.io/OotSS_Sand/) · [公开仓库](https://github.com/Jimmyzzt/OotSS_Sand)**

本地可打开 [三地图攻略索引](results/worlds/index.html)（筛选栏选择主世界、天空世界、地下世界），或保留的 [一阶段快照](results/stage1/index.html)：真实 Joric 地形，可拖动、缩放、搜索关卡、按分 P 筛选；点击标记查看参考布局，再点击时间跳转对应攻略。双击本地 HTML 即可，低倍率地图离线可用，高倍率瓦片需要联网。

一阶段按作者标题界定为 **P1–P24**，24个分 P 全部看图审核，共收录 **396个不同的 Overworld Level_Entry、403段访问**，仅按视频出现收录，没有将全部466个Overworld入口填入。一阶段验收、统计及限制见 [REPORT.md](results/stage1/REPORT.md)，明细可用 [CSV](results/stage1/visits.csv)。P1为前言/操作说明，没有独立关卡访问。大型关卡内部的相邻房间归入对应入口访问，不额外杜撰地表坐标。

完整系列 **68/68个分 P 已下载**，最高480p、保留音频，共约43小时57分钟、6.21GiB。文件在 `inputs/series/stage1`、`stage2`、`stage3`，以 `P编号__原标题` 命名；[下载清单](results/series/inventory.md) / [CSV](results/series/inventory.csv) / [可续传台账](results/series/manifest.json)。P4复用原视频；P17修复版文件名带 `__recovered`，台账保留实际路径，避免抽帧缓存失去来源。

[P4详细索引](results/p4/index.html) 与 [P4互动地图](results/p4/atlas/index.html) 也已换成真实地形；原有29关的审核不变。

Windows 快捷入口（自动把临时目录放进项目，首次自动同步依赖）：

```powershell
.\ootss.ps1 import-map
.\ootss.ps1 series --discover-only
# 首次批量下载或断点续传（默认两路并发）：
.\ootss.ps1 series
# 导入三地图参考目录，重建P1–67综合地图（P68隐藏内容已排除）：
.\ootss.ps1 import-map --all-worlds
.\ootss.ps1 atlas --all-worlds
# 仅重建原P1–24快照：
.\ootss.ps1 atlas
.\ootss.ps1 scan --video 'inputs/你的文件.mp4' --out runs/p5 --interval 5 --black-min 0.125
.\ootss.ps1 match --run runs/p5
.\ootss.ps1 packet --run runs/p5 --start 100 --end 120 --step 2
# Codex 看图并写审核 JSON 后：
.\ootss.ps1 export --review results/p5/reviewed.json --out results/p5
```

如果 PowerShell 执行策略不允许运行脚本，可在当前终端按前述临时目录说明设置后直接 `uv run python -m ootss ...`，无需修改系统执行策略。

实际 P4 结果放在 `results/p4/`，大体积缓存放在 `runs/p4/` 和 `cache/map/`。审核结果与机器候选分开，重跑不会覆盖审核记录。

地图、参考图及 pHash/HSV 算法来源：[Joric OotSS](https://github.com/joric/ootss)，Unlicense。地图版本、素材来源和映射缺失记录在 catalog.json。当前上游图片已移至 `ootss_tileset`，不在主仓库 images/ 目录。

机器检索只提供候选；没有视觉证据就写 unknown。进入前主世界的核验单独记录，不因候选坐标存在而声称验证成功。该工具不依赖字幕或付费模型；需要时由 Codex 读取局部图册补充判断。

本地验证：`uv run pytest -q --basetemp runs/tests`、`uv run ruff check ootss tests scripts`。19项Python测试、8项Worker/前端Node测试通过；实现取舍、真实计时及质量限制见 [实施记录](docs/implementation_notes.md)。


区域视图沿用原地图19×13网格，三地图分别维护区域；原一阶段快照涉及85个区域。选定分P后，右栏显示该P的关卡序号和开始时间；同一关重复访问沿用首次编号。点击区域放大，地图左下显示区域名。P5的镜之群岛1–6与参考图一致。演示模式隐藏顶栏，用左右箭头沿区域路线前进，Esc退出，适合录制阶段索引。

默认米白浅色，可切换深色；设置中可调整标点、标签大小。区域名可修改，并与关卡标注一起保存在本机、导入导出。关卡弹窗可手工勾选多存档关、调整大星星标记或写备注，保存在本机，可导出/导入JSON。维护者把导出结果写入 `data/annotations.json` 后用 `atlas --all-worlds` 重建即可发布共享标注。

插入索引分P后，运行 `uv run python scripts/update_video_links.py`，按CID匹配新分P，再重建 `atlas --all-worlds`；源分P与关卡编号保持不变。发布、手动标注与录屏操作见 [部署说明](docs/publishing.md)。

综合地图仅使用画面对照确认的访问（P68隐藏内容按用户要求排除），后续阶段回访主世界仍归主世界。未能定位的棋盘保留时间链接，不绘制猜测坐标；各地图、分P统计和限制见 [综合录入报告](results/worlds/REPORT.md)。

人工校对入口：[在线差异清单](https://sand.zzt.si/audit.html) / [审计记录](results/audit/REPORT.md)。P02同构桥面已结合初始角色和入场位置改正；结局篇跨世界错配撤销旧坐标。未定位、目录差集和重复ID分别列出，均不能据此自动认定新关卡或独立进入次数。
