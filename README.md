# 沉星之序 · 塞德莎攻略索引

[打开攻略地图](https://sand.zzt.si/) · [作者 B 站主页](https://space.bilibili.com/2940424) · [文档导航](docs/README.md)

以 Joric 真实地形为背景，按主世界、上方、下方查找关卡，跳转到塞德莎攻略的对应视频时间。收录已审核的原视频 P1–67；源 P68 隐藏内容不参与地图。后续回访主世界的关卡仍显示在主世界。

## 玩家使用

- 地图可拖动、缩放，支持搜索、地图／分 P／区域筛选；双击区域空白处进入单区域视图。
- 点关卡预览，再点时间播放攻略。end1 提供四阶段导航。
- 在「关卡标记」中勾选「已完成关卡」，标点与编号变淡。顶栏「已完成」默认开启，关闭可隐藏完成关卡。进度只在本机保存，可在设置中导出、导入备份。
- 右侧时间轴默认收起，将鼠标移到右侧中间显示展开按钮；展开后同一位置可收起。触屏直接显示按钮。
- 顶栏切换深浅色；设置可调标点、区域标题和编号大小。区域标题默认关闭。自定义文字已下线。
- 关卡弹窗和设置都有「问题反馈」；管理面板在设置 → 数据与来源第一行，仅授权邮箱能登录。

## 本地开发

需要 Python 3.11+、FFmpeg、uv；网页无需前端构建框架。Worker 维护另需 Node.js 24 和 npm。

```powershell
uv sync --locked
npm ci
# Windows 包装脚本将缓存和临时文件放在仓库内。
.\ootss.ps1 atlas --all-worlds
python -m http.server 8765 --directory results
```

打开 `http://127.0.0.1:8765/worlds/`。首次构建需联网下载固定版本的参考目录和地形素材。

```powershell
node --test deployment/*.test.js tests/atlas-ui.test.js
uv run pytest -q --basetemp runs/tests
uv run ruff check ootss tests scripts
uv run ruff format --check ootss tests scripts
```

## 维护资料

- [发布、功能与标注说明](docs/publishing.md)
- [问题反馈与管理面板](docs/feedback.md)
- [视频录入工作流](docs/workflow.md)：少量本地工具配合人工／Agent 审核，不自动裁定关卡身份。
- [入口差异与校对](results/audit/REPORT.md)、[三地图录入报告](results/worlds/REPORT.md)
- [存档导入后续方案](docs/save-import-plan.md)：本次只调研，尚未上线。

`results/p*/reviewed.json` 是审核记录，`data/` 是人工修正和资源版本，`results/worlds/` 是发布产物。早期技术探索说明集中在 `docs/archive/`。原视频、缓存和临时目录不进入 Git；历史阶段快照与校对证据保留供追溯。
