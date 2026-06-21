# Architecture / 架构

**English** · [中文](#架构)

## Layers: judgment vs determinism

```
Judgment layer (LLM, gets smarter as the model improves)
  skills/daily-reflect/SKILL.md   distill insights, evolve profile, suggest style, retros
Deterministic layer (Python, must be reliable, no hallucination)
  engine/readers.py    incremental per-tool reads + backlog hard cap + three states + schema self-check
  engine/sanitize.py   deterministic redaction gate (key/PII regex)
  engine/feedback.py   correction-rate signal (denominator correction / churn detection / engagement)
  engine/discover.py   detect other tools' capability changes each run (added/updated/removed, by fingerprint)
  engine/apply.py      git/backup rollbackable writes + sentinel blocks + pre-write hash
  engine/heartbeat.py  OS-level scheduled heartbeat + self-heal when behind
  engine/install.py    plan/apply (zero-input): scan -> draft plan -> (edited) -> apply
  engine/update.py     self-update: code-only, additive migration, never touches user data
  engine/mcp_server.py read-only cross-tool profile exposure
  engine/__main__.py   orchestration: produce run_context.json for the Skill to judge
Heartbeat (OS level, not parasitic on a GUI)
  Windows Task Scheduler / cron -> python -m engine daily
```

## Storage split (key to cross-device use)

```
~/.ai-reflect/
  synced/   travels with you, syncable: profile.md, profile/<domain>.md, retros/, preferences.json, changelog.md
  local/    bound to this machine, never synced: adapters.json (local paths), state.json (watermark/device_id),
            backups/, reports/, review/, .heartbeat, run_context.json
```

Watermarks, device_id, and local paths all live in `local/`, so machine A's progress and dead paths never pollute machine B.

## One run's data flow

1. OS timer -> `python -m engine daily`
2. engine reads each tool incrementally (window capped by max_messages/max_days), computes the correction signal, three-state judgment, writes `run_context.json`, advances watermarks
3. Low-activity day stops here (just a heartbeat, no token burn)
4. With data, the daily-reflect Skill reads run_context -> three-step reflection -> updates profile/retros -> optimizes each tool's config -> evolves and trims
5. Per apply_mode: draft writes `review/`, or write goes through the redaction gate + git/backup
6. Writes changelog, marks heartbeat success

## How the loop actually closes (vs the audit)

- **Observation** is not polluted: storage split landed, paths not hardcoded, style echo filtered out.
- **Application** can physically connect: draft backpressure prompts a switch to write; accumulating successful runs is falsifiable.
- **Verification** has a real signal: correction-rate with denominator correction + churn marked N/A + engagement cross-check + asking the user on anomaly, instead of auto-rewarding.

---

<a name="架构"></a>
# 架构（中文）

[English](#architecture--架构) · **中文**

## 分层：判断 vs 确定性

```
判断层（LLM，会随模型升级变聪明）
  skills/daily-reflect/SKILL.md   提炼洞见、画像演化、风格建议、复盘
确定性层（Python，必须可靠不幻觉）
  engine/readers.py    各工具增量读取 + 积压硬上限 + 三态 + schema 自检
  engine/sanitize.py   确定性脱敏 gate（密钥/PII 正则）
  engine/feedback.py   纠正率信号（分母校正/流失识别/参与度）
  engine/discover.py   每轮侦测其他工具能力变化（新增/更新/移除，按指纹比对）
  engine/apply.py      git/备份可回滚写入 + 哨兵区块 + 写前哈希
  engine/heartbeat.py  OS 级定时心跳 + 落后自愈
  engine/install.py    plan/apply（零输入）：扫描 → 草稿计划 →（编辑后）→ 落地
  engine/update.py     自升级：只换代码、纯增量迁移、绝不动用户数据
  engine/mcp_server.py 跨工具只读暴露画像
  engine/__main__.py   编排：产出 run_context.json 供 Skill 判断
心跳（OS 级，不寄生 GUI）
  Windows Task Scheduler / cron → python -m engine daily
```

## 存储分层（跨设备的关键）

```
~/.ai-reflect/
  synced/   跟你走、可同步：profile.md、profile/<领域>.md、retros/、preferences.json、changelog.md
  local/    绑本机、绝不同步：adapters.json(本机绝对路径)、state.json(水位线/device_id)、
            backups/、reports/、review/、.heartbeat、run_context.json
```

水位线、device_id、本机路径一律在 local/，所以 A 机的进度/死路径绝不会污染 B 机。

## 一轮数据流

1. OS 定时 → `python -m engine daily`
2. engine 增量读各工具（窗口上限 max_messages/max_days）、算纠正率信号、三态判断 → 写 `run_context.json`，推进水位线
3. 低活跃日到此为止（只记心跳，不烧 token）
4. 有数据则 daily-reflect Skill 读 run_context → 三步反思 → 更新画像/复盘 → 优化各工具配置 → 进化瘦身
5. 按 apply_mode：draft 写 review/ 或 write 经脱敏 gate + git/备份落盘
6. 写 changelog、mark 心跳成功

## 闭环如何真正闭合（针对审计）

- **观察**不被污染：分层落地、路径不硬编码、风格回声剔除。
- **应用**能物理接通：draft 背压会提示切 write；runs 累积成功记录可证伪。
- **验证**有真信号：纠正率分母校正 + 流失标 N/A + 参与度交叉验证 + 异常时主动问用户，而非自动加码。
