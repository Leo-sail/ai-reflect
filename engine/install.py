"""安装 / 首次配置（模式A）—— 两段式、零文本输入。

设计（v4 + 交互改造）：
- 不再用 input() 让用户填空。拆成两步，都不阻塞输入：
    plan()  扫描整机 AI 工具，产出一份草稿计划 ~/.ai-reflect/local/setup-plan.json（含探测到的工具与默认值）。
    apply() 读取（可能已被用户/命令层编辑过的）setup-plan.json，落地配置、装心跳。
- 命令层(/reflect-setup)负责：调 plan → 用工具自带的“选择题 UI”让用户挑选/编辑 → 写回 setup-plan.json → 调 apply。
- 安全不变：adapters/state/device_id 写 local/ 不同步；路径 expanduser；Python 用 sys.executable；
  git 仓只在 synced/；装真实 pre-commit；.engine_path 放 local/。
"""
from __future__ import annotations
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
from engine import paths  # noqa: E402

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

SETUP_PLAN = paths.LOCAL / "setup-plan.json"


def scan_tools():
    return [t for t in KNOWN_TOOLS if Path(t["probe"]).expanduser().exists()]


def plan() -> dict:
    """扫描并产出草稿计划（不落地、不问问题）。命令层据此出选择题给用户编辑。"""
    found = scan_tools()
    prefs = paths.load_preferences()
    p = {
        "detected_tools": [
            {"id": t["id"], "display": t["display"], "probe": t["probe"],
             "authorize": False, "_adapter": t}      # authorize 默认 False，由用户在选择题里勾选
            for t in found
        ],
        "sync_mode": prefs.get("sync_mode", "manual"),         # git_remote | cloud_folder | manual
        "storage_mode": prefs.get("storage_mode", "git"),       # git | backup
        "apply_mode": prefs.get("apply_mode", "draft"),         # draft | write
        "daily_time": prefs.get("daily_time", "03:17"),
        "communication_style": prefs.get("communication_style", ""),
        "sensitive_terms": prefs.get("sensitive_terms", []),
        "_choices": {                                           # 供命令层做选择题用的可选项
            "sync_mode": ["git_remote", "cloud_folder", "manual"],
            "storage_mode": ["git", "backup"],
            "apply_mode": ["draft", "write"],
        },
        "_note": "命令层把 authorize / 各 *_mode / daily_time / style / sensitive_terms 改好后，调 apply。",
    }
    paths.LOCAL.mkdir(parents=True, exist_ok=True)
    paths.save_json(SETUP_PLAN, p)
    return p


def apply(plan_obj: dict | None = None) -> dict:
    """读取（已编辑的）setup-plan.json 落地配置、装心跳。零输入。"""
    if plan_obj is None:
        plan_obj = paths._read_json(SETUP_PLAN, None)
    if not plan_obj:
        raise SystemExit("缺少 setup-plan.json，请先运行 plan。")

    dt = plan_obj.get("daily_time", "03:17")
    if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", dt):
        raise SystemExit(f"daily_time 非法（应为 HH:MM）：{dt!r}")
    sync = plan_obj.get("sync_mode", "manual")
    storage = plan_obj.get("storage_mode", "git")
    apply_mode = plan_obj.get("apply_mode", "draft")
    style = plan_obj.get("communication_style", "")
    terms = plan_obj.get("sensitive_terms", []) or []

    authorized = []
    for t in plan_obj.get("detected_tools", []):
        if t.get("authorize"):
            a = dict(t.get("_adapter") or {})
            a["enabled"] = True
            authorized.append(a)

    for d in (paths.SYNCED, paths.LOCAL, paths.RETROS, paths.PROFILE_FACETS, paths.BACKUPS,
              paths.REPORTS, paths.REVIEW):
        d.mkdir(parents=True, exist_ok=True)
    if not paths.PROFILE.exists():
        shutil.copy2(ENGINE_DIR / "templates" / "profile.md", paths.PROFILE)

    prefs = paths.load_preferences()
    prefs.update({"sync_mode": sync, "storage_mode": storage, "apply_mode": apply_mode,
                  "daily_time": dt, "communication_style": style, "sensitive_terms": terms})
    paths.save_json(paths.PREFERENCES, prefs)

    state = paths.load_state()
    state["onboarded"] = True
    state["device_id"] = state.get("device_id") or uuid.uuid4().hex[:12]
    paths.save_json(paths.STATE, state)
    paths.save_json(paths.ADAPTERS, {"tools": authorized})

    if storage == "git":
        if not (paths.SYNCED / ".git").exists():
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(paths.SYNCED))
            subprocess.run(["git", "config", "user.name", "ai-reflect"], cwd=str(paths.SYNCED))
            subprocess.run(["git", "config", "user.email", "ai-reflect@localhost"], cwd=str(paths.SYNCED))
        hooks = paths.SYNCED / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ENGINE_DIR / "hooks" / "pre-commit", hooks / "pre-commit")
        (paths.LOCAL / ".engine_path").write_text(str(ENGINE_DIR), encoding="utf-8")
        try:
            os.chmod(hooks / "pre-commit", 0o755)
        except OSError:
            pass

    from engine import heartbeat
    res = heartbeat.install_schedule(dt, ENGINE_DIR.parent / "engine")
    summary = {"authorized": [t["id"] for t in authorized], "sync": sync, "storage": storage,
               "apply_mode": apply_mode, "daily_time": dt, "style": style or "(默认)", "schedule": res}
    print("配置完成 / setup done:", summary)
    return summary


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "plan"
    if cmd == "plan":
        import json
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        apply()
        return 0
    sys.stderr.write("用法: python -m engine.install [plan|apply]\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
