# Security and Privacy / 安全与隐私

**English** · [中文](#安全与隐私)

## Layered defenses (deterministic, not relying on the LLM)

1. **Credential-file denylist**: files like `.env`, `auth.json`, key files (`.key/.pem/.pfx/.p12/.jks`), `.npmrc`, `.netrc`, `.pgpass`, `id_*`, and names containing secret/credential/token are excluded at the read stage; their contents never enter the pipeline.
2. **Redaction gate before any write**: any text written to disk or committed first passes the regex rules in `engine/sanitize.py` (AWS/GitHub/OpenAI/Anthropic/Google/Slack keys, private keys, JWT, Bearer, generic key=value, email, IPv4). On a hit it raises and blocks the write. This gate is wired into every write path, so backup mode does not run naked either.
3. **pre-commit hook backstop**: `engine/hooks/pre-commit` re-scans for secrets and leftover git conflict markers at commit time; the engine's own commits never add `--no-verify`. The engine also runs the scan in Python before committing, so the hook is a redundant second layer that cannot be bypassed via `core.hooksPath`.
4. **Whitelist writes to the profile**: the profile only stores abstract conclusions and never quotes conversations verbatim. This is what blocks pattern-less client/project names that regex cannot catch.
5. **MCP read-only and re-redacted**: the MCP server only exposes the synced profile/retros, re-redacts on return, and never exposes `local/`.
6. **Path confinement**: writes are refused outside the authorized target whitelist; imports reject zip-slip; MCP `get_retro` only serves exact whitelisted names.

## Honest residual risks

- Regex redaction cannot catch pattern-less sensitive terms (a particular client name). Mitigated by whitelist writes plus the user-entered `sensitive_terms`, but not 100% guaranteed.
- git history is permanent: if something slips through and was pushed to a remote, you must rewrite history with `git filter-repo`, not just delete the file.
- Cloud-drive sync hands `synced/` to the cloud provider. Privacy-sensitive users should choose private git remote or manual export.
- The MCP server uses local stdio and does not listen on a network port, but other local processes could in theory call it. Do not expose it on a shared/multi-user machine.
- The MCP launch command in `plugin.json` uses `python`, which relies on PATH resolution and is in theory subject to PATH hijacking (especially on Windows). Mitigation: use it in a trusted environment / fixed venv; heartbeat and install already pin the interpreter via `sys.executable`. This is a known residual risk.

## Passing security tests (`engine/selftest.py`)

Redaction catches keys/IP, `assert_clean` blocks, write-path gate wired in, sentinel-forgery blocked, Zip-Slip blocked, MCP path-traversal whitelisted, email regex has no ReDoS, future-timestamp poison dropped, backlog hard cap, churn marked N/A. 18 checks total; all must pass before release.

## User control

- Speaking style is user-specified and changeable anytime; the AI does not auto-imitate (prevents style convergence and treating "sounding like you" as data collection).
- Content auto-written into tool configs is wrapped in `<!-- ai-reflect:auto BEGIN/END -->`, easy to spot and delete.
- `apply_mode` defaults to draft: changes go to `review/` for your approval first; switch to write once you trust it.

---

<a name="安全与隐私"></a>
# 安全与隐私（中文）

[English](#security-and-privacy--安全与隐私) · **中文**

## 多道防线（确定性，不靠 LLM 自觉）

1. **凭证文件 denylist**：`.env / auth.json / .npmrc / .netrc / id_rsa / credentials / *.key / *.pem`
   在读取层就被 `engine/readers.py` 排除，正文永不进管道。
2. **写入前脱敏 gate**：任何落盘/提交文本先过 `engine/sanitize.py` 的正则规则（AWS/GitHub/OpenAI/
   Anthropic/Google/Slack key、私钥、JWT、Bearer、通用 key=赋值、email、IPv4）。
3. **pre-commit 钩子兜底**：`engine/hooks/pre-commit` 在 commit 时再扫一遍密钥 + git 冲突标记残留；
   引擎自身 commit **绝不加 `--no-verify`**，保证钩子始终生效。
4. **画像白名单写入**：profile 只写抽象结论，**禁止逐字摘录对话原文**（依据写成"某次需求澄清"）。
   这是为了挡住无正则特征的客户名/项目名等——正则挡不住的，靠"根本不抄原文"挡。
5. **MCP 只读且再脱敏**：mcp_server 只暴露 synced 的画像/复盘，且返回再过一遍脱敏；绝不暴露 local/。

## 诚实的残余风险

- 正则脱敏对**无特征的**敏感词（某个客户名）无能为力——靠白名单写入 + 用户自录敏感词表（preferences.sensitive_terms）缓解，但不能 100% 保证。
- git 历史是永久的：若脱敏漏网且已 push 到远程，需用 `git filter-repo` 重写历史并强推（见 INSTALL 故障处理）。
- 云盘同步会把 synced/ 交给云厂商——选 cloud_folder 即接受这一点；重隐私用户应选 manual 导出包或 git 私有远程。
- MCP server 默认本机 stdio，不监听网络端口；但本机其他进程理论上能调用——不要在共享/多人机器上开放。
- **plugin.json 的 MCP 启动命令用 `python`**：依赖 PATH 解析，理论上存在 PATH 劫持（尤其 Windows）。
  缓解：在受信环境/固定 venv 中使用；heartbeat 与 install 已用 `sys.executable` 钉死解释器。属已知残余风险。

## 已通过的安全测试（engine/selftest.py）

脱敏抓密钥/IP、assert_clean 阻断、写出口 gate 接入、哨兵伪造阻断、Zip-Slip 防护、MCP 路径穿越白名单、
email 正则无 ReDoS、未来时间戳投毒丢弃、积压硬上限、流失标 N/A。共 18 项，CI 前必须全绿。

## 用户掌控

- 沟通风格由用户指定、随时可改，AI 不自动模仿（防风格趋同，也防把"像你"当成隐私采集）。
- 自动写入各工具配置的内容都包在 `<!-- ai-reflect:auto BEGIN/END -->` 之间，一眼可辨、可手删。
- apply_mode 默认 draft：改动先进 review/ 待你过目，你信得过再切 write。
