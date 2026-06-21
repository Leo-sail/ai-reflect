# Design audit record (v3 -> v4) / 设计审计记录

**English** · [中文](#设计审计记录v3--v4)

Before packaging, the system went through an adversarial audit (4 auditors attacking: feedback loop / security-privacy / cross-device consistency / survivability). Verdict: the v3 design **did not close the loop** (open-loop spinning + multiple positive-feedback contamination paths). v4 fixed each serious finding, recorded here for review.

| # | Audit finding (v3 hole) | v4 fix | Where |
|---|---|---|---|
| 1 | Layering was fake: watermark/local paths would sync via git, polluting cross-device "observation" | synced/local physically separated; watermark/paths/device_id only in local/, not in the sync repo | paths.py, install.py |
| 2 | Style imitation pollutes the single source of truth, positive-feedback convergence | style is now **user-specified, AI only suggests, never auto-changes**; reflection filters out "style echo" evidence | SKILL.md, reflect-style, mcp_server |
| 3 | Redaction was vaporware (script/hook did not exist) | deterministic redaction gate + real pre-commit hook + credential denylist + profile does not quote originals | sanitize.py, hooks/pre-commit, readers.py |
| 4 | Correction-rate was a bad signal (all causes read as "success") | denominator correction + churn marked N/A + engagement cross-check + ask the user on anomaly, no auto-reward | feedback.py, SKILL.md |
| 5 | Heartbeat parasitic on Claude Desktop, silent death | heartbeat moved to OS-level scheduling (schtasks/cron), self-heal when behind | heartbeat.py, install.py |
| 6 | Backlog uncapped, token explosion after days offline | per-round max_messages/max_days hard cap + batching, watermark only to batch end | readers.py(_window), __main__.py |
| 7 | Adapter silent failure treated as "user did not use it" -> destructive pruning | three states (data/empty/parse_error) + schema self-check; deletion needs K consecutive empty rounds; no delete on drift | readers.py, __main__.py, SKILL.md |
| 8 | draft with no merge -> pure spinning, pretending to learn | low-activity day only heartbeats; draft backpressure prompts switch to write; runs accumulate falsifiable success records | __main__.py, SKILL.md |

A second pre-publish security audit then found and fixed runtime vulnerabilities: redaction gate not wired into write paths, Zip-Slip, MCP path traversal, email ReDoS, future-timestamp poisoning, missing target whitelist, sentinel forgery, weak credential denylist, input validation. 18 regression tests now cover these.

## Against confirmation bias
Step 1 of the three-step reflection **forces a falsification question** ("which profile entry is most likely wrong"); the question stage does not read the full profile to avoid anchoring; source is three-valued and a user's agreement after AI prompting must not be upgraded to "user said."

## Residual limits still honestly kept
See README's "Before you use it" and SECURITY's "residual risks." This is not a perfect closed loop; it is a **verifiable, rollbackable, self-alarming** one.

---

<a name="设计审计记录v3--v4"></a>
# 设计审计记录（v3 → v4）（中文）

[English](#design-audit-record-v3---v4--设计审计记录) · **中文**

本系统在打包前经过一轮**对抗性审计**（4 名审计员分别攻击：反馈闭环/安全隐私/跨设备一致性/存活性）。
结论：v3 方案**不闭环**（开环空转 + 多处正反馈污染）。v4 针对每个严重发现做了修复，记录如下，便于复核。

| # | 审计发现（v3 的洞） | v4 修复 | 落在哪 |
|---|---|---|---|
| 1 | 分层是假的：水位线/本机路径会被 git 同步，污染跨设备"观察" | synced/local 物理分离；水位线/路径/device_id 只在 local/，不进同步仓 | paths.py, install.py |
| 2 | 风格模仿污染唯一真相源、正反馈趋同 | 风格改为**用户指定、AI 只建议不自改**；反思剔除"风格回声"证据 | SKILL.md, reflect-style, mcp_server |
| 3 | 脱敏是 vaporware（脚本/钩子不存在） | 确定性脱敏 gate + 真 pre-commit 钩子 + 凭证 denylist + 画像不抄原文 | sanitize.py, hooks/pre-commit, readers.py |
| 4 | 纠正率是坏信号（五种成因都读成"成功"） | 分母校正 + 流失标 N/A + 参与度交叉验证 + 异常主动问用户、不自动加码 | feedback.py, SKILL.md |
| 5 | 心跳单点寄生于 Claude Desktop，静默死 | 心跳改 OS 级调度（schtasks/cron），落后自愈 | heartbeat.py, install.py |
| 6 | 积压无上限，多日不开机一轮 token 爆炸 | 每轮 max_messages/max_days 硬上限 + 分批，水位线只推到本批末尾 | readers.py(_window), __main__.py |
| 7 | 适配器静默失效被当"用户没用"→破坏性瘦身 | 三态(data/empty/parse_error) + schema 自检；删除需连续 K 轮确认无活动；漂移时不删 | readers.py, __main__.py, SKILL.md |
| 8 | draft 无人合并→纯空转、假装学习 | 低活跃日只记心跳不空转；draft 背压提示切 write；runs 累积成功记录可证伪 | __main__.py, SKILL.md |

## 防确认偏误（治"AI 读自己输出"）
三步反思第 1 步**强制含一个证伪式问题**（"现有画像哪条最可能错"），提问阶段禁读 profile 全文防锚定；
来源三值化，AI 引导后的附和不得升级为"用户说的"。

## 仍诚实保留的局限
见 README 的"不做什么"与 SECURITY 的"残余风险"。这套不追求完美闭环，而是**可验证、可回滚、会自我报警**的闭环。
