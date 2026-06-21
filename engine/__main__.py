"""引擎入口（确定性编排层）。被 OS 定时任务调用：python -m engine daily

它负责确定性的"管道"：读取、窗口化、脱敏、写入、提交、记状态、自愈。
而"判断"（提炼什么洞见、画像怎么演化、风格建议）由 daily-reflect Skill（LLM）完成——
本入口生成一份「本轮物料包」(run_context.json) 供 Skill 读取，Skill 产出后回调 apply。

这样切分的原因（v4 设计）：扫密钥、读 SQLite、加窗口、git 操作必须确定可靠、不能幻觉；
而"什么算成长、风格稳不稳"需要判断力，交给会随模型升级变聪明的 Skill。
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone

from . import paths, readers, feedback, heartbeat


def _build_run_context() -> dict:
    prefs = paths.load_preferences()
    state = paths.load_state()
    adapters = paths.load_adapters()
    wm = state.get("per_tool_watermark", {})
    empty_streak = state.get("per_tool_empty_streak", {})
    prev_feedback = {f.get("tool"): f for f in (state.get("runs", [{}])[-1].get("feedback", []) if state.get("runs") else [])}

    bundle = {"generated_at": datetime.now(timezone.utc).isoformat(), "tools": [], "prefs": prefs}
    for tool in adapters.get("tools", []):
        if not tool.get("enabled"):
            continue
        tid = tool["id"]
        res = readers.read_tool(tool, wm.get(tid, 0.0),
                                prefs["max_messages_per_run"], prefs["max_days_per_run"])
        user_msgs = [m for m in res.messages if m.role == "user"]
        sig = feedback.compute(tid, user_msgs, res.new_watermark > wm.get(tid, 0.0),
                               prev_feedback.get(tid, {}))
        # 三态处理：解析异常绝不当"无活动"，跳过瘦身、不推水位线
        if res.status == "parse_error":
            empty_streak[tid] = 0
            bundle["tools"].append({"id": tid, "status": "parse_error", "note": res.note,
                                    "allow_prune": False})
            continue
        if res.status == "empty":
            empty_streak[tid] = empty_streak.get(tid, 0) + 1
        else:
            empty_streak[tid] = 0
        allow_prune = empty_streak.get(tid, 0) >= prefs["prune_requires_consecutive_empty"]
        bundle["tools"].append({
            "id": tid, "status": res.status,
            "new_watermark": res.new_watermark, "backlog_remaining": res.backlog_remaining,
            "message_count": len(res.messages), "user_message_count": len(user_msgs),
            "feedback": sig.__dict__, "allow_prune": allow_prune,
            "global_config": tool.get("global_config"), "skills_dir": tool.get("skills_dir"),
            # 只把"摘要级"物料给 Skill；正文留在磁盘按需窄查，避免 token 爆炸
        })
    # 暂存物料供 Skill 读取
    paths.save_json(paths.LOCAL / "run_context.json", bundle)
    # 推进水位线与 empty streak（确定性部分先落，Skill 的画像写入随后由 apply 落）
    for t in bundle["tools"]:
        if t["status"] == "data":
            wm[t["id"]] = t["new_watermark"]
    state["per_tool_watermark"] = wm
    state["per_tool_empty_streak"] = empty_streak
    paths.save_json(paths.STATE, state)
    return bundle


def daily() -> int:
    state = paths.load_state()
    if not state.get("onboarded"):
        sys.stderr.write("尚未 onboard，请先运行 install.py 完成首次扫描配置。\n")
        return 2
    bundle = _build_run_context()
    active = [t for t in bundle["tools"] if t["status"] == "data"]
    drifting = [t["id"] for t in bundle["tools"] if t["status"] == "parse_error"]
    # 低活跃日：无任何新数据则只记心跳、不烧 token 让 Skill 空转
    if not active:
        heartbeat.mark_success()
        note = f"低活跃：无新对话。" + (f" 适配器疑似漂移: {drifting}" if drifting else "")
        sys.stdout.write(note + "\n")
        return 0
    # 有数据：留下信号，由 Skill（/daily-reflect）读取 run_context.json 完成判断与写入
    heartbeat.mark_success()
    sys.stdout.write(
        f"本轮物料已就绪：{sum(t['user_message_count'] for t in active)} 条新用户消息，"
        f"待 daily-reflect Skill 提炼。漂移告警: {drifting or '无'}\n")
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "daily"
    if cmd == "daily":
        return daily()
    if cmd == "heal":
        db = heartbeat.days_behind()
        if db is not None and db >= 2:
            return daily()
        return 0
    sys.stderr.write(f"未知命令: {cmd}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
