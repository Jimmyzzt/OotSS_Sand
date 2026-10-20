# 发布与录制索引

公开仓库：[Jimmyzzt/OotSS_Sand](https://github.com/Jimmyzzt/OotSS_Sand)。GitHub Pages是源站；Cloudflare Worker在[sand.zzt.si](https://sand.zzt.si/)代理网页、页面资源和高倍率Joric底图。基础瓦片与参考缩略图随网站保存。Worker只允许GET/HEAD，目标固定，不转发访客Cookie或Authorization，无需为GitHub Actions配置Cloudflare凭证。

## 区域与关卡顺序

网格来自原Joric页面的gridLayer：宽19、高13，中心(80,69)，中心格边界X70.5–89.5/Y62.5–75.5；严格按原坐标定位，各物理地图分别保留有视频访问的区域（原一阶段快照85个）。P5的镜之群岛1–6分别是东1、东2、北1东2、北1东1、南1东3、南1东2，与用户参考图一致。区域左下显示区域名和涉及的分P；放大后标点旁显示关卡序号。网格线独立开关，选定分P时其全部涉及区域加粗；区域标签、关卡标签也可分别关闭。

关卡编号按每个源分P中不同level_id首次出现的时间排列；重复访问不增加编号。P5有30段访问、27个不同关卡，编号1–27。区域路线保留返回：P5先经1、2、3、4，再返回3，之后5、6。地图右上左右箭头顺序前进，返回区域也不会形成导航死循环。选定分P时显示整P列表，选定区域时进一步筛选本区域。

中文主题名根据视频路线及原图area归纳，不视为游戏官方逐格命名。少数作者标题的方位叫法与坐标网格不完全一致（如P7标题南2/南4，而入口数据落在本网格南3/南5），保留题名并按原图坐标画格，不移动入口。data/annotations.json可增加regions字典，以地图ID:网格ID（如sky:1,0）为键，用title覆盖展示名。

录制时先选择分P，打开“网格”看整体路线，再进入区域，点“演示模式”隐藏顶栏。左右键切换区域，Esc退出。右栏保留关卡编号与谜题开始时间。也可用?p=5&record=1进入P5演示模式。当前交付是可用于录屏的页面，没有生成或上传索引视频。

## 主题与手动标注

默认米白浅色，右上可切换柔和深色。“设置”为下拉菜单，可调整标点0.6–2.6倍（默认1.6倍）、标签10–28px。标点随地图缩放，并为总览和近景保留尺寸上下限；白边突出入口，多存档关使用方形。设置保存在本机浏览器。

右侧栏提供列表和紧凑视图，默认紧凑，多列按攻略时间先后显示关卡序号和时间，包括同关卡的再次访问。桌面可拖动左侧分隔条在240–640px内调宽（不超过窗口60%），也可用分隔条的左右键调宽、Home/End切到边界。可收起或展开侧栏。页面固定于视口，关卡内容统一在侧栏内部滚动，滚动条使用透明轨道。

全部分P模式中，单一分P区域的关卡只显示序号；混合区域按分P着色，以“2·1”显示分P与关卡号。同区域、同分P、相邻坐标且序号连续的关卡合并前缀，只在每组首关保留。距离阈值为3.2地图单位；缩放不会改变分组。图例位于右下角，避开区域左下角名称；已移除额外悬浮说明框。

区域选中后点侧栏标题旁的✎，或在设置中选择区域，可保存新名称或恢复默认。区域名称同步到地图、筛选、路线、搜索和关卡详情，与关卡标注共同保存在本机。导出JSON的version=2，regions使用“地图ID:网格ID”（如overworld:1,0）为键；仍兼容旧版version=1的关卡标注文件。

点击关卡弹窗，可勾选多存档关、调整大星星及写备注。大星星初值来自原始Level_Entry的Hero样式；多存档不做自动识别。标注只在当前浏览器保存。“导出手动标注”下载annotations.json，其他浏览器可导入；维护者将文件合并到data/annotations.json，运行uv run python -m ootss atlas --all-worlds并提交，即可更新共享站点。共享标注与本机覆盖值分开。

## 分P插入后的更新

results/series/manifest.json保存原CID和源分P，不要用新合集顺序覆盖它。运行：

```powershell
uv run python scripts/update_video_links.py
uv run python -m ootss atlas --all-worlds
```

脚本读取当前合集，用不可变CID找到原视频的新分P，写入data/video_links.json。丢失原CID会报错，不猜偏移。地图、区域顺序与关卡编号保持源记录不变；分P显示和跳转统一使用映射。当前尚未插入索引视频，映射为空，原链接不变。

## 部署

master上的results/worlds或results/stage1变化触发Publish atlas工作流。scripts/package_site.py默认发布results/worlds，只打包首页、脚本样式、JSON/CSV和assets；原视频、缓存、原帧及本机配置不进入Pages。源站为https://jimmyzzt.github.io/OotSS_Sand/。

Worker配置在wrangler.jsonc，账户和sand.zzt.si已核对。修改Worker后先npm run test:worker、npm run worker:check，再npm run worker:deploy；使用本机Wrangler登录，不写入凭证。普通网页更新只需Pages发布，无需重新部署Worker。

验证包括Python测试、Worker代理测试、标签分组及缩放的Node测试、Ruff、Node语法检查，以及桌面/窄屏布局、透明滚动条、标签开关、拖拽侧栏、手动标注与在线发布的浏览器核验。

右上角选择“主世界 / 天空世界 / 地下世界”；可使用 `?map=sky&p=25`、`?map=underworld&p=45` 深链接。后续阶段回访主世界不会被阶段筛选排除。区域改名以地图ID隔离，同坐标网格不会互相覆盖；导入导出一次包含三地图的本机修改。Worker仅代理三个白名单地图瓦片路径。
