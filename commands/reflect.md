---
description: Run one reflection round, then show an editable draft for confirmation (choices, not typing) / 跑一轮反思，把草稿直接给用户看、可编辑，用选择题确认后再同步
---

**English**

Goal: after every run (including the first), **do not ask the user to type a reply or answer**. Show your draft directly, let them edit it, prefer multiple-choice over fill-in, and only sync to files after confirmation.

Steps:
1. Build this round's materials in Bash: `python -m engine daily` (reads new conversations, windows, advances watermarks, writes `~/.ai-reflect/local/run_context.json`). It never blocks on input.
2. Follow the daily-reflect Skill: read run_context.json, do the three-step reflection (with forced falsification), and produce a **draft** of all proposed changes (profile/retro updates, each tool's config edits). Write the draft to `~/.ai-reflect/local/review/<date>.md`.
3. **Show the draft to the user and offer choices, never a text box.** Use the tool's question UI:
   - Per change (or grouped): Apply / Edit / Skip.
   - For edits, present concrete options (e.g. wording A vs B, keep vs drop) as multiple choice; fall back to free text only if the user explicitly wants to write their own.
   - A final "Sync these now?" yes/no choice.
4. Only after confirmation, apply via the engine (`write` commits with backup + changelog; `draft` mode keeps them staged). Report what synced in a sentence.

If `preferences.apply_mode` is `draft`, never auto-write; the confirmation choice is what promotes a draft to applied. Respect backpressure: if many drafts are unmerged, surface that as one reminder instead of piling on.

---

**中文**

目标：每次跑完（**包含首次**）**都不要让用户在文本框输入修改或答案**。直接把你的草稿给用户看、可编辑、尽量做选择题，确认后才同步到各文件。

步骤：
1. 在 Bash 生成本轮物料：`python -m engine daily`（读新对话、加窗口、推水位线、产出 `~/.ai-reflect/local/run_context.json`），全程不卡输入。
2. 按 daily-reflect Skill：读 run_context.json，三步反思（含强制证伪），把所有拟改动（画像/复盘更新、各工具配置编辑）做成**草稿**，写到 `~/.ai-reflect/local/review/<日期>.md`。
3. **把草稿给用户看，并给选择题，绝不用文本框。** 用工具的选择 UI：
   - 每条（或分组）改动：应用 / 编辑 / 跳过。
   - 要编辑时，把具体方案做成选择题（如 措辞 A vs B、保留 vs 删除）；只有用户明确想自己写，才回退到填空。
   - 最后一个"现在同步这些吗？"的是/否选择。
4. 仅在确认后，用引擎落地（`write` 带备份+changelog 提交；`draft` 模式保持暂存）。用一句话报告同步了什么。

若 `preferences.apply_mode` 为 `draft`，绝不自动写入；那个确认选择就是把草稿提升为已应用的开关。遵守背压：若很多草稿没合并，合成一条提醒，别堆积。
