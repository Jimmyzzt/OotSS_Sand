# 发布与录制索引

公开仓库：[Jimmyzzt/OotSS_Sand](https://github.com/Jimmyzzt/OotSS_Sand)。GitHub Pages是源站；Cloudflare Worker在[sand.zzt.si](https://sand.zzt.si/)代理网页、页面资源和高倍率Joric底图。基础瓦片与参考缩略图随网站保存。Worker只允许GET/HEAD，目标固定，不转发访客Cookie或Authorization，无需为GitHub Actions配置Cloudflare凭证。

## 区域与关卡顺序

网格来自原Joric页面的gridLayer：宽19、高13，中心(80,69)，中心格边界X70.5–89.5/Y62.5–75.5；严格按原坐标定位，保留85个有视频访问的区域。P5的镜之群岛1–6分别是东1、东2、北1东2、北1东1、南1东3、南1东2，与用户参考图一致。区域左下显示涉及的分P，放大后下方显示区域名，星点上显示关卡序号。

关卡编号按每个源分P中不同level_id首次出现的时间排列；重复访问不增加编号。P5有30段访问、27个不同关卡，编号1–27。区域路线保留返回：P5先经1、2、3、4，再返回3，之后5、6。地图右上左右箭头顺序前进，返回区域也不会形成导航死循环。选定分P时显示整P列表，选定区域时进一步筛选本区域。

中文主题名根据视频路线及原图area归纳，不视为游戏官方逐格命名。少数作者标题的方位叫法与坐标网格不完全一致（如P7标题南2/南4，而入口数据落在本网格南3/南5），保留题名并按原图坐标画格，不移动入口。data/annotations.json可增加regions字典，以网格ID（如1,0）为键，用title覆盖展示名。

录制时先选择分P，点“区域划分”看整体路线，再进入区域，点“演示模式”隐藏顶栏。左右键切换区域，Esc退出。右栏保留关卡编号与谜题开始时间。也可用?p=5&record=1进入P5演示模式。当前交付是可用于录屏的页面，没有生成或上传索引视频。

## 主题与手动标注

默认米白浅色，右上可切换柔和深色。“设置”中可调整标点0.6–2倍、标签10–28px，保存在本机浏览器。

点击关卡弹窗，可勾选多存档关、调整大星星及写备注。大星星初值来自原始Level_Entry的Hero样式；多存档不做自动识别。标注只在当前浏览器保存。“导出手动标注”下载annotations.json，其他浏览器可导入；维护者将文件合并到data/annotations.json，运行uv run python -m ootss atlas并提交，即可更新共享站点。共享标注与本机覆盖值分开。

## 分P插入后的更新

results/series/manifest.json保存原CID和源分P，不要用新合集顺序覆盖它。运行：

```powershell
uv run python scripts/update_video_links.py
uv run python -m ootss atlas
```

脚本读取当前合集，用不可变CID找到原视频的新分P，写入data/video_links.json。丢失原CID会报错，不猜偏移。地图、区域顺序与关卡编号保持源记录不变；分P显示和跳转统一使用映射。当前尚未插入索引视频，映射为空，原链接不变。

## 部署

master上的results/stage1变化触发Publish atlas工作流。scripts/package_site.py只打包首页、脚本样式、JSON/CSV和assets；原视频、缓存、原帧及本机配置不进入Pages。源站为https://jimmyzzt.github.io/OotSS_Sand/。

Worker配置在wrangler.jsonc，账户和sand.zzt.si已核对。修改Worker后先npm run test:worker、npm run worker:check，再npm run worker:deploy；使用本机Wrangler登录，不写入凭证。普通网页更新只需Pages发布，无需重新部署Worker。

本轮验证包含16项Python测试、2项Worker代理测试、Ruff、Node语法检查、Wrangler dry-run，以及桌面区域网格、返回路线、编号/时间、主题尺寸与手动标注的浏览器核验。
