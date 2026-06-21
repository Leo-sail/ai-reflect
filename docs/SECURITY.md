# 安全与隐私

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
