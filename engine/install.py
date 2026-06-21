"""一键安装 / 首次配置（模式A）。交互式：扫描整机 AI 工具→征授权→配置→装心跳。

设计要点（v4 审计修复）：
- adapters.json 写在 local/（不同步），路径用 expanduser，Python 用 sys.executable，绝不硬编码。
- state.json / device_id 写在 local/。synced/ 只放 profile/retros/preferences/changelog。
- git 仓只在 synced/ 初始化；安装真正的 pre-commit 钩子；引擎 commit 绝不 --no-verify。
"""
from __future__ import annotations
import os
import platform
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
from engine import paths  # noqa: E402

# 已知工具的探测模板（命中即提示用户授权；找不到的工具不接）
KNOWN_TOOLS = [
    {"id": "claude-code", "display": "Claude Code", "probe": "~/.claude",
     "transcript_globs": ["~/.claude/projects/**/*.jsonl"],
     "transcript_exclude": ["**/subagents/**", "**/workflows/**", "**/tool-results/**", "**/sessions/**"],
     "format": "claude-jsonl", "global_config": "~/.claude/CLAUDE.md",
     "skills_dir": "~/.claude/skills"},
    {"id": "codex", "display": "OpenAI Codex", "probe": "~/.codex",
     "transcript_globs": ["~/.codex/sessions/**/*.jsonl", "~/.codex/archived_sessions/**/*.jsonl"],
     "transcript_exclude": ["**/plugins/**", "**/.tmp/**"],
     "format": "codex-rollout-jsonl", "global_config": "~/.codex/AGENTS.md",
     "skills_dir": "~/.codex/skills"},
    {"id": "hermes", "display": "Nous Hermes", "probe": "~/.hermes",
     "format": "sqlite", "sqlite_db": "~/.hermes/state.db",
     "global_config": "~/.hermes/SOUL.md", "skills_dir": "~/.hermes/skills"},
]


def _ask(prompt, default=""):
    try:
        r = input(f"{prompt} " + (f"[{default}] " if default else "")).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        raise SystemExit(1)
    return r or default


def _yes(prompt, default="n"):
    return _ask(prompt + " (y/n)", default).lower().startswith("y")


def scan_tools():
    found = []
    for t in KNOWN_TOOLS:
        if Path(t["probe"]).expanduser().exists():
            found.append(t)
    return found


def main():
    print("=== ai-reflect 首次配置 ===")
    print(f"系统: {platform.system()}  Python: {sys.executable}\n")

    # 1. 扫描 + 授权
    found = scan_tools()
    if not found:
        print("未发现已知 AI 工具。可稍后手动编辑 adapters.json。")
    authorized = []
    for t in found:
        if _yes(f"发现 {t['display']}（{t['probe']}）。授权接入？", default="n"):
            t = dict(t)
            t["enabled"] = True
            authorized.append(t)

    # 2. 同步方式
    print("\n同步方式：1) git 私有远程  2) 云盘文件夹  3) 手动导出包")
    sync = {"1": "git_remote", "2": "cloud_folder", "3": "manual"}.get(_ask("选择", "3"), "manual")

    # 3. 回滚方式
    storage = "git" if _yes("\n用 git 做可回滚？（否则用本地备份文件夹）") else "backup"

    # 4. 每日时间（强校验）
    import re as _re
    while True:
        daily_time = _ask("\n每日反思运行时间 HH:MM", "03:17")
        if _re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", daily_time):
            break
        print("  格式应为 HH:MM（24 小时制），请重输。")

    # 5. 初始沟通风格（用户指定，可留空，随时可改）
    style = _ask("\n指定 AI 的沟通风格（可留空，之后用 /reflect-style 随时改）", "")

    # 6. 敏感词（客户名/项目名等无正则特征的，用于脱敏 extra_terms）
    raw_terms = _ask("\n额外敏感词（逗号分隔，写入画像/报告/导出时会被替换；可留空）", "")
    sensitive_terms = [s.strip() for s in raw_terms.split(",") if s.strip()]

    # --- 落地 scaffold ---
    for d in (paths.SYNCED, paths.LOCAL, paths.RETROS, paths.PROFILE_FACETS, paths.BACKUPS,
              paths.REPORTS, paths.REVIEW):
        d.mkdir(parents=True, exist_ok=True)
    if not paths.PROFILE.exists():
        shutil.copy2(ENGINE_DIR / "templates" / "profile.md", paths.PROFILE)

    prefs = paths.load_preferences()
    prefs.update({"sync_mode": sync, "storage_mode": storage,
                  "daily_time": daily_time, "communication_style": style,
                  "sensitive_terms": sensitive_terms})
    paths.save_json(paths.PREFERENCES, prefs)

    state = paths.load_state()
    state["onboarded"] = True
    state["device_id"] = state.get("device_id") or uuid.uuid4().hex[:12]
    paths.save_json(paths.STATE, state)
    paths.save_json(paths.ADAPTERS, {"tools": authorized})

    # git 仓只在 synced/，装 pre-commit 钩子
    if storage == "git":
        if not (paths.SYNCED / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=str(paths.SYNCED))
            subprocess.run(["git", "config", "user.name", "ai-reflect"], cwd=str(paths.SYNCED))
            subprocess.run(["git", "config", "user.email", "ai-reflect@localhost"], cwd=str(paths.SYNCED))
        hooks = paths.SYNCED / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ENGINE_DIR / "hooks" / "pre-commit", hooks / "pre-commit")
        # .engine_path 放 local/（绝不进同步仓，防泄露本机路径 + 防篡改致 RCE）
        (paths.LOCAL / ".engine_path").write_text(str(ENGINE_DIR), encoding="utf-8")
        try:
            os.chmod(hooks / "pre-commit", 0o755)
        except OSError:
            pass

    # 心跳：OS 级定时（不依赖任何 GUI）
    from engine import heartbeat
    entry = f'-m engine'  # 由调度器以 `python -m engine daily` 调用
    res = heartbeat.install_schedule(daily_time, ENGINE_DIR.parent / "engine")
    print(f"\n定时心跳: {res}")
    print("\n配置完成。授权工具:", [t["id"] for t in authorized])
    print("同步:", sync, " 回滚:", storage, " 时间:", daily_time, " 风格:", style or "(默认)")
    print("\n提示：首轮会从最近 14 天回看；之后增量。draft 模式下改动先进 review/ 待你合并。")


if __name__ == "__main__":
    main()
