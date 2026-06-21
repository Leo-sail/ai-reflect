"""存活性（v4 审计修复：心跳与单一 GUI 解耦、积压自愈、静默死→被任一工具救活）。

主心跳用 OS 级调度（Windows Task Scheduler / cron），不寄生于任何单一工具。
每轮成功写 last_success_at；任何工具的轻量入口都可调 check_and_heal() 发现落后就触发补跑。
"""
from __future__ import annotations
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import paths


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
    """注册 OS 级每日任务。daily_time 形如 'HH:MM'。返回人类可读结果。"""
    hh, mm = daily_time.split(":")
    system = platform.system()
    py = sys.executable
    if system == "Windows":
        # schtasks：独立于 Claude/任何 GUI 存活
        cmd = ["schtasks", "/Create", "/SC", "DAILY", "/TN", "ai-reflect-daily",
               "/TR", f'"{py}" "{engine_entry}" daily', "/ST", f"{hh}:{mm}", "/F"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return f"Windows Task Scheduler: {'OK' if r.returncode == 0 else r.stderr}"
    # macOS / Linux：写一行 crontab
    cron_line = f"{int(mm)} {int(hh)} * * * {py} {engine_entry} daily\n"
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return "未找到 crontab，请手动配置定时（见 docs/INSTALL.md）"
    lines = [l for l in existing.splitlines() if "ai-reflect" not in l]
    lines.append("# ai-reflect-daily")
    lines.append(cron_line.strip())
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    return f"cron 已写入：{cron_line.strip()}"


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
