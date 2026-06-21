# Cross-device sync / 跨设备同步

**English** · [中文](#跨设备同步)

## Principle
**Knowledge travels with you, bindings are rebuilt per machine.** `synced/` syncs; `local/` (watermark/paths/device_id) never syncs.

## Three methods (chosen at install)

### 1. Private git remote (recommended for technical users)
```bash
cd ~/.ai-reflect/synced
git remote add origin <your private repo>
git push -u origin main        # the pre-commit hook scans for secrets before push; never --no-verify
```
New machine: install plugin -> at `python engine/install.py` choose git_remote and the same repo -> the installer clones `synced/` and rebuilds `local/` via step A.
Pros: full history, field-level merge. Note: make sure redaction passes before pushing.

### 2. Cloud-drive folder (recommended for non-technical users)
Put `~/.ai-reflect/synced/` in a OneDrive/iCloud/Dropbox folder (or symlink it). **Do not** put `.git` in the cloud drive (it corrupts); choose backup storage with this method.
New machine points at the same cloud folder. Pros: zero-effort auto-sync. Cons: weak conflict handling.

### 3. Manual export/import (recommended for privacy-sensitive users)
```bash
python engine/export.py   # produces ai-reflect-export.zip with no machine paths
# on the new machine:
python engine/import.py ai-reflect-export.zip
```
Pros: most private, fully manual, auditable. Cons: you move it by hand.

## Multi-device conflicts
- Profile entries carry `id+source+confidence+last_confirmed+device`; merge rule: **user_* always beats ai_inferred, same level takes the newer last_confirmed**, real conflicts marked "to verify next reflection," no blind merge.
- pre-commit scans for `<<<<<<<` conflict markers and blocks committing a dirty merge into the profile.
- changelog is sharded by device to avoid multi-machine write-write conflicts.

## Across operating systems (Win <-> Mac/Linux)
- All paths use expanduser, no drive letters; Python uses sys.executable.
- After switching platforms you **must** run `python engine/install.py` (step A) on the new machine to rebuild adapters.json; the old machine's paths must never be reused directly.

---

<a name="跨设备同步"></a>
# 跨设备同步（中文）

[English](#cross-device-sync--跨设备同步) · **中文**

## 原则
**知识跟你走，绑定按机器重建。** synced/ 同步，local/（水位线/路径/device_id）绝不同步。

## 三种方式（安装时选）

### 1. git 私有远程（推荐给技术用户）
```bash
cd ~/.ai-reflect/synced
git remote add origin <你的私有仓库>
git push -u origin main        # 推前 pre-commit 钩子会扫密钥；绝不 --no-verify
```
新设备：装插件 → `python engine/install.py` 时选 git_remote 并填同一仓库 → 安装器 clone synced/ 并跑模式A 重建 local/。
优点：完整历史、可字段级合并。注意：先确保脱敏过关再推。

### 2. 云盘文件夹（推荐给非技术用户）
把 `~/.ai-reflect/synced/` 放进 OneDrive/iCloud/Dropbox 同步目录（或软链过去）。
**不要**把 `.git` 放进云盘（会损坏）——云盘方案下 storage 选 backup 即可。
新设备装好后指向同一云盘目录。优点：零操作自动同步。缺点：冲突处理弱。

### 3. 手动导出/导入包（推荐给重隐私用户）
```bash
python engine/export.py   # 产出不含任何本机路径的便携包 ai-reflect-export.zip
# 新设备：
python engine/import.py ai-reflect-export.zip
```
优点：最私密、纯手动、可审包内容。缺点：要手动搬。

## 多设备冲突
- 画像条目带 `id+source+confidence+last_confirmed+device`；合并规则：**user_* 永远压过 ai_inferred，
  同级取 last_confirmed 新的**，真冲突标"待下轮反思核实"，不裸合并。
- pre-commit 扫 `<<<<<<<` 冲突标记，阻断把脏合并提交进画像。
- changelog 按 device 分片，避免多机写写冲突。

## 跨操作系统（Win ↔ Mac/Linux）
- 所有路径 expanduser，不含盘符；Python 用 sys.executable。
- 换平台后**必须**在新机跑 `python engine/install.py`（模式A）重建 adapters.json——旧机的路径绝不能直接用。
