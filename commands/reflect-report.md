---
description: Produce a real usage report on demand / 按需生成真实使用报告（日报/周报/月报/年报或自定义范围与内容）
argument-hint: "[period or range, e.g. weekly / this-month / 2026 / custom · 周期或范围，如 周报 / 本月 / 2026 / 自定义]"
---

**English**

Produce a report **based entirely on real data**. Where data is missing, honestly mark "none / not recorded by this tool"; never fabricate.

Data sources (use the engine in Bash plus narrow queries over conversations/SQLite):
- Usage frequency / duration: each tool's session start-end timestamps and message counts.
- Which features were used: skills/agents/commands/tools invoked in the conversations.
- Token usage and cost: Hermes's sessions table has input/output_tokens and cost; for Claude/Codex take the usage field, mark when unavailable.
- Which projects: each tool's working directory / cwd.
- Problems found (yours and the AI's) and how each was solved: summarized from retros/.
- Mutual growth: read synced's git log/diff to see how the profile changed over this period.
- AI self-reflection: an honest review of its own performance in this period.

The range comes from `$ARGUMENTS` (default weekly). If the user specified custom content/format requirements, follow the user. Write the report to `~/.ai-reflect/local/reports/<date>-<period>.md` and return the highlights to the user. The report is also redacted, containing no keys or verbatim private data.

---

**中文**

生成一份**全部基于真实数据**的报告，缺数据就如实标"无/该工具未记录"，绝不编造。

数据来源（在 Bash 用 engine 辅助 + 窄查对话/SQLite 取）：
- 使用频率/时长：各工具会话起止时间戳与条数。
- 用了哪些功能：对话里调用过的 skill/agent/命令/工具。
- token 用量与成本：Hermes 的 sessions 表有 input/output_tokens 与成本；Claude/Codex 按 usage 字段取，取不到标注。
- 做了哪些项目：各工具工程目录/cwd。
- 发现的问题（你的+AI 的）及各自解法：汇总自 retros/。
- 双方成长：读 synced 的 git log/diff 看画像这段时间怎么变的。
- AI 自我反思：对这段表现的诚实复盘。

范围取自参数 $ARGUMENTS（默认周报）。若用户指定了自定义内容/格式要求，以用户要求为准。生成的报告写到 `~/.ai-reflect/local/reports/<日期>-<周期>.md` 并把要点回给用户。报告内容同样过脱敏，不含密钥/逐字隐私。
