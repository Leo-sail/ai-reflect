---
description: 立即跑一轮跨工具反思（读本轮物料、更新画像与复盘、按 apply_mode 应用）
---

先在 Bash 跑确定性管道生成本轮物料：`python -m engine daily`（它会读各工具新对话、加窗口、推水位线、产出 `~/.ai-reflect/local/run_context.json`）。

然后按 daily-reflect Skill 的方法论：读 run_context.json，三步反思（含强制证伪）更新画像与复盘，按各工具约定优化配置，进化瘦身，按 preferences.apply_mode 应用（draft 写 review/ 或 write 提交）。完成后用一两句话报告：各工具处理了多少新消息、提炼/进化了什么、改了哪些文件、有无适配器漂移告警。
