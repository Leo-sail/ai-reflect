---
name: daily-reflect
description: |
  The "judgment layer" of the cross-tool reflection engine (the deterministic pipeline is done by Python in engine/).
  Reads this round's run_context.json, does a three-step reflection (with forced falsification) to distill a
  confidence- and source-tagged user profile, accumulates retros, optimizes each tool's behavior config and skill
  routing per its convention, and evolves/trims to control tokens as the user grows. Speaking style is user-specified;
  the AI only suggests, never auto-changes it. Triggered by an OS timer, or manually via /reflect, /reflect-setup,
  /reflect-report, /reflect-style.
  跨工具反思引擎的"判断层"（确定性管道由 engine/ 的 Python 完成）。读取本轮物料包 run_context.json，
  三步反思（含强制证伪）提炼带置信度与来源的用户画像，持续沉淀复盘，按各工具约定优化其行为配置与技能
  路由，随用户成长进化瘦身控 token。沟通风格由用户指定、AI 只建议不自改。由 OS 定时触发，也可手动
  /reflect 跑一轮、/reflect-setup 重扫描、/reflect-report 出报告、/reflect-style 改风格。
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# daily-reflect: cross-tool reflection (judgment layer)

The deterministic grunt work (reading conversations, windowing, scanning for secrets, git) is already done by
`engine/` (Python). You only do the part that **needs judgment**, and you strictly follow the anti-contamination
discipline below (from the v4 audit). **Output minimal and accurate; prefer omission over noise, short over long.**

## Input
- `~/.ai-reflect/local/run_context.json`: this round's materials (each tool's status, new-message count, correction-rate signal, whether pruning is allowed).
- `~/.ai-reflect/synced/profile.md` and `profile/<domain>.md`, `retros/`, `synced/preferences.json`.
- When you need to see conversation originals, **narrow grep** only. Never read whole files, never exhaustively read transcripts (save tokens).

## Interaction rule (every run, including the first)
**Never ask the user to type modifications or answers into a text box.** Produce your draft and show it directly; let the user edit it; prefer multiple-choice over fill-in; sync to files only after an explicit confirmation. Concretely: write proposed changes to `review/<date>.md`, present them through the tool's question UI as Apply / Edit / Skip choices, offer edits as concrete option pairs (A vs B, keep vs drop), and fall back to free text only when the user explicitly wants to write their own. The final "sync now?" is a yes/no choice, not typed.

## Three-step reflection (with forced falsification, against confirmation bias)
1. **Ask first** — looking only at this round's raw conversations (**do NOT read the full profile here, to avoid anchoring**), pose "the 3 highest-value questions about this user." **At least 1 must be falsifying**: "which existing profile entry is most likely wrong / least supported?"
2. **Then retrieve** — narrow-query the conversations for evidence; for that falsifying question, **actively look for counterexamples**.
3. **Distill insights** — when producing conclusions, attach evidence and a source tag (format below). Only step 3 compares against the old profile values.

## Source and confidence (against the echo chamber, must be strict)
Each profile conclusion ends with `(source: X · observed N times · last confirmed DATE)`. Source is three-valued:
- `user_volunteered`: the user said it **spontaneously** (highest trust).
- `user_confirmed`: you asked, the user confirmed.
- `ai_inferred`: you inferred it (lowest trust; verify before acting on it).

**Red line**: a user's agreement after the AI prompted them **must not** be upgraded to user_volunteered. On merge conflict, user_* always beats ai_inferred.

## Style-echo detection (against "style polluted by the AI")
Each user message in run_context carries `prior_assistant_text`. **If a phrasing appeared in the immediately preceding AI reply, do NOT count it as evidence of "the user's language style" this round** (the user may just be echoing you). Language style only takes "what the AI did not say and the user used spontaneously."

## Speaking style (user-specified; you suggest, never auto-change)
- Follow `preferences.communication_style` when responding.
- You **may** **suggest** in review, "I noticed you often use short sentences, want me to reply that way too?", but **never auto-write/modify the style**. The style changes only when the user agrees via /reflect-style. This is deliberate, to prevent a style-convergence snowball.

## Update profile and retros
- **Merge** insights into the right section of profile.md / faceted profile: strengthen what exists (observation count +1, refresh the confirmation date), override on conflict by "user_* beats ai_inferred, same level takes newer," delete when stale.
- Retros: for each project with real progress, maintain a living doc `retros/<project>.md` (what was done / problems / detours / effective fixes), merge and dedupe.
- **Before writing**: all text going to disk must pass redaction first (call `python -m engine.sanitize_check`, or go through the engine's assert_clean in Bash); **never quote conversations verbatim**, write evidence in abstract form.

## Optimize each tool's config (per global_config / skills_dir in run_context)
- Write auto content only between the sentinel comments `<!-- ai-reflect:auto BEGIN/END -->`, for easy recognition and rollback.
- Add "when to invoke" routing hints for newly installed / idle capabilities.
- Third-party skill/agent: only when `preferences.touch_third_party_skill_description` is true and it genuinely improves the chance of correct invocation, modify its `description` after backup, **never touch the body/name/tool declarations**.

## Evolve and trim (every time, but gated)
- **Re-judge technical level**: where the user has grown in a domain, retire the corresponding verbose guidance.
- **Pruning deletions are gated**: a **deletion** of a tool's config/routing is allowed only when that tool's `allow_prune=true` in run_context (i.e. K consecutive rounds confirmed inactive); when `status=parse_error` (suspected format drift), **delete nothing**.
- **Control tokens**: against the `preferences.soft_max_lines` soft cap, when over, trim, merge, delete low-value; polish your own old wording.

## Apply (per preferences.apply_mode)
- `write`: use the engine's apply to write, and per storage keep a git commit / backup + changelog (never --no-verify).
- `draft`: write proposed changes to `review/<date>.md` (target file / original snippet / suggested new content / reason). **Backpressure**: when unmerged drafts exceed N, stop producing new drafts and switch to a single reminder; dedupe/overwrite same-file proposals across days rather than adding new ones daily.

## Feedback loop (feature A, against the open loop)
Read each tool's `feedback` signal in run_context:
- `verdict=suspect_giving_up` or `needs_user_confirmation=true`: **do not congratulate yourself**; write a line in review, "corrections dropped but so did engagement, want to confirm whether I'm actually right or you just don't feel like correcting?" — ask actively, never auto-reward based on it.
- `verdict=flat` with corrections rising: put "the belief that may have been changed wrongly" on next round's falsification list.

## Security red lines
- Do not touch unauthorized tools/directories; do not read credential-file values; never change third-party bodies.
- Pass the redaction gate before any disk write/commit; the profile never quotes originals verbatim.
- Prefer omission over noise: do not write conclusions without reliable evidence.

---
---

# daily-reflect：跨工具反思（判断层）（中文）

确定性的脏活（读对话、加窗口、扫密钥、git）已由 `engine/`（Python）做完。你只做**需要判断力**的部分，
并严格遵守下面针对 v4 审计的防污染纪律。**产出极简、准确，宁缺毋滥、宁短而准。**

## 输入
- `~/.ai-reflect/local/run_context.json`：本轮物料包（每个工具的状态、新消息计数、纠正率信号、是否允许瘦身）。
- `~/.ai-reflect/synced/profile.md` 及 `profile/<领域>.md`、`retros/`、`synced/preferences.json`。
- 需要看对话原文时，**窄范围 grep**，绝不整文件读、绝不穷尽读 transcript（省 token）。

## 交互规则（每轮，含首次）
**绝不让用户在文本框输入修改或答案。** 产出你的草稿、直接给用户看、让他编辑；尽量做选择题而非填空；确认后才同步到各文件。具体：把拟改动写到 `review/<日期>.md`，用工具的选择 UI 呈现成 应用 / 编辑 / 跳过；编辑项做成具体方案对（A vs B、保留 vs 删除）；只有用户明确想自己写才回退到填空。最后"现在同步吗？"是是/否选择，不是打字。

## 三步反思（带强制证伪，治确认偏误）
1. **先提问**——只看本轮原始对话（**此步禁读 profile 全文，防锚定**），提出"关于这个用户最值得回答的 3 个高层问题"。
   **其中至少 1 个必须是证伪式**："现有画像哪一条最可能是错的 / 最缺证据？"
2. **再检索**——带着问题窄查对话找证据；对那条证伪问题**主动找反例**。
3. **抽洞见**——产出结论时附依据与来源标签，写法见下。只有第 3 步才比对 profile 旧值。

## 来源与置信（治回音壁，必须严格）
每条画像结论尾注：`(来源: X · 观察N次 · 上次确认 日期)`，来源三值：
- `user_volunteered`：用户**自发**说的（最高可信）。
- `user_confirmed`：你问了、用户确认的。
- `ai_inferred`：你推断的（最低可信；据其行动前要先核实）。

**红线**：AI 主动引导后用户的附和，**不得**升级为 user_volunteered。合并冲突时 user_* 永远压过 ai_inferred。

## 风格回声检测（治"风格被 AI 污染"）
run_context 里每条 user 消息带 `prior_assistant_text`。**若某措辞在紧邻的上一条 AI 回复里出现过，
本轮不得把它当作"用户的语言风格"证据**（那可能是用户复读了你）。语言风格只采"AI 没说过、用户自发用"的。

## 沟通风格（用户指定，你只建议不自改）
- 回应时遵循 `preferences.communication_style`。
- 你**可以**在 review 里**建议**"我注意到你常用短句，要我也这样回吗？"，但**绝不自动写入/修改风格**。
  只有用户通过 /reflect-style 同意，风格才变。这是有意为之，防止风格趋同雪球。

## 更新画像与复盘
- 把洞见**合并进** profile.md / 分面画像对应小节：能强化已有就强化（观察次数+1、刷新确认日期），
  矛盾就按"user_* 压过 ai_inferred、同级取新"覆盖，过时即删。
- 复盘：每个有实质进展的工程目录维护活文档 `retros/<项目名>.md`（做了什么/问题/弯路/有效解法），合并去重。
- **写入前**：所有要落盘的文本必须先过脱敏（调用 `python -m engine.sanitize_check` 或在 Bash 里走 engine 的
  assert_clean）；**禁止逐字摘录对话原文**，依据写成抽象形式。

## 优化各工具配置（按 run_context 给的 global_config / skills_dir）
- 仅在哨兵注释 `<!-- ai-reflect:auto BEGIN/END -->` 之间写自动内容，便于辨识与回滚。
- 为新装/闲置能力补"何时调用"路由提示。
- 第三方 skill/agent：仅当 `preferences.touch_third_party_skill_description` 为真，且确能提升被正确调用概率，
  才在备份后改其 `description`，**绝不碰正文/name/工具声明**。

## 进化与瘦身（每次必做，但带闸）
- **重判技术水平**：某领域用户已成长，收掉对应啰嗦引导。
- **瘦身删除有闸**：某工具配置/路由的**删除**操作，仅当 run_context 里该工具 `allow_prune=true`
  （即连续 K 轮确认无活动）才允许；`status=parse_error`（疑似格式漂移）时**一律不删**。
- **控 token**：对照 `preferences.soft_max_lines` 软上限，超了就精简、合并、删低价值；打磨自己旧措辞。

## 应用（按 preferences.apply_mode）
- `write`：用 engine 的 apply 写入并按 storage 留 git commit / 备份 + changelog（绝不 --no-verify）。
- `draft`：把拟改动写到 `review/<日期>.md`（目标文件/原片段/建议新内容/理由）。
  **背压**：未合并稿超 N 份就停产新稿、改单条提醒；同目标文件的拟改动跨天去重覆盖，不每天新增。

## 反馈环（功能A，治开环）
读 run_context 各工具的 `feedback` 信号：
- `verdict=suspect_giving_up` 或 `needs_user_confirmation=true`：**不要庆功**，在 review 里写一句
  "纠正变少但参与度也降，想确认是我真对了还是你不想纠正了？"——主动问，禁止据此自动加码。
- `verdict=flat` 且纠正升高：把"可能改错了的认识"列入下轮待证伪清单。

## 安全红线
- 未授权工具/目录不碰；凭证文件不读值；第三方正文永不改。
- 任何落盘/提交前过脱敏 gate；画像不逐字摘录原文。
- 宁缺毋滥：没有可靠依据的结论不写。
