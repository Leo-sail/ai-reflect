---
description: Run one cross-tool reflection round now / 立即跑一轮跨工具反思（读本轮物料、更新画像与复盘、按 apply_mode 应用）
---

**English**

First run the deterministic pipeline in Bash to build this round's materials: `python -m engine daily` (it reads each tool's new conversations, applies the window, advances watermarks, and produces `~/.ai-reflect/local/run_context.json`).

Then follow the daily-reflect Skill methodology: read run_context.json, do the three-step reflection (with forced falsification) to update the profile and retros, optimize each tool's config per its convention, evolve and trim, and apply per `preferences.apply_mode` (draft writes `review/`, write commits). When done, report in a sentence or two: how many new messages each tool processed, what was distilled/evolved, which files changed, and whether there were any adapter-drift warnings.

---

**中文**

先在 Bash 跑确定性管道生成本轮物料：`python -m engine daily`（它会读各工具新对话、加窗口、推水位线、产出 `~/.ai-reflect/local/run_context.json`）。

然后按 daily-reflect Skill 的方法论：读 run_context.json，三步反思（含强制证伪）更新画像与复盘，按各工具约定优化配置，进化瘦身，按 preferences.apply_mode 应用（draft 写 review/ 或 write 提交）。完成后用一两句话报告：各工具处理了多少新消息、提炼/进化了什么、改了哪些文件、有无适配器漂移告警。
