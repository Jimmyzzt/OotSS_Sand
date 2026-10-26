# 原地图图像同步（2026-10-26）

核验上游主仓库 [4ff8265 → 0b70f2f](https://github.com/joric/ootss/compare/4ff82651f7af3859a16ebce6197fe363ac40d9a1...0b70f2fcc0a3d15be7d252f42b103cade2b4dbfc)，图像仓库 [4e7b655 → fe721ce](https://github.com/joric/ootss_tileset/compare/4e7b655375fbc104d69d742ad42d69fd5dd7fd5c...fe721ce403ab8891a37ae05cf6c24282092d05e8)。最新两条图像提交分别修复 sky 首瓦片预热和最高处图像。

- 主仓库标记 1895 → 2653；新增 758 个 Freezer 机关标记。
- 全部 920 个 Level_Entry ID、入口坐标、属性均无变化，新增/删除/变化关卡数均为 0，不触发视频重新匹配。
- images 目录 Git tree SHA 相同，关卡参考图与预览图未变化；原图的检索索引仅移动文件位置。
- 主世界与下方的完整瓦片 Git tree SHA 各自保持不变；sky 在 0–7 级有 954 张瓦片变化，各级依次 1、2、2、6、18、60、193、672。
- 发布包包含 0–3 级，实际更新 sky 11 张。高倍率由 Worker 从同一个固定 Git 提交流式代理；全部瓦片 URL 带完整提交号，避免浏览器复用旧图。
- 原审核、目录与 map_commit 保留原身份核验的提交。图像版本独立记录于 data/map_assets.json 与导出页面的 tileset_revision，不把视觉修复冒充入口身份变化。

复现：git -C cache/map/upstream fetch origin --depth=1，再运行 python scripts/check_map_update.py --ref origin/main。脚本比较快照，仅写差异报告，不切换上游工作树、不修改已审核结果。如果关卡发生变化，应先检查报告，不直接用新坐标覆盖审核。

本次图像版本已写入 data/map_assets.json；重建 atlas 与 atlas --all-worlds 会把固定版本缓存到 cache/map/versions/<commit>/ 并替换已存在的发布副本，避免旧版“文件存在则永久跳过”行为。
