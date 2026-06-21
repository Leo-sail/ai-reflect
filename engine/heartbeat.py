"""存活性（v4 审计修复：心跳与单一 GUI 解耦、积压自愈、静默死→被任一工具救活）。

主心跳用 OS 级调度（Windows Task Scheduler / cron），不寄生于任何单一工具。
每轮成功写 last_success_at；任何工具的轻量入口都可调 check_and_heal() 发现落后就触发补跑。
"""
from __future__ import annotations
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import paths

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _valid_time(daily_time: str) -> tuple[int, int]:
    m = _TIME_RE.match(daily_time.strip())
    if not m:
        raise ValueError(f"非法时间格式（应为 HH:MM）：{daily_time!r}")
    return int(m.group(1)), int(m.group(2))


def mark_success() -> None:
    paths.HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    paths.HEARTBEAT.write_text(
        datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def last_success() -> datetime | None:
    try:
        return datetime.fromisoformat(paths.HEARTBEAT.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def days_behind() -> float | None:
    ls = last_success()
    if ls is None:
        return None
    return (datetime.now(timezone.utc) - ls).total_seconds() / 86400


def install_schedule(daily_time: str, engine_entry: Path) -> str:
    """注册 OS 级每日任务。daily_time 形如 'HH:MM'（强校验）。返回人类可读结果。"""
    h, mm = _valid_time(daily_time)
    system = platform.system()
    py = sys.executable
    if system == "Windows":
        cmd = ["schtasks", "/Create", "/SC", "DAILY", "/TN", "ai-reflect-daily",
               "/TR", f'"{py}" "{engine_entry}" daily', "/ST", f"{h:02d}:{mm:02d}", "/F"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return f"Windows Task Scheduler: {'OK' if r.returncode == 0 else r.stderr}"
    cron_line = f"{mm} {h} * * * {py} {engine_entry} daily"
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return "未找到 crontab，请手动配置定时（见 docs/INSTALL.md）"
    lines = [l for l in existing.splitlines() if "ai-reflect" not in l]
    lines.append("# ai-reflect-daily")
    lines.append(cron_line)
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    return f"cron 已写入：{cron_line}"


def remove_schedule() -> str:
    system = platform.system()
    if system == "Windows":
        r = subprocess.run(["schtasks", "/Delete", "/TN", "ai-reflect-daily", "/F"],
                           capture_output=True, text=True)
        return "Windows 任务已删除" if r.returncode == 0 else r.stderr
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    lines = [l for l in existing.splitlines() if "ai-reflect" not in l]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    return "cron 行已移除"
