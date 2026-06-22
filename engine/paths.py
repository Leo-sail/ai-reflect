"""ai-reflect paths & config — 确定性基础层。

关键设计（针对 v4 审计）：
- synced/ 与 local/ 严格分离：水位线、本机绝对路径、device_id 一律在 local/，绝不进同步仓。
- 所有路径用 Path.home() / expanduser()，绝不硬编码盘符或反斜杠，保证 Win/Mac/Linux 一致。
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("AI_REFLECT_HOME", str(Path.home() / ".ai-reflect")))
SYNCED = ROOT / "synced"
LOCAL = ROOT / "local"

# --- synced（跟用户走、可跨设备同步）---
PROFILE = SYNCED / "profile.md"
PROFILE_FACETS = SYNCED / "profile"          # profile/<领域>.md 分面画像
RETROS = SYNCED / "retros"
PREFERENCES = SYNCED / "preferences.json"     # apply_mode、风格、阈值等用户偏好
CHANGELOG = SYNCED / "changelog.md"

# --- local（绑本机、绝不同步）---
ADAPTERS = LOCAL / "adapters.json"            # 本机各工具的绝对路径，由 install 模式A 生成
STATE = LOCAL / "state.json"                  # 水位线、device_id、运行历史
BACKUPS = LOCAL / "backups"
REPORTS = LOCAL / "reports"
REVIEW = LOCAL / "review"                     # draft 模式的评审稿
HEARTBEAT = LOCAL / ".heartbeat"              # last_success_at 等存活信息

DEFAULT_PREFERENCES = {
    "apply_mode": "draft",                    # draft | write
    "storage_mode": "git",                    # git | backup（install 时确定）
    "sync_mode": "manual",                    # git_remote | cloud_folder | manual
    "communication_style": "",                # 用户指定的沟通风格，空=默认；随时可改，AI 不自动模仿
    "style_suggestions": True,                # 允许 AI 观察后"建议"风格（仍需用户点头才生效）
    "soft_max_lines": {"profile_md": 80, "tool_global_config": 90},
    "skeptical_memory": True,
    "evolve_not_append": True,
    "touch_third_party_skill_description": True,
    "daily_time": "03:17",                    # install 时由用户指定
    "max_messages_per_run": 2000,             # 积压硬上限（防 token 爆炸）
    "max_days_per_run": 3,
    "prune_requires_consecutive_empty": 2,    # 连续 K 轮确认无活动才允许删配置
}


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_preferences() -> dict:
    prefs = dict(DEFAULT_PREFERENCES)
    prefs.update(_read_json(PREFERENCES, {}))
    return prefs


def load_state() -> dict:
    return _read_json(STATE, {
        "onboarded": False,
        "device_id": None,
        "per_tool_watermark": {},
        "per_tool_empty_streak": {},
        "known_skills_by_tool": {},
        "known_agents_by_tool": {},
        "runs": [],
        "last_tool_scan": None,
    })


def load_adapters() -> dict:
    return _read_json(ADAPTERS, {"tools": []})


def save_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)  # 原子写，消除夜间并发竞态


def is_within(child: Path, parent: Path) -> bool:
    """child 解析后是否真落在 parent 内（防路径穿越/符号链接逃逸）。"""
    try:
        rc = child.resolve()
        rp = parent.resolve()
        return rc == rp or rp in rc.parents
    except OSError:
        return False


def allowed_config_targets() -> list[Path]:
    """write_sentinel_block 允许写入的目标白名单：当前 enabled 适配器的配置/技能目录 + synced。

    scan 策略的写回工具（如 Trae）文件名用户可改，写回前要重扫目录找哨兵复用真实文件，
    复用到的文件名≠global_config，故把其 writeback_dir 整目录纳入白名单（与 skills_dir 同理）。
    """
    targets = [SYNCED]
    for t in load_adapters().get("tools", []):
        if not t.get("enabled"):
            continue
        for key in ("global_config", "skills_dir", "writeback_dir"):
            v = t.get(key)
            if v:
                targets.append(Path(v).expanduser())
    return targets
