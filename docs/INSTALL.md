# Install and operate / 安装与操作

**English** · [中文](#安装与操作)

> Prerequisites: Python 3.9+; git (optional, for rollback/sync); `pip install mcp` (optional, for cross-tool live read).

## One-step install

Best done inside Claude Code via `/reflect-setup`, which presents the setup as **multiple-choice questions** (no typing) and applies it after you confirm. Under the hood it is two no-prompt steps you can also run by hand:

```bash
git clone https://github.com/Leo-sail/ai-reflect.git ai-reflect
cd ai-reflect
python -m engine.install plan     # scans tools, writes a draft plan to local/setup-plan.json (asks nothing)
# review/edit setup-plan.json (the /reflect-setup command does this via a choice UI)
python -m engine.install apply    # reads the (edited) plan, lands config, installs the heartbeat
```

What it does:
1. `plan` scans local AI tools (Claude/Codex/Hermes...) and drafts the choices (authorize off by default).
2. You pick, via choices: which tools to authorize, sync method, rollback method, apply mode, daily time, speaking style, sensitive terms.
3. `apply` builds the `~/.ai-reflect/{synced,local}` scaffold, writes adapters.json (local paths).
4. With storage=git, inits git in `synced/` and installs the pre-commit hook.
5. Registers an OS-level daily schedule (Windows Task Scheduler or cron) calling `python -m engine daily`.

## As a Claude Code plugin

Place this repo in the Claude Code plugin directory (or via a marketplace) to get five commands: `/reflect` (run now), `/reflect-setup` (re-scan/configure), `/reflect-report` (report), `/reflect-style` (change style), `/reflect-update` (update itself), and the ai-reflect-memory MCP server.

## Daily use

- Automatic: runs daily on schedule, no intervention. After each run it shows a draft and lets you pick what to apply; nothing syncs until you confirm.
- Manual: `/reflect` runs a round now; `/reflect-report` makes a report (pick the period); `/reflect-style` changes the style (pick from presets).
- Each run also checks whether your other tools' extensions changed (added/updated/removed) and folds new capabilities into the routing hints, editing only its own marked block.

## Updating ai-reflect

```bash
python -m engine.update plan      # shows current version, what is new, additive-only defaults
python -m engine.update apply     # fast-forward pull + additive migration; never touches your data
```

Or run `/reflect-update`, which shows what is new and applies after you confirm. It only updates plugin code; your profile, retros, preferences, adapters, and watermarks are untouched; new preference defaults are filled in only where you never set a value. A non-fast-forward pull (you edited the code) is refused rather than forced.

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

推荐在 Claude Code 里用 `/reflect-setup`，它把配置做成**选择题**（不打字），你确认后才落地。底层是两步、都不提问，也可手动跑：

```bash
git clone https://github.com/Leo-sail/ai-reflect.git ai-reflect
cd ai-reflect
python -m engine.install plan     # 扫描工具，把草稿计划写到 local/setup-plan.json（全程不提问）
# 审阅/编辑 setup-plan.json（/reflect-setup 命令用选择 UI 帮你做这步）
python -m engine.install apply    # 读取（已编辑的）计划，落地配置、装心跳
```

做的事：
1. `plan` 扫描本机 AI 工具（Claude/Codex/Hermes…），把选项做成草稿（默认都不授权）。
2. 你用选择题挑：授权哪些工具、同步方式、回滚方式、应用模式、每日时间、沟通风格、敏感词。
3. `apply` 建好 `~/.ai-reflect/{synced,local}` 脚手架，写 adapters.json（本机路径）。
4. storage=git 时在 synced/ 初始化 git 并装 pre-commit 钩子。
5. 注册 OS 级每日定时（Windows Task Scheduler 或 cron）调 `python -m engine daily`。

## 作为 Claude Code 插件

把本仓库放进 Claude Code 插件目录（或通过插件市场），即可用 `/reflect`、`/reflect-setup`、
`/reflect-report`、`/reflect-style`、`/reflect-update` 五个命令，并启用 ai-reflect-memory MCP server。

## 日常使用

- 自动：每日定时跑，无需干预。每次跑完它给你看草稿、让你挑要应用哪些；确认前什么都不同步。
- 手动：`/reflect` 立刻跑一轮；`/reflect-report` 出报告（挑周期）；`/reflect-style` 改风格（从预设挑）。
- 每次跑还会查你其他工具的扩展能力有没有变化（新增/更新/移除），把新能力补进路由提示，只改自己那块带标记的内容。

## 升级 ai-reflect

```bash
python -m engine.update plan      # 显示当前版本、有哪些新功能、纯增量的新默认项
python -m engine.update apply     # 快进式 pull + 纯增量迁移；绝不动你的数据
```

或用 `/reflect-update`，它先告诉你有啥新功能、确认后才落地。它只更新插件代码；你的画像/复盘/偏好/适配器/水位线一概不动；新默认项仅在你没设过的地方才补。非快进（你改过代码）就拒绝、不强推。

## 故障处理

- **某工具读不到（适配器漂移）**：daily 会告警、且**不删任何配置**。运行 `/reflect-setup` 重新探测该工具路径/格式。
- **积压很多（长期没跑）**：每轮有 max_messages/max_days 上限，不会一轮爆炸；多跑几轮自动追平。
- **draft 稿堆积**：会自动背压并提示你切 write 或处理。
- **脱敏漏网已进 git**：`cd ~/.ai-reflect/synced && git filter-repo --replace-text <规则文件>`，再强推。
- **想暂停**：禁用 OS 定时任务即可；`python engine/uninstall.py` 彻底卸载（可保留 synced/）。
