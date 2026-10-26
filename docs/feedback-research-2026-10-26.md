# 问题反馈方案调研（2026-10-26）

本轮只调研，不上线表单、不创建问卷、不开放写入接口、不自动提交 GitHub Issue。

## 建议

若优先保证玩家无需注册、不离开地图、自动带上关卡上下文，本站建议采用**小型反馈弹窗 + 现有 Worker + D1**。第一版只收文字，不用 R2，也不做管理网页；维护者从 Cloudflare 控制台查看/导出，核实后才转成公开 Issue。规模是一个提交接口和一张表，不是完整工单系统。

若优先避免维护后端，可先选择**腾讯问卷**作为外链收集入口。Google 应使用 Forms（表单），而不是共享 Docs 文档。国内 B 站受众的外链访问、是否强制登录与手机填写步骤需要实测，不能仅凭平台功能宣传判断体验。

## 方案对比

| 方案 | 玩家操作 | 维护与限制 | 本站建议 |
| --- | --- | --- | --- |
| Google Forms | 跳转问卷；支持预填答案 | 需要创建、发布问卷；开启“仅回答一次”会要求 Google 登录，文件上传也会要求登录。将普通文本题与预填关卡信息组合，禁止公开答案汇总 | 面向能正常访问 Google 的受众才考虑 |
| 腾讯问卷 / 腾讯文档收集表 | 跳转现成收集页 | 无需自建后端；腾讯问卷“不要求登录”和收费的“允许匿名填答”并非同一设置。腾讯文档收集表的免登录、预填与上传权限尚未以真实表单验收，不承诺这些能力 | 维护最省事的备选；本轮优先核对了腾讯问卷官方资料 |
| 直接 GitHub Issue / Issue Forms | 跳转 GitHub 并以 GitHub 账号提交 | 可预填标题、正文、模板字段；天然支持讨论、去重、关闭。玩家需要账号，内容公开；URL 太长会失败，不宜把完整数据塞入链接 | 可作辅助入口，不作为面向所有玩家的唯一入口 |
| Worker 自动创建 Issue | 玩家可留在网站，不必持有 GitHub 账号 | 后端必须保存仅限目标仓库 Issues:write 的凭证；匿名公开写入易制造垃圾 Issue，需要验证、限流、去重与失败重试。反馈若有联系方式或截图会直接公开 | 不建议第一版自动直发；先收件审核后再转 Issue |
| Worker + D1 | 站内弹窗，无账号；自动携带上下文 | 需要新增提交接口、D1 绑定、校验和导出流程；可按关卡、类型、状态查询。D1 免费档含每天 500 万行读取、10 万行写入、总计 5 GB；Worker 请求另计且与现有页面/瓦片代理共享配额 | 体验与维护成本最均衡，推荐 |
| R2 | 通常作为截图上传的存储层 | R2 面向对象/文件；反馈的类型、处理状态和去重更适合 D1。R2 不替代校验接口，也不会自动提供工单列表 | 等确有截图附件需求再加，第一版无需开通 |

以上价格/限制只是官方当前额度，不是对本站实际费用的承诺；查询索引、现有 Worker 用量与是否付费会影响结果。

## 建议的第一版交互

- 在关卡预览图下方、第一条时间链接右侧放“反馈问题”，对应参考图红框位置；打开同页小弹窗。
- 类型：不匹配、重复、缺失、其他。只需填写类型和问题描述；可选填写正确关卡/时间/另一个重复点的链接，不强制提供邮箱或账号。
- 自动带入：物理地图、稳定 level_id、入口 marker_id 与坐标、区域名、所选分 P 的源编号和显示编号、CID/视频链接/开始时间、地图资源版本。若同一入口有多条访问，先让用户选择有问题的那一条。
- “缺失”不能只有关卡弹窗入口：缺少的标点无法被点击。应另设全局“反馈缺失关卡”，允许附视频时间或地图位置。不要强行把缺失归到当前已存在的关卡。
- 提交成功返回收件编号；失败保留所填文字、允许重试，不能仅显示一个通用错误后清空。
- 反馈仅形成待核记录，不直接修改已审核坐标、关卡身份或时间。

## 最小实现边界

POST /api/feedback 单独处理，原有 GET/HEAD 代理与地图请求不变。D1 一张反馈表即可：id、created_at、type、level_id、marker_id、map_id、context_json、description、status（待核/已确认/已修复/重复/无效）。加状态+创建时间索引及请求幂等键；同一次网络重试不重复收件。用户输入按纯文本显示，不拼接成 HTML。

服务端检查请求来源、类型枚举、上下文字段和正文长度；数据库参数绑定；限制提交频率并设置适当保留期。Turnstile 在打开反馈时才加载，必须由 Worker 调用 Siteverify 验证并检查 hostname/action；不能只放一个前端控件。密钥只放 Worker Secret。无需永久记录原始 IP、浏览历史、本机标注或编辑历史。

暂不上传图片；可以贴证据链接。如果后续加截图，再配置私有 R2、大小/格式校验和短期访问，不能直接把未审核附件公开。通知不是第一版必需项；若以后接邮件/Webhook，需单独配置目标。

## 实施顺序

1. 先定收件方案。如果选外部问卷，由维护者创建表单，提供发布链接并完成一次未登录手机验收，再接预填入口。
2. 如选 D1，配置数据库与 Turnstile；实现上述小弹窗、提交接口和导出，不增加后台管理应用。
3. 收到真实反馈后再判断是否需要自动通知、附件和经维护者确认的 Issue 同步。

## 官方依据

- [Google Forms 发布、预填与登录限制](https://support.google.com/docs/answer/2839588)
- [Google 表单文件上传的登录要求](https://support.google.com/docs/answer/15473134)
- [腾讯问卷填答限制：登录验证与匿名填答](https://cloud.tencent.com.cn/document/product/1304/135539)
- [腾讯问卷官方常见问题](https://cloud.tencent.cn/document/product/1304/139190)
- [腾讯问卷 HiFlow 集成前提：团队版与 Webhook](https://hiflow.tencent.com/document/applications/qq-wj/)
- [GitHub 预填 Issue 链接](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue)
- [GitHub Create an issue 的 Issues:write 权限](https://docs.github.com/en/rest/issues/issues#create-an-issue)
- [D1 产品概览](https://developers.cloudflare.com/d1/)
- [D1 计费与免费额度](https://developers.cloudflare.com/d1/platform/pricing/)
- [Worker 计费](https://developers.cloudflare.com/workers/platform/pricing/)
- [R2 对象存储适用范围](https://developers.cloudflare.com/r2/how-r2-works/)
- [Turnstile 服务端验证](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
