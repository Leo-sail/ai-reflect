---
description: Set or change the AI speaking style via choices (you decide; AI never auto-imitates) / 用选择题设置或修改 AI 沟通风格（你定，AI 不自动模仿）
argument-hint: "[optional style words; if omitted, present choices · 可留空，留空则给选择题]"
---

**English**

Manage the `communication_style` field in `~/.ai-reflect/synced/preferences.json`. **Prefer choices over a text box.**

- First show the current style setting.
- Then offer style presets as multiple choice (e.g. Concise and direct / Detailed and thorough / Casual and friendly / Keep current / Clear it). Only if the user picks "custom" do they type their own. If `$ARGUMENTS` is provided, treat it as the chosen custom style directly.
- Show the resulting setting as a draft and get a yes/no confirm before writing it back.

Explain once: this deliberately keeps style under the user's control rather than letting the AI auto-learn it from conversations, which avoids the two styles converging. In reflection the AI at most "suggests" a style; it only changes when the user agrees here. Tools read this live via the MCP `get_communication_style`.

---

**中文**

管理 `~/.ai-reflect/synced/preferences.json` 的 `communication_style` 字段。**尽量做选择题，别用文本框。**

- 先显示当前风格设置。
- 再把风格预设做成选择题（如 简洁直接 / 详细周到 / 随意像朋友 / 保持当前 / 清空）。只有用户选"自定义"才让他自己写。若带了 $ARGUMENTS，直接当作选定的自定义风格。
- 把结果当草稿展示，要一个是/否确认后再写回。

说明一次：这是有意把风格交给用户掌控、而非让 AI 从对话自动学——避免你我风格趋同。AI 在反思里至多"建议"某风格，只有用户在这里同意才会改。各工具通过 MCP 的 get_communication_style 实时读取。
