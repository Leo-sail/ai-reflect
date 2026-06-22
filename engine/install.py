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

SETUP_PLAN = paths.LOCAL / "setup-plan.json"


def scan_tools():
    """运行时自动发现：在本机实测分类，不依赖写死路径。返回 detect() 的结果。"""
    from engine import detect
    return detect.detect()


def _plan_tool_entry(t: dict) -> dict:
    """把 detect() 的一条结果转成草稿计划里的工具项。
    - readable：默认建议授权（读+写回）。
    - writeback：默认建议授权但仅写回；target_unconfirmed 时写回目标待用户指认，apply 不会乱写。
    - unknown：默认不授权，标注待用户决定。
    """
    klass = t.get("klass", "unknown")
    return {
        "id": t["id"], "display": t["display"], "klass": klass,
        # 默认授权策略：能读的和能确定写回目标的默认勾选；unknown / 目标未确认的默认不勾
        "authorize": klass == "readable" or (klass == "writeback" and not t.get("target_unconfirmed")),
        "writeback_only": klass == "writeback",
        "target_unconfirmed": bool(t.get("target_unconfirmed")),
        "global_config": t.get("global_config"),
        "reason": t.get("reason", ""),
        "_adapter": t,
    }


def plan() -> dict:
    """扫描并产出草稿计划（不落地、不问问题）。命令层据此出选择题给用户编辑。"""
    found = scan_tools()
    prefs = paths.load_preferences()
    p = {
        "detected_tools": [_plan_tool_entry(t) for t in found],
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
    skipped = []
    for t in plan_obj.get("detected_tools", []):
        if not t.get("authorize"):
            continue
        adapter = t.get("_adapter") or {}
        klass = adapter.get("klass") or t.get("klass", "unknown")
        # 写回目标可由命令层在确认后写到草稿项顶层 global_config；顶层优先，其次 _adapter。
        effective_gc = t.get("global_config") or adapter.get("global_config")
        # 写回目标仍未确认的 writeback 工具：不落地（绝不往臆想路径写），记到 skipped 让命令层提示用户指认
        if klass == "writeback" and not effective_gc:
            skipped.append({"id": t["id"], "display": t["display"],
                            "reason": "写回目标未确认，待用户在 Trae/工具界面指认规则文件后再启用"})
            continue
        # 用户手贴的明文导出绕过了 detect 的实测分级，落地前必须自己再验一遍：
        # format=sqlite 的 readable 工具，复用 detect 的实测（明文魔数 + messages schema），
        # 验不过就降级——有写回目标退回 writeback，否则整条跳过。绝不凭文档承诺信任未验证的 readable。
        if klass == "readable" and adapter.get("format") == "sqlite":
            from engine import detect as _detect
            db = Path(adapter["sqlite_db"]).expanduser() if adapter.get("sqlite_db") else None
            plain = _detect._sqlite_is_plain(db) if db and db.exists() else None
            has_msgs = _detect._sqlite_has_messages_table(db) if plain is True else False
            if not (plain is True and has_msgs):
                why = ("导出文件不存在" if not (db and db.exists())
                       else "导出非明文 SQLite（魔数不符）" if plain is not True
                       else "导出缺 messages 表/列，schema 不符")
                if effective_gc:
                    klass = "writeback"  # 退回只写回：读不了导出，但还能写回画像
                    adapter = {**adapter, "reason": f"明文导出校验未过（{why}），退回只写回"}
                else:
                    skipped.append({"id": t["id"], "display": t["display"],
                                    "reason": f"明文导出校验未过（{why}），且无写回目标，跳过"})
                    continue
        a = {k: v for k, v in adapter.items() if not k.startswith("_")}
        a["enabled"] = True
        a["klass"] = klass
        if effective_gc:
            a["global_config"] = effective_gc  # 采纳用户确认/探测到的真实写回目标
        if klass == "writeback":
            # 只写回：明确标记不读对话，reader 不会尝试打开它的库
            a["read_disabled"] = True
            a["read_disabled_reason"] = adapter.get("reason", "厂商加密/不可本地读取，按合规只写回")
            # 清掉读取相关字段：降级自 readable 时会残留 sqlite_db/format 等，留着误导且不干净。
            # writeback 只认 global_config / writeback_dir / writeback_strategy，读取字段一律剥掉。
            for k in ("sqlite_db", "format", "vscdb_sources", "transcript_globs", "transcript_exclude"):
                a.pop(k, None)
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
               "apply_mode": apply_mode, "daily_time": dt, "style": style or "(默认)", "schedule": res,
               "skipped_unconfirmed": skipped,
               "readonly_writeback": [t["id"] for t in authorized if t.get("read_disabled")]}
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
