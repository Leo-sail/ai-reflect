---
description: Update ai-reflect itself, safely (only code changes; never touches your local data) / 安全升级 ai-reflect 自身（只换代码，绝不动你本地数据）
---

**English**

Goal: update the plugin **without changing any of the user's existing local content**, and show what is new before applying.

Steps:
1. Run `python -m engine.update plan` in Bash. It checks the remote, and reports: current version, whether an update is available, the **new feature highlights**, and the **purely additive** preference defaults it would add (only for keys you never set).
2. Present this to the user as a review with multiple-choice confirmation (Update now / Not now), not a text box. Clearly restate the guarantee: it only updates plugin code; your profile, retros, preferences, adapters, and watermarks are untouched; new defaults are added only where you never set a value.
3. On confirm, run `python -m engine.update apply`. It does a fast-forward pull, adds only missing preference defaults, refreshes the pre-commit hook and `.engine_path` to point at the new code, and reports from/to versions and what defaults were added.

If the pull is not fast-forward (local code was modified), do not force it; tell the user and let them decide.

---

**中文**

目标：**不改用户任何已有本地内容**地升级插件，并在落地前展示有哪些更新。

步骤：
1. 在 Bash 跑 `python -m engine.update plan`。它检查远端并报告：当前版本、有无更新、**新增功能要点**、以及会做的**纯增量** preferences 默认项（仅针对你从没设过的键）。
2. 把结果作为评审展示给用户，用选择题确认（现在升级 / 暂不），不要文本框。明确复述保证：只换插件代码；你的画像/复盘/偏好/适配器/水位线一概不动；新默认项仅在你没设过的地方才补。
3. 确认后跑 `python -m engine.update apply`。它做快进式 pull、只补缺失的默认项、把 pre-commit 钩子与 `.engine_path` 刷新指向新代码，并报告版本从/到与补了哪些默认项。

若不是快进（本地代码被改过），不要强行覆盖；告诉用户、由他决定。
