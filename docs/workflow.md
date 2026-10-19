# 给后续 Codex 的操作流程

1. 确认用户视频、BVID、分 P。运行 `python -m ootss import-map`（默认复用已固定版本，不自动拉取）。
2. `python -m ootss scan --video "inputs/xxx.mp4" --out runs/p4`。默认 8fps 黑屏扫描、15s 图册采样，一次低分辨率解码。scan.json 保存来源签名和元数据。先查看所有 sheet，防止忽略没有黑屏的连续关卡。
3. `python -m ootss match --run runs/p4` 生成机器候选，不写已确认事件。逐项看参考图，必要时用 `packet` 在短窗口密集抽帧。不要把主世界探索当独立谜题。
4. 关卡确认需检查静态布局、角色或机关位置关系。低 pHash 距离不足以确认。SIFT 内点也只是候选证据，重复地砖会误匹配。
5. 在进入前 10–30s 抽帧，将主世界地标和候选局部地图并排看。无法核验时写 `unverified` 或 `no_overworld_context`。不要凭同一检索候选自行循环证明。
6. 把判断写入独立 reviewed.json：关卡 ID、起止时间、时间误差范围、接近与转场时间、截图路径、理由、未知/冲突。一次访问一条记录，可多次访问同关卡。完成状态仅依据视频，无法确认则 unknown。
7. 可用 Luna 子 agent 对有界图册复核；明确要求返回 evidence/unknown/conflicts，不发送全视频，不调用外部模型 API。
8. `python -m ootss export --review results/p4/reviewed.json --out results/p4`，生成 JSON/CSV/Markdown 和静态 SVG/PNG 坐标图。地图跳转使用上游 `#level_id`。

全部时间为当前分 P 开始后的秒数。扫描时间为 fps 采样近似值；不能用平均 FPS 推算可变帧率视频的精确帧号。必要时从 FFmpeg 输出 PTS 复查。更换视频、采样参数或算法版本会失效扫描缓存；不要在同一个输出目录处理不同视频。机器重跑永远不写 reviewed.json。

原 starting_guide.md 已由上述工作流及实际结果说明替代：不实现 ASR 服务、Web 审核平台、复杂 Agent Adapter、自动训练、GitHub Issue 工程管理。GitHub CLI 凭证失效时继续本地提交。
