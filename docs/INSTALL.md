# Install and operate / 安装与操作

**English** · [中文](#安装与操作)

> Prerequisites: Python 3.9+; git (optional, for rollback/sync); `pip install mcp` (optional, for cross-tool live read).

## One-step install

```bash
git clone https://github.com/Leo-sail/ai-reflect.git ai-reflect
cd ai-reflect
python engine/install.py          # interactive: scan -> authorize -> sync -> rollback -> time -> style -> heartbeat
```

What the installer does:
1. Scans local AI tools (Claude/Codex/Hermes...) and asks one by one to connect (off by default).
2. Choose sync method, rollback method, daily time, initial speaking style, sensitive terms.
3. Builds the `~/.ai-reflect/{synced,local}` scaffold, writes adapters.json (local paths).
4. With storage=git, inits git in `synced/` and installs the pre-commit hook.
5. Registers an OS-level daily schedule (Windows Task Scheduler or cron) calling `python -m engine daily`.

## As a Claude Code plugin

Place this repo in the Claude Code plugin directory (or via a marketplace) to get four commands: `/reflect` (run now), `/reflect-setup` (re-scan), `/reflect-report` (report), `/reflect-style` (change style), and the ai-reflect-memory MCP server.

## Daily use

- Automatic: runs daily on schedule, no intervention. In `draft` mode changes go to `~/.ai-reflect/local/review/`, effective after you merge.
- Manual: `/reflect` runs a round now; `/reflect-report weekly` makes a report; `/reflect-style be concise` changes the style.

## Troubleshooting

- **A tool reads nothing (adapter drift)**: daily warns and deletes no config. Run `/reflect-setup` to re-detect that tool's path/format.
- **Large backlog (not run for a while)**: each round is capped by max_messages/max_days, so it never blows up in one run; it catches up over several rounds.
- **Drafts piling up**: it backpressures automatically and prompts you to switch to write or handle them.
- **Redaction slipped into git**: `cd ~/.ai-reflect/synced && git filter-repo --replace-text <rules file>`, then force push.
- **Pause it**: disable the OS scheduled task; `python engine/uninstall.py` fully uninstalls (can keep `synced/`).

---

<a name="安装与操作"></a>
# 安装与操作（中文）

[English](#install-and-operate--安装与操作) · **中文**

> 前置：Python 3.9+；git（可选，用于 git 回滚/同步）；`pip install mcp`（可选，用于跨工具 MCP 实时读）。

## 一键安装

```bash
git clone <your-private-repo> ai-reflect
cd ai-reflect
python engine/install.py          # 交互式：扫描→授权→同步→回滚→时间→风格→装心跳
```

安装器做的事：
1. 扫描本机 AI 工具（Claude/Codex/Hermes…），逐个问你是否授权接入。
2. 选同步方式、回滚方式、每日时间、初始沟通风格。
3. 建好 `~/.ai-reflect/{synced,local}` 脚手架，写 adapters.json（本机路径）。
4. storage=git 时在 synced/ 初始化 git 并装 pre-commit 钩子。
5. 注册 OS 级每日定时（Windows Task Scheduler 或 cron）调 `python -m engine daily`。

## 作为 Claude Code 插件

把本仓库放进 Claude Code 插件目录（或通过插件市场），即可用 `/reflect`、`/reflect-setup`、
`/reflect-report`、`/reflect-style` 四个命令，并启用 ai-reflect-memory MCP server。

## 日常使用

- 自动：每日定时跑，无需干预。`draft` 模式下改动进 `~/.ai-reflect/local/review/`，你合并后生效。
- 手动：`/reflect` 立刻跑一轮；`/reflect-report 周报` 出报告；`/reflect-style 简洁直接` 改风格。

## 故障处理

- **某工具读不到（适配器漂移）**：daily 会告警、且**不删任何配置**。运行 `/reflect-setup` 重新探测该工具路径/格式。
- **积压很多（长期没跑）**：每轮有 max_messages/max_days 上限，不会一轮爆炸；多跑几轮自动追平。
- **draft 稿堆积**：会自动背压并提示你切 write 或处理。
- **脱敏漏网已进 git**：`cd ~/.ai-reflect/synced && git filter-repo --replace-text <规则文件>`，再强推。
- **想暂停**：禁用 OS 定时任务即可；`python engine/uninstall.py` 彻底卸载（可保留 synced/）。
