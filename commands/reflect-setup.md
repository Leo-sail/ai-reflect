---
description: Re-scan AI tools and (re)configure / 重新扫描整机 AI 工具并（重新）配置接入、同步、回滚、时间、风格
---

**English**

Run setup as **multiple-choice questions, never a text box**. The engine discovers tools at runtime on *this* machine and classifies each by what it actually finds on disk; you never hardcode paths.

Steps:

1. In Bash run `python -m engine.install plan` (scans this machine, writes a draft plan to `~/.ai-reflect/local/setup-plan.json`; asks nothing). Each detected tool carries a `klass`:
   - `readable` — its conversations can be read locally (JSONL / unencrypted `messages` SQLite / Cursor-style vscdb). Gets full read + write-back.
   - `writeback` — conversations cannot be read locally (vendor-encrypted DB, leveldb, or server-side, e.g. Trae). ai-reflect can still write your profile into the tool's rules file, but only if it knows where that file is.
   - `unknown` — detected but storage shape unrecognized; default off, let the user decide.

2. Read the draft plan. Present choices with the AskUserQuestion tool (multiple choice):
   - Which detected tools to connect (multi-select; `readable` default on, `writeback`/`unknown` default off). For each tool show its `klass` and `reason` so the user understands why it is read+write vs write-back only.
   - Sync method: git remote / cloud folder / manual export.
   - Rollback: git / local backup.
   - Apply mode: draft (review before changes) / write (auto-commit with rollback).
   - Daily time: offer presets (e.g. 03:17 / 12:30 / 22:00) plus "custom".
   - Communication style: offer presets (concise / detailed / friendly / professional) plus "keep blank".

3. **Write-back target confirmation (only for `writeback` tools the user chose to connect).** If a tool has `target_unconfirmed: true`, ai-reflect does NOT guess a path. Ask the user to confirm where that tool reads its rules/instructions file (open the tool's Settings → Rules / AI rules to check). Offer choices built from real candidates plus "I'll paste the path" and "skip for now". Only when the user confirms a real location do you set that tool's `global_config` in the plan. Never write to an unconfirmed path.

4. **Encrypted-conversation decision (only for tools whose `klass` is `writeback` *because the DB is vendor-encrypted*, e.g. Trae).** ai-reflect never tries to decrypt a vendor-encrypted database — that is a hard compliance line. But don't silently settle for write-back-only; surface it and let the user decide, as a multiple-choice question:
   - **Write-back only (recommended default)** — we can't read past conversations, but we still write your evolving profile into the tool's rules file, so the tool gets smarter going forward.
   - **Help me read them with a local tool** — the user has, or is willing to use, a local utility that can export/decrypt that tool's own data *on their own machine* (e.g. the tool's official export, or a local DB they can unlock themselves). If chosen, ask them to point ai-reflect at the resulting plaintext export; ai-reflect reads that export read-only, never the encrypted original. **Be honest about the format limit**: ai-reflect can only parse an export it recognizes — a plaintext SQLite file with a `messages(role, content, timestamp, session_id)` table, or JSONL in a dialect it already knows. An arbitrary dump in some other shape won't be read; if that's all the user has, the engine will report `parse_error` and the tool stays write-back only. Don't promise it will work sight-unseen — let the engine verify the export on apply.
   - **Skip this tool entirely** — don't connect it at all.
   Make clear ai-reflect will not decrypt the vendor DB itself and will not ask for any account password; the only "read" path is a plaintext export the user produces with their own local tooling, and only if it matches a format the reader understands.

5. Write the user's picks back into setup-plan.json (same shape). For confirmed write-back targets, set `_adapter.global_config` and clear `target_unconfirmed`. For a user-provided plaintext export, set `_adapter.sqlite_db` (for a SQLite export) or the JSONL glob, plus the matching `_adapter.format` (`sqlite` / a known JSONL dialect). Do **not** pre-flip `klass` to `readable` yourself — leave it as detected; `apply` validates the export (plaintext SQLite magic + a real `messages` table, or parseable JSONL) and only then treats it as readable. If validation fails the tool stays write-back only and is reported as such.

6. In Bash run `python -m engine.install apply` to land config and install the heartbeat.

7. Report what was connected and how (read+write vs write-back only), what was skipped and why (e.g. "Trae: encrypted DB, read not possible; write-back target not confirmed"), plus sync/rollback/apply mode, daily time, style. Mention draft items go to `review/`.

Never ask the user to type free-form answers for setup. Use choices. Only "custom time", "custom style", or "paste the rules-file path" may invite typing.

---

**中文**

把配置做成**选择题，绝不用文本框**。引擎在**本机运行时自动发现**工具，并按它在磁盘上实际找到的东西给每个工具判级——绝不写死路径。

步骤：

1. 在 Bash 跑 `python -m engine.install plan`（扫描本机，把草稿计划写到 `~/.ai-reflect/local/setup-plan.json`；不提问）。每个探测到的工具带一个 `klass`：
   - `readable` —— 对话能在本地读（JSONL / 未加密的 `messages` SQLite / Cursor 式 vscdb）。读 + 写回都做。
   - `writeback` —— 对话**读不了**（厂商加密库 / leveldb / 服务端，如 Trae）。ai-reflect 仍能把你的画像写进该工具的规则文件，**前提是知道那个文件在哪**。
   - `unknown` —— 发现了但存储形态认不出；默认不勾，交用户决定。

2. 读取草稿计划。用 AskUserQuestion 把选项做成**选择题**：
   - 接入哪些工具（多选；`readable` 默认勾选，`writeback`/`unknown` 默认不勾）。每个工具显示它的 `klass` 和 `reason`，让用户明白为什么是"读+写"还是"仅写回"。
   - 同步方式：git 远程 / 云盘 / 手动导出。
   - 回滚方式：git / 本地备份。
   - 应用模式：draft（改动先审）/ write（自动提交，可回滚）。
   - 每日时间：给预设（如 03:17 / 12:30 / 22:00）+"自定义"。
   - 沟通风格：给预设（简洁 / 详细 / 朋友式 / 专业）+"留空"。

3. **写回目标指认（仅针对用户选择接入的 `writeback` 工具）。** 若某工具 `target_unconfirmed: true`，ai-reflect **绝不猜路径**。请用户确认该工具读哪个规则/指令文件（打开它的 设置 → 规则 / AI 规则 查看）。把真实候选 + "我来粘贴路径" + "暂时跳过" 做成选择题。**只有用户确认了真实位置**，才把该工具的 `global_config` 写进计划。绝不往未确认的路径写。

4. **加密对话的处置决策（仅针对因厂商加密库而被判为 `writeback` 的工具，如 Trae）。** ai-reflect 永不尝试解密厂商加密库——这是合规硬红线。但别默默接受"只写回"就完事，要把它摆出来交用户决定，做成选择题：
   - **仅写回（推荐默认）** —— 读不了过去的对话，但我们仍把你不断演化的画像写进该工具的规则文件，让它往后越来越懂你。
   - **用本机工具协同读取** —— 用户自己有、或愿意用一个**在自己机器上**能导出/解密该工具数据的本机工具（如该工具官方的导出功能、或用户自己能解锁的本地库）。选了就请用户把**导出后的明文文件路径**指给 ai-reflect（用户自己产出的 SQLite/JSONL）；ai-reflect 只读这个明文导出，**绝不碰加密原库**。**但要说清能不能读取取决于导出的格式**：ai-reflect 目前只认两种明文形态——① 含 `messages(role, content, timestamp, session_id)` 表的未加密 SQLite；② 它认得方言的 JSONL（当前为 Claude / Codex 系）。导出若不是这两种，仍只能写回（往后可加方言适配）。没有导出就退回"仅写回"。
   - **完全跳过这个工具** —— 不接入。
   要讲清楚:ai-reflect 不会自己去解密厂商库、也不会索要任何账号密码;唯一的"读"路径是用户用自己的本机工具产出的、且 ai-reflect 认得格式的明文导出。

5. 把用户的选择写回 setup-plan.json（结构不变）。对已确认的写回目标，设置 `_adapter.global_config` 并清掉 `target_unconfirmed`。对用户提供的明文导出：把 `_adapter.sqlite_db`（明文 SQLite）或 `_adapter.transcript_globs`（JSONL）设为该路径，并设 `_adapter.format`（`sqlite` 或 `claude-jsonl`/`codex-rollout-jsonl`）。**不要在计划里直接把 `klass` 改成 `readable`**——交给 `apply` 实测校验：只有当导出确为明文且 schema 被 reader 认得（SQLite 含 `messages(role,content,timestamp,session_id)` 表，或 JSONL 是认得的方言）时才翻 `readable`；认不得就保持 `writeback`，并把原因报给用户（导出格式 ai-reflect 读不了，仍只写回）。

6. 在 Bash 跑 `python -m engine.install apply` 落地配置、装心跳。

7. 报告：接入了什么、以什么方式（读+写 还是 仅写回）、跳过了什么及原因（如"Trae：库加密、读不了；写回目标未确认"），以及同步/回滚/应用模式、每日时间、风格。说明 draft 项进 `review/`。

把配置做成选择题，绝不让用户填空。只有"自定义时间/自定义风格/粘贴规则文件路径"才可以让用户打字。
