# Connecting other tools / 接入其他工具

**English** · [中文](#接入其他工具-中文)

---

ai-reflect is tool-agnostic at its core: it keeps a single understanding of you that any tool can use. An "adapter" tells it **how to read a given tool's conversations** and **which file to write the understanding back to**. Known tools work out of the box; for tools that are not built in, add one entry using the template at the end.

## What an adapter is

One entry per tool, stored on this machine in `~/.ai-reflect/local/adapters.json` (this file is not synced, because it holds machine-local paths). An adapter tells the engine three things:

1. **How to read its conversations** — in what form and where they live: a pile of JSONL files, or a SQLite database.
2. **Where to write the understanding** — which file this tool reads as its long-term instructions (Claude reads CLAUDE.md, Codex reads AGENTS.md, Hermes reads SOUL.md).
3. **Where its extensions live** — used to improve skill-routing hints.

The engine only recognizes two forms of conversation storage:

- `claude-jsonl` / `codex-rollout-jsonl`: JSONL files with one message per line, matched by glob paths.
- `sqlite`: a SQLite database with a `messages` table (at least `role`, `content`, `timestamp` columns).

Most tools store conversations either as JSONL files or in SQLite, so these two cover the vast majority.

## Built in: Claude Code

Auto-detected at `~/.claude` during install.

- Read: `~/.claude/projects/**/*.jsonl` (sub-agent and workflow intermediate files are skipped automatically)
- Write back: `~/.claude/CLAUDE.md`
- Extensions dir: `~/.claude/skills`

No manual config; just approve the connection at install.

## Built in: OpenAI Codex

Auto-detected at `~/.codex` during install.

- Read: `~/.codex/sessions/**/*.jsonl` and `~/.codex/archived_sessions/**/*.jsonl`
- Write back: `~/.codex/AGENTS.md`
- Extensions dir: `~/.codex/skills`

> Note: Codex session file formats vary slightly across versions. The engine normalizes common fields (role / content / timestamp) automatically. If after some upgrade it reads empty, it warns "suspected format drift" in the log and will **not** delete config just because it read empty. Run `/reflect-setup` to re-detect.

## Built in: Hermes

Auto-detected at `~/.hermes` during install.

- Read: `~/.hermes/state.db` (SQLite, opened read-only, from the `messages` table)
- Write back: `~/.hermes/SOUL.md`
- Extensions dir: `~/.hermes/skills`

> Tip: if a directory junction points Hermes data elsewhere on this machine, the adapter follows the junction; nothing special is needed.

## Built in: VS Code family (Cursor / VS Code + Copilot / Trae / Windsurf)

These editors do not store chat as JSONL or in a `messages` table. They use `state.vscdb`, a SQLite **key-value table** (`ItemTable` / `cursorDiskKV`) holding JSON blobs. So ai-reflect has a third reader format, `vscdb-kv`, with one dialect per tool.

- **Cursor** — supported, Windows path confirmed. Reads `~/AppData/Roaming/Cursor/User/{workspaceStorage/*/state.vscdb, globalStorage/state.vscdb}`, keys `composerData:<id>` and `bubbleId:<composerId>:<bubbleId>` (`type` 1=user, 2=assistant). Writes back to `~/.cursor/rules/ai-reflect.mdc`. The database is opened **read-only and immutable**; ai-reflect never writes or deletes `state.vscdb` (deleting the global one can leave Cursor stuck on "Loading Chat"). On macOS the base is `~/Library/Application Support/Cursor/User`, on Linux `~/.config/Cursor/User`; `/reflect-setup` re-detects per machine.
- **VS Code + Copilot Chat** — framework ready, **disabled until verified on a machine that has it**. Chat bodies live in the filesystem (`workspaceStorage/<hash>/chatSessions/<uuid>.{json,jsonl}`, versioned), the index in `globalStorage/state.vscdb`. Needs a combined fs+db read; the adapter ships `enabled:false` with a note.
- **Trae** (ByteDance VS Code fork) — framework ready, **disabled until reverse-engineered**. Same `state.vscdb` family, but its exact key patterns are undocumented; they must be dumped on a machine that has Trae before the dialect mapping can be written. The Windows folder name (`Trae` vs `Trae CN`) is also unconfirmed.

> Why some are disabled rather than guessed: writing a dialect mapping with wrong keys would just read empty, which the engine treats as "suspected format drift" (it warns and deletes nothing), but that helps no one. Honest placeholders beat silent failure. To enable Copilot/Trae, on a machine that has them, dump `state.vscdb`'s `ItemTable` keys and tell us (or add the mapping in `engine/readers.py`).

## Works in Cowork

Cowork is Anthropic's Claude desktop agent mode, and it uses the **same plugin format** as Claude Code (`.claude-plugin/plugin.json` + skills + commands + a local MCP server). So ai-reflect installs and runs in Cowork with no code changes: its commands, the daily-reflect skill, and the read-only memory MCP server all work there. The local MCP server is allowed to run inside Cowork, so the all-local privacy model is preserved.

What ai-reflect does **not** do (yet): use Cowork's own conversations as a reflection data source. Cowork stores conversation content in a Chromium leveldb bound to your claude.ai account, not as local JSONL/SQLite, so it is out of reach of all three readers. This is left for when Anthropic exposes a local export.

## Connecting a tool that is not built in (e.g. Open Claw or any other)

Three steps.

### Step 1: Find where its conversations live

Poke around that tool's data directory (usually under your home directory, like `~/.toolname`). Check:

- Are there a bunch of `.jsonl` files? Open one and see if each line is a message with role / content / time fields.
- Or is there a `.db` / `.sqlite` file with a table of messages inside?

### Step 2: Add an adapter from the template

Edit `~/.ai-reflect/local/adapters.json` and add an entry to the `tools` array.

For a JSONL-style tool:

```json
{
  "id": "openclaw",
  "display": "Open Claw",
  "enabled": true,
  "format": "claude-jsonl",
  "transcript_globs": ["~/.openclaw/**/*.jsonl"],
  "transcript_exclude": ["**/cache/**", "**/tmp/**"],
  "global_config": "~/.openclaw/AGENTS.md",
  "skills_dir": "~/.openclaw/skills"
}
```

For a SQLite-style tool:

```json
{
  "id": "sometool",
  "display": "Some Tool",
  "enabled": true,
  "format": "sqlite",
  "sqlite_db": "~/.sometool/history.db",
  "global_config": "~/.sometool/INSTRUCTIONS.md",
  "skills_dir": "~/.sometool/skills"
}
```

Field reference:

| Field | Meaning |
|---|---|
| `id` | internal unique id, lowercase, e.g. `openclaw` |
| `display` | display name |
| `enabled` | must be `true` to be processed |
| `format` | `claude-jsonl` (JSONL files) or `sqlite` (database) |
| `transcript_globs` | required for JSONL: glob paths to conversation files, multiple allowed |
| `transcript_exclude` | optional: paths to skip (cache, temp files) |
| `sqlite_db` | required for SQLite: path to the database file |
| `global_config` | which file to write the understanding back to (this tool's long-term instruction file) |
| `skills_dir` | optional: its extensions directory, used for skill-routing hints |

Use `~` for your home directory in paths; the engine expands it and it works across Windows / Mac / Linux.

### Step 3: Verify it reads

```bash
python -m engine daily
```

Check the output. If it reports "tool processed N new messages," it reads fine. If it says "suspected format drift," the field names probably do not match: this tool may use different field names (e.g. `msg` instead of `content`). The engine already handles a set of common field names (role / message.role, content / text / message.content, timestamp / time / ts), covering mainstream tools. If yours uses very unusual names, tell me in an issue, or edit the normalization in `engine/readers.py`.

## Let tools read your profile live (optional, needs MCP)

The above is "write the understanding back to each tool's config file," read when the tool starts. If a tool supports MCP, it can also read your **latest** profile live, without waiting for the next start.

ai-reflect ships a read-only MCP service exposing four things: your profile, the speaking style you set, the list of project lessons, and a single lesson's detail.

In an MCP-capable tool, add this service to its MCP config:

```json
{
  "mcpServers": {
    "ai-reflect-memory": {
      "command": "python",
      "args": ["<ai-reflect install path>/engine/mcp_server.py"]
    }
  }
}
```

(When installed as a plugin in Claude Code, this service is already configured; no need to add it manually.)

The service is read-only and re-redacts before returning, never exposing your machine-local paths, backups, or reports.

## Security boundary (holds for connecting any tool)

- Tools/directories you have not approved are never touched.
- Files like `.env` and key files are excluded at the read stage; their contents never enter the profile.
- When writing back to a tool's config, auto content is wrapped in `<!-- ai-reflect:auto BEGIN/END -->` comments, easy to spot and delete; the body of others' extensions is never changed.
- Only the config files in your authorized list can be written; everything else is refused.

---
---

<a name="接入其他工具-中文"></a>
# 接入其他工具（中文）

[English](#connecting-other-tools--接入其他工具) · **中文**

ai-reflect 的核心是工具无关的：它对你的了解只存一份，谁都能用。一个"适配器"负责教它**怎么读某个工具的对话**、**把了解写回哪个文件**。装好已知的工具开箱即用；没内置的工具，照本文末尾的模板加一条即可。

## 适配器是什么

每个工具一条配置，存在本机的 `~/.ai-reflect/local/adapters.json`（这份不同步，因为里面是本机路径）。一条适配器告诉引擎三件事：

1. **怎么读它的对话** —— 对话以什么形式存在哪：一堆 JSONL 文件，还是一个 SQLite 数据库。
2. **把了解写回哪** —— 这个工具读哪个文件当"长期指令"（Claude 读 CLAUDE.md、Codex 读 AGENTS.md、Hermes 读 SOUL.md）。
3. **它的扩展能力放在哪** —— 用来优化技能调用的提示。

引擎只认两种对话存储形式：

- `claude-jsonl` / `codex-rollout-jsonl`：每行一条消息的 JSONL 文件，用通配路径去匹配。
- `sqlite`：一个 SQLite 数据库，里面有张 `messages` 表（至少有 role、content、timestamp 三列）。

绝大多数工具的对话，不是落成 JSONL 文件，就是塞进 SQLite，所以这两种基本够用。

## 已内置：Claude Code

安装时自动探测 `~/.claude`。

- 读：`~/.claude/projects/**/*.jsonl`（自动跳过子代理、工作流等中间文件）
- 写回：`~/.claude/CLAUDE.md`
- 能力目录：`~/.claude/skills`

无需手动配置，安装时同意接入即可。

## 已内置：OpenAI Codex

安装时自动探测 `~/.codex`。

- 读：`~/.codex/sessions/**/*.jsonl` 和 `~/.codex/archived_sessions/**/*.jsonl`
- 写回：`~/.codex/AGENTS.md`（Codex 读取的项目级指令文件）
- 能力目录：`~/.codex/skills`

> 注意：Codex 的会话文件格式各版本略有差异。引擎会自动归一常见字段（role / content / timestamp）。万一某次升级后它读出来是空的，会在日志里告警"疑似格式漂移"，并且**不会**因为读到空就误删配置——这时跑一次 `/reflect-setup` 重新探测即可。

## 已内置：Hermes

安装时自动探测 `~/.hermes`。

- 读：`~/.hermes/state.db`（SQLite，只读方式打开，从 `messages` 表取）
- 写回：`~/.hermes/SOUL.md`
- 能力目录：`~/.hermes/skills`

> 提示：本机若用目录联接（junction）把 Hermes 数据指到了别处，适配器跟着联接走即可，无需特殊处理。

## 已内置：VS Code 系（Cursor / VS Code+Copilot / Trae / Windsurf）

这些编辑器不把聊天存成 JSONL、也不用 `messages` 表，而是 `state.vscdb`——一个 SQLite 的**键值表**（`ItemTable` / `cursorDiskKV`），value 塞 JSON 大块。所以 ai-reflect 有第三种 reader：`vscdb-kv`，每个工具一个方言。

- **Cursor** —— 已支持，Windows 路径已确证。读 `~/AppData/Roaming/Cursor/User/{workspaceStorage/*/state.vscdb, globalStorage/state.vscdb}`，key 为 `composerData:<id>` 和 `bubbleId:<会话id>:<气泡id>`（`type` 1=用户、2=助手）。写回 `~/.cursor/rules/ai-reflect.mdc`。数据库**只读且 immutable 方式**打开，ai-reflect 绝不写/删 `state.vscdb`（删 global 那个会让 Cursor 卡在 "Loading Chat"）。macOS 根目录是 `~/Library/Application Support/Cursor/User`，Linux 是 `~/.config/Cursor/User`；`/reflect-setup` 会按本机重探。
- **VS Code + Copilot Chat** —— 框架就绪，**在装有它的机器上验证前默认关闭**。正文在文件系统（`workspaceStorage/<hash>/chatSessions/<uuid>.{json,jsonl}`，版本化），索引在 `globalStorage/state.vscdb`。需要 fs+db 联合读取；适配器先 `enabled:false` 并带说明。
- **Trae**（字节的 VS Code fork）—— 框架就绪，**逆向前默认关闭**。同属 `state.vscdb` 一系，但确切 key 模式无公开资料，必须在装了 Trae 的机器上 dump 出来才能写方言映射。Windows 目录名（`Trae` 还是 `Trae CN`）也待证实。

> 为什么有的先关着而不是盲写：用错的 key 写方言只会读到空，引擎会判"疑似格式漂移"（告警、不删任何东西），但那对谁都没用。老实占位胜过静默失效。要点亮 Copilot/Trae，在装有它们的机器上 dump `state.vscdb` 的 `ItemTable` key 告诉我（或自己在 `engine/readers.py` 里补 mapping）。

## 在 Cowork 里可用

Cowork 是 Anthropic Claude 桌面的 agent 模式，用的是和 Claude Code **一样的插件格式**（`.claude-plugin/plugin.json` + skills + commands + 本地 MCP server）。所以 ai-reflect 在 Cowork 里**零改动**就能装能跑：命令、daily-reflect 技能、只读记忆 MCP server 都好使。本地 MCP server 在 Cowork 里被允许运行，纯本地隐私模型不受影响。

ai-reflect **暂时不做**的：把 Cowork 自己的对话当反思数据源。Cowork 的对话内容存在绑定 claude.ai 账号的 Chromium leveldb 里，不是本地 JSONL/SQLite，三种 reader 都够不着。等 Anthropic 提供本地导出再说。

## 接入一个没内置的工具（比如 Open Claw 或任何其他）

分三步。

### 第一步：搞清它的对话存在哪

到那个工具的数据目录翻一翻（通常在你的用户主目录下，像 `~/.toolname` 这种）。看看：

- 有没有一堆 `.jsonl` 文件？随便打开一个，看每行是不是一条消息，有没有 role、content、时间这类字段。
- 还是有个 `.db` / `.sqlite` 文件？里面有没有一张存消息的表。

### 第二步：照着加一条适配器

编辑 `~/.ai-reflect/local/adapters.json`，在 `tools` 数组里加一条。

JSONL 类的工具：

```json
{
  "id": "openclaw",
  "display": "Open Claw",
  "enabled": true,
  "format": "claude-jsonl",
  "transcript_globs": ["~/.openclaw/**/*.jsonl"],
  "transcript_exclude": ["**/cache/**", "**/tmp/**"],
  "global_config": "~/.openclaw/AGENTS.md",
  "skills_dir": "~/.openclaw/skills"
}
```

SQLite 类的工具：

```json
{
  "id": "sometool",
  "display": "Some Tool",
  "enabled": true,
  "format": "sqlite",
  "sqlite_db": "~/.sometool/history.db",
  "global_config": "~/.sometool/INSTRUCTIONS.md",
  "skills_dir": "~/.sometool/skills"
}
```

字段说明：

| 字段 | 意思 |
|---|---|
| `id` | 内部唯一标识，小写英文，比如 `openclaw` |
| `display` | 显示名 |
| `enabled` | 设 `true` 才会被处理 |
| `format` | `claude-jsonl`（JSONL 文件）或 `sqlite`（数据库） |
| `transcript_globs` | JSONL 类必填：对话文件的通配路径，可多条 |
| `transcript_exclude` | 选填：要跳过的路径（缓存、临时文件等） |
| `sqlite_db` | SQLite 类必填：数据库文件路径 |
| `global_config` | 把了解写回哪个文件（这个工具读取的长期指令文件） |
| `skills_dir` | 选填：它的扩展能力目录，用于优化技能调用提示 |

路径里用 `~` 代表你的主目录即可，引擎会自动展开，跨 Windows / Mac / Linux 都认。

### 第三步：验证读得到

```bash
python -m engine daily
```

看输出。如果它报告"某工具处理了 N 条新消息"，说明读通了。如果报"疑似格式漂移"，多半是字段名对不上——这个工具的消息可能用了不一样的字段名（比如用 `msg` 而不是 `content`）。引擎已经兼容了一批常见字段名（role / message.role、content / text / message.content、timestamp / time / ts），覆盖了主流工具。万一你的工具用了很特别的字段名，可以在 issue 里告诉我，或自己改 `engine/readers.py` 里的归一逻辑。

## 让工具实时读你的档案（可选，需要 MCP）

上面是"把了解写回各工具的配置文件"，每次工具启动时读取。如果某个工具支持 MCP，还能让它**实时**读你的最新档案，不用等下次启动。

ai-reflect 自带一个只读的 MCP 服务，暴露四样东西：你的档案、你设的说话风格、项目经验列表、单条经验详情。

在支持 MCP 的工具里，把下面这个服务加进它的 MCP 配置：

```json
{
  "mcpServers": {
    "ai-reflect-memory": {
      "command": "python",
      "args": ["<ai-reflect 安装路径>/engine/mcp_server.py"]
    }
  }
}
```

（在 Claude Code 里作为插件安装时，这个服务已经自动配好，无需手动加。）

这个服务只读、且返回前会再过一遍脱敏，绝不会暴露你的本机路径、备份、报告这些本地文件。

## 安全边界（接入任何工具都成立）

- 没经你同意的工具/目录，引擎一概不碰。
- 像 `.env`、密钥文件这类，读取阶段就被排除，正文永远进不了档案。
- 写回各工具配置时，自动内容都包在 `<!-- ai-reflect:auto BEGIN/END -->` 注释里，一眼可辨、可手删；别人写的扩展能力正文绝不改动。
- 只有你授权清单里的那几个配置文件能被写入，别的文件一律拒绝。
