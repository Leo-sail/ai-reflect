# ai-reflect

> 一个**跨工具的反思与自进化引擎**。它观察你在各个 AI 编程工具（Claude Code、Codex、Hermes…）里的协同，
> 提炼出一份**带置信度的用户画像**，按每个工具自己的约定优化其行为配置与技能路由，
> 并用「你纠正 AI 的频率」来验证学习是否真的有效——**一个能自我验证、可回滚、会瘦身的闭环。**

**状态：v0.4.0 源码，未在任何机器上部署。** 审阅无误后再按下文安装。

---

## 它解决什么

每次换会话、换工具，AI 都得重新认识你。ai-reflect 让"对你的认识"成为一份跨工具共享、随你成长而进化的资产：

- **每日反思**：增量读各工具的新对话，三步反思提炼语言风格/习惯/技术水平/协同节奏。
- **项目复盘**：持续沉淀"解决了什么难题、走了哪些弯路、最终怎么解决"。
- **配置自优化**：按各工具约定（Claude→CLAUDE.md、Codex→AGENTS.md、Hermes→SOUL.md）优化行为与技能路由，让闲置能力被合理调用。
- **进化与瘦身**：随你能力成长收掉过时引导，删冗余、控 token。
- **按需报告**：使用频率/功能/时长/token 成本/项目/问题及解法/双方成长/AI 自我反思。
- **沟通风格**：由**你指定、随时可改**（见安全设计，这是有意为之，不让 AI 自动模仿你以免风格趋同）。

## 不做什么（诚实边界）

- 只覆盖**本地**工具对话，抓不到 claude.ai 网页版（数据在服务端）。
- 不替你做不可逆决定；自动改配置默认走 `draft`（先攒评审稿）。
- 不把对话原文逐字写进画像；不联网，除非你显式选 git 远程同步。

## 架构一句话

`Skill（判断）+ Python 引擎（确定性管道）+ OS 级定时（心跳）+ 文件/git（记忆与回滚）+ MCP server（跨工具实时读）`，打包成一个插件。

```
~/.ai-reflect/
  synced/   跟你走、可跨设备：profile.md、profile/<领域>.md、retros/、preferences.json、changelog.md
  local/    绑本机、不同步：adapters.json、state.json、backups/、reports/、.heartbeat
```

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 与 [docs/SECURITY.md](docs/SECURITY.md)。

---

## 安装（一键，审阅无误后再做）

```bash
# 1. 克隆到插件目录（或用 Claude Code 插件市场安装）
git clone <your-private-repo> ai-reflect

# 2. 一键安装：检测系统、扫描已装 AI 工具、征求授权、配置同步/回滚/时间/初始风格
python ai-reflect/engine/install.py
```

安装器会**交互式**带你走完：
1. 扫描本机 AI 工具，逐个问你是否授权接入。
2. 选同步方式（git 私有远程 / 云盘文件夹 / 手动导出包）。
3. 选回滚方式（git / 本地备份）。
4. 定每日运行时间。
5. 指定初始沟通风格（可留空）。
6. 安装 OS 级定时任务作主心跳（不依赖任何单一 GUI）。

卸载：`python ai-reflect/engine/uninstall.py`（移除定时任务与本机 `~/.ai-reflect/`，可选保留 synced/）。

详细操作见 [docs/INSTALL.md](docs/INSTALL.md)。

## 跨设备

新设备上：克隆插件 → `python engine/install.py` 选同样的同步源拉取 `synced/` → 安装器跑模式A 用**本机路径**重建 `local/`。知识跟你走，绑定按机器重建。详见 [docs/SYNC.md](docs/SYNC.md)。
