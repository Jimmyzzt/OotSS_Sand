# 沉星之序：视频关卡笔记工具

用途：把本地攻略视频交给 Codex，利用抽帧图册、转场和参考图候选，完成关卡时间及地图坐标记录。以可核对的实际结果为目标，不建设全自动平台。

Python 3.13、FFmpeg/ffprobe、Git；依赖用 uv 管理。无需 API Key。原视频不上传。

```powershell
$env:UV_CACHE_DIR = 'F:\Video\.cache\uv'
# 若 Windows 沙箱临时目录拒绝访问，将 TEMP 和 TMP 指向项目 cache/tmp
uv sync
uv run python -m ootss --help
```

操作步骤见 [docs/workflow.md](docs/workflow.md)。实际 P4 结果放在 `results/p4/`，大体积缓存放在 `runs/p4/` 和 `cache/map/`。

地图、参考图及 pHash/HSV 算法来源：[Joric OotSS](https://github.com/joric/ootss)，Unlicense。地图版本、素材来源和映射缺失记录在 catalog.json。当前上游图片已移至 `ootss_tileset`，不在主仓库 images/ 目录。

机器检索只提供候选；没有视觉证据就写 unknown。进入前主世界的核验单独记录，不因候选坐标存在而声称验证成功。该工具不依赖字幕或付费模型；需要时由 Codex 读取局部图册补充判断。
