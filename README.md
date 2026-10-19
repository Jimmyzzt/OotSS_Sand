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

**本次验收先打开 [P4 索引](results/p4/index.html)**（本地静态文件，双击即可，无需启动服务）；也可直接读 [Markdown 表格](results/p4/index.md) 和 [验收说明](results/p4/REPORT.md)。共29个关卡身份已由 Codex 对照画面确认，13个入口有独立主世界证据，尚待你验收。

Windows 快捷入口（自动把临时目录放进项目，首次自动同步依赖）：

```powershell
.\ootss.ps1 import-map
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

本地验证：`uv run pytest -q --basetemp runs/tests`、`uv run ruff check ootss tests scripts`。8项测试通过；实现取舍、真实计时及质量限制见 [实施记录](docs/implementation_notes.md)。
