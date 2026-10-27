# 问题反馈与管理

地图使用 Worker + D1 收集反馈，不会自动改变已经审核的关卡数据。

## 玩家入口

- 点击关卡，在视频跳转链接同一行右侧点击「问题反馈」，自动附带当前地图、关卡、真实入口坐标、视频分 P／时间和地图版本；同一关有多个视频时间时可选择对应记录。
- 设置 →「问题反馈」可报告缺失关卡或其他全局问题；请在描述中补充区域、分 P 和时间点。
- 类型包括不匹配、重复、缺失、其他。描述必填，证据网页链接选填；当前版本不上传截图文件。
- 完成人机验证后提交，成功时显示收件编号。网络失败会保留填写内容；相同提交重试不会生成两条反馈。
- 不上传浏览器本机的区域改名、标注或完成进度。关闭或刷新页面前请自行保存尚未提交的内容。

## 管理面板

设置 → 数据与来源展开后的第一行 →「问题反馈管理面板」，或直接访问 https://sand.zzt.si/feedback-admin 。

Cloudflare Access 应用覆盖 `sand.zzt.si/feedback-admin` 及其子路径。Allow 邮箱仅限 `mocking.jimmy@gmail.com`、`2601848284@qq.com`，建议启用 One-time PIN 邮箱验证码，不使用 Everyone 或 Bypass 策略。Worker 另外验证 Access JWT 的 RS256 签名、issuer、AUD、有效期及这两个邮箱；未配置时拒绝访问。workers.dev 域名不提供管理访问，GitHub Pages 不包含管理页面。

面板支持按状态、类型、地图及关卡／描述搜索，50 条分页；可以定位到地图关卡、跳转攻略、填写管理员备注及将状态改为待核对／已确认／已修复／重复／无效。修改包含版本检查，避免两人覆盖同一条记录。导出当前筛选结果最多 1000 条 CSV，并转义电子表格公式。第一版保留所有反馈，不提供删除。

静态地图和全部精度瓦片现由 Workers Static Assets 直接提供，仅反馈／管理调用脚本。额度耗尽不影响静态地图，反馈仍可能暂时不可用。部署方式见 [托管说明](hosting.md)。

## 部署与维护

已创建专用 D1 `ootss-sand-feedback`，绑定 `FEEDBACK_DB`；迁移在 `deployment/migrations/`。Turnstile 组件仅允许 `sand.zzt.si` 和 `jimmyzzt.github.io`，后端强制验证 action=feedback 及请求网站域名。密钥只保存在 Worker Secrets，不写进页面或仓库。

```powershell
# 仅检查资源；不会打印凭证或 Turnstile secret。
node deployment/setup-feedback.mjs
# 缺少资源时创建，写入公开配置和 Worker Secrets；已有资源不重复创建。
node deployment/setup-feedback.mjs --apply
npx wrangler d1 migrations apply FEEDBACK_DB --remote
npm run test:worker
npm run worker:check
npm run worker:deploy
```

Access team domain 和应用 AUD 在 `wrangler.jsonc`；两者是公开验证配置，不是密钥。调整 Access 白名单时，同时维护 `deployment/feedback-auth.js` 中的邮箱列表。浏览器重新认证走 Access 登录页；不要用不验证签名的身份请求头代替 JWT。

公共提交仅允许地图正式域名和 GitHub Pages origin，最多 16 KiB JSON；有蜜罐、Turnstile、每来源每 15 分钟最多 5 条限制及幂等编号。限流只保存加盐的短期 IP 摘要，不保存原始 IP，过期记录在后续提交时清理。反馈为纯文本呈现，所有数据库参数绑定；私有接口和响应不缓存。验证脚本仅在打开反馈窗口时加载，普通地图浏览不加载 Turnstile。

测试采用内存 SQLite、生成的测试 RSA 密钥和模拟 Siteverify 响应，覆盖公开提交、重复重试、限流、来源校验、Access 签名／白名单、管理分页／搜索／CSV／并发修改；生产接口不提供测试凭证或认证旁路。

官方参考：[Access JWT 验证](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)、[Turnstile 服务端验证](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)。

## 上线验收（2026-10-26）

31 项 Node 测试、27 项 Python 测试及 Ruff 检查通过，GitHub Pages 自动发布成功。线上 Turnstile 自动验证和真实 D1 收件已验证，坐标及新分 P 号正确；管理页与管理 API 未登录跳转 Access，workers.dev 直接拒绝管理访问。站主已通过真实邮箱验证码登录并确认看到了管理面板。手机 375px 视口验证反馈入口与视频链接同行，设置按钮使用淡红底色及深红悬停／键盘焦点样式。
