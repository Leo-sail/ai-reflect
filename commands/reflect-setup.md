---
description: Scan installed AI tools and configure via choices (no typing) / 扫描已装 AI 工具并用选择题完成配置（不让用户打字）
---

**English**

Goal: configure setup **without making the user type into a text box**. Use multiple-choice questions, show a draft, let them edit it, and only then apply.

Steps:
1. Run `python -m engine.install plan` in Bash. It scans the machine and writes a draft plan to `~/.ai-reflect/local/setup-plan.json` (detected tools + default choices). It asks nothing.
2. Read that draft and present it to the user through the tool's **question UI as multiple choice** (do NOT ask them to type free text). Prefer choices over fill-in for every field:
   - Which detected tools to authorize (multi-select; default none).
   - Sync method: git remote / cloud folder / manual export.
   - Rollback: git / local backup.
   - Apply mode: draft (recommended) / write.
   - Daily time: offer a few preset options (e.g. ~03:00 / noon / evening / custom).
   - Speaking style: offer presets (concise / detailed / casual / keep default), "custom" only if they want.
   - Sensitive terms: optional; only ask if they want to add any.
3. Write the user's selections back into `setup-plan.json`. Show the final plan as an editable draft and get a clear confirm (a yes/no choice, not typed).
4. After confirmation, run `python -m engine.install apply`. Report the result in a sentence.

Never connect a tool that was not authorized. If the user mentions a newly installed tool, re-run from step 1.

---

**中文**

目标：**不让用户在文本框打字**就完成配置。用选择题、给草稿、可编辑，确认后才落地。

步骤：
1. 在 Bash 跑 `python -m engine.install plan`。它扫描本机并把草稿计划写到 `~/.ai-reflect/local/setup-plan.json`（探测到的工具 + 默认选项），全程不提问。
2. 读这份草稿，用工具自带的**选择题 UI** 呈现给用户（**不要让他打字**）。每一项都尽量做成选择题而非填空：
   - 授权接入哪些已探测到的工具（多选；默认都不选）。
   - 同步方式：git 远程 / 云盘 / 手动导出。
   - 回滚方式：git / 本地备份。
   - 应用模式：草稿（推荐）/ 直接写入。
   - 每日时间：给几个预设（如 凌晨3点左右 / 中午 / 晚上 / 自定义）。
   - 沟通风格：给预设（简洁 / 详细 / 随意 / 保持默认），想自定义才填。
   - 敏感词：可选，用户想加再问。
3. 把用户的选择写回 `setup-plan.json`。把最终计划当作可编辑草稿展示，并要一个明确确认（用是/否选择题，不是打字）。
4. 确认后跑 `python -m engine.install apply`，用一句话报告结果。

绝不接入未经授权的工具。若用户提到新装了工具，从第 1 步重跑。
