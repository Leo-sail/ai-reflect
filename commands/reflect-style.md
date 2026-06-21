---
description: Set or change the AI speaking style (you specify, changeable anytime; the AI never auto-imitates) / 设置或修改 AI 的沟通风格（由你指定，随时可改；AI 不会自动模仿你）
argument-hint: "[desired style, e.g. concise / fewer jargon / casual; empty = show current · 想要的风格描述，留空则查看当前]"
---

**English**

Read/modify the `communication_style` field in `~/.ai-reflect/synced/preferences.json`.

- If `$ARGUMENTS` is empty: show the current style setting.
- Otherwise: write `$ARGUMENTS` into `communication_style` (this is **explicitly user-specified**, effective immediately) and confirm.

Explain to the user: this deliberately puts the style under your control rather than letting the AI auto-imitate you from conversations, which avoids your styles converging on each other. In reflection the AI at most "suggests" a style, but it only changes when you agree here. Tools read this setting live via the MCP `get_communication_style`.

---

**中文**

读取/修改 `~/.ai-reflect/synced/preferences.json` 的 `communication_style` 字段。

- 若 $ARGUMENTS 为空：显示当前风格设置。
- 否则：把 $ARGUMENTS 写入 communication_style（这是用户**明确指定**的，直接生效），并确认。

说明给用户：这是有意把风格交给你掌控、而非让 AI 从对话里自动模仿你——避免你我语言风格互相模仿趋同。AI 在反思里至多"建议"某种风格，但只有你在这里同意才会改。各工具通过 MCP 的 get_communication_style 实时读取这个设置。
