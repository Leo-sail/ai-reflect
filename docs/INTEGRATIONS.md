# 接入其他工具

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
