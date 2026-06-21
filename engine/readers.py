"""各工具对话读取适配器（v4 审计修复：积压硬上限、三态、凭证 denylist、schema 自检）。

三态返回 ReadResult.status：
  "data"        正常读到消息
  "empty"       确认无新消息（真实信号，可参与"无活动"判断）
  "parse_error" 匹配到源但解析异常/0 条可解析（疑似格式漂移）——绝不当成"用户没用"，
                调用方据此跳过瘦身删除、不推进水位线、告警。
"""
from __future__ import annotations
import glob
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

# 凭证文件 denylist：在读取层就排除，正文永不进入管道（模式匹配，从严）
_CRED_NAME_RE = re.compile(
    r"(?i)(^\.env|(^|[._-])(secret|credential|token|password|passwd)|^id_[a-z]+$|"
    r"^\.npmrc$|^\.netrc$|^\.pgpass$|kubeconfig)")
CRED_SUFFIXES = {".key", ".pem", ".pfx", ".p12", ".jks"}

# DoS 防护上限
MAX_FILE_BYTES = 50_000_000
MAX_LINE_BYTES = 1_000_000
MAX_TOTAL_LINES = 500_000


@dataclass
class Msg:
    role: str
    time: float          # unix 秒
    text: str
    session_id: str = ""
    prior_assistant_text: str = ""  # 紧邻的上一条 assistant 文本，供"风格回声"检测


@dataclass
class ReadResult:
    status: str                      # data | empty | parse_error
    messages: list = field(default_factory=list)
    new_watermark: float = 0.0
    backlog_remaining: bool = False
    note: str = ""


def _is_cred(path: Path) -> bool:
    return bool(_CRED_NAME_RE.search(path.name)) or path.suffix.lower() in CRED_SUFFIXES or path.name == "auth.json"


def _expand(p: str) -> str:
    return str(Path(p).expanduser())


def read_tool(adapter: dict, watermark: float, max_messages: int, max_days: int) -> ReadResult:
    fmt = adapter.get("format")
    cutoff_floor = watermark
    try:
        if fmt in ("claude-jsonl", "codex-rollout-jsonl"):
            return _read_jsonl(adapter, cutoff_floor, max_messages, max_days)
        if fmt == "sqlite":
            return _read_sqlite(adapter, cutoff_floor, max_messages, max_days)
        return ReadResult(status="parse_error", note=f"未知 format: {fmt}")
    except Exception as e:  # noqa: BLE001 — 任何异常都收敛成 parse_error，绝不静默当空
        return ReadResult(status="parse_error", note=f"{type(e).__name__}: {e}")


def _collect_jsonl_rows(adapter):
    excl = adapter.get("transcript_exclude", [])
    rows, total = [], 0
    for pat in adapter.get("transcript_globs", []):
        for fp in glob.glob(_expand(pat), recursive=True):
            path = Path(fp)
            if _is_cred(path):
                continue
            if any(Path(fp).match(_expand(e)) for e in excl):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue  # 跳过超大文件，避免内存耗尽 DoS
            except OSError:
                continue
            with path.open(encoding="utf-8", errors="ignore") as fh:
                for line in fh:  # 流式逐行，不全量读入
                    line = line.strip()
                    if not line or len(line) > MAX_LINE_BYTES:
                        continue
                    rows.append(line)
                    total += 1
                    if total >= MAX_TOTAL_LINES:
                        return rows
    return rows


def _read_jsonl(adapter, watermark, max_messages, max_days):
    raw = _collect_jsonl_rows(adapter)
    if not raw:
        return ReadResult(status="empty", new_watermark=watermark)
    msgs, parsed_any, ts_any = [], False, False
    for line in raw:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        role, text, ts, sid = _normalize(obj, adapter.get("format"))
        if role is None:
            continue
        parsed_any = True
        if ts is not None:
            ts_any = True
            if ts > watermark:
                msgs.append(Msg(role=role, time=ts, text=text or "", session_id=sid or ""))
    if not parsed_any:
        return ReadResult(status="parse_error", note="匹配到文件但 0 条可解析，疑似格式漂移")
    if not ts_any:
        return ReadResult(status="parse_error", note="可解析但无有效时间戳，疑似戳字段漂移")
    return _window(msgs, watermark, max_messages, max_days)


def _normalize(obj, fmt):
    """把不同工具的行归一成 (role, text, ts, session_id)。容错：字段缺失返回 role=None 跳过。
    兼容三种常见形态：顶层 role/content；message.role/message.content；payload.role/payload.content
    （如 Codex rollout：每行 {timestamp, type, payload:{type:'message', role, content:[{type:'input_text',text}]}}）。"""
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    # Codex rollout：只取 payload.type == 'message' 的行，跳过 session_meta/event_msg/turn_context 等
    if payload and payload.get("type") and payload.get("type") != "message":
        return None, None, None, ""
    role = obj.get("role") or msg.get("role") or payload.get("role")
    text = (obj.get("content") or obj.get("text") or msg.get("content") or payload.get("content"))
    if isinstance(text, list):  # content 可能是 block 数组（claude / codex）
        parts = []
        for b in text:
            if isinstance(b, dict):
                parts.append(b.get("text") or b.get("input_text") or b.get("output_text") or "")
            elif isinstance(b, str):
                parts.append(b)
        text = " ".join(p for p in parts if p)
    ts = obj.get("timestamp") or obj.get("time") or obj.get("ts") or payload.get("timestamp")
    if isinstance(ts, str):
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = None
    sid = obj.get("session_id") or obj.get("sessionId") or payload.get("id") or ""
    return role, (text if isinstance(text, str) else None), ts, sid


def _read_sqlite(adapter, watermark, max_messages, max_days):
    db = _expand(adapter["sqlite_db"])
    if not Path(db).exists():
        return ReadResult(status="parse_error", note=f"数据库不存在: {db}")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        # schema 自检：关键列必须在
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if not {"role", "content", "timestamp"}.issubset(cols):
            return ReadResult(status="parse_error", note="messages 表缺关键列，疑似 schema 漂移")
        cur.execute(
            "SELECT role, content, timestamp, session_id FROM messages "
            "WHERE timestamp > ? ORDER BY timestamp", (watermark,))
        rows = cur.fetchall()
    finally:
        con.close()
    if not rows:
        return ReadResult(status="empty", new_watermark=watermark)
    msgs = []
    for r in rows:
        if r[2] is None:  # NULL 时间戳
            continue
        try:
            msgs.append(Msg(role=r[0], time=float(r[2]), text=r[1] or "", session_id=r[3] or ""))
        except (TypeError, ValueError):
            continue
    if not msgs:
        return ReadResult(status="parse_error", note="messages 行无有效时间戳，疑似 schema/戳漂移")
    return _window(msgs, watermark, max_messages, max_days)


def _window(msgs, watermark, max_messages, max_days):
    """积压硬上限：单轮最多 max_messages 条或 max_days 天，水位线只推到本批末尾。
    时间戳投毒防护：丢弃未来戳（> now+宽限），水位线单调且不晚于当前时刻。"""
    now = time.time()
    skew = 300  # 容忍 5 分钟时钟偏差
    msgs = [m for m in msgs if m.time <= now + skew]  # 丢弃未来戳，防投毒永久跳过
    msgs.sort(key=lambda m: m.time)
    if not msgs:
        return ReadResult(status="empty", new_watermark=watermark)
    day_cap = msgs[0].time + max_days * 86400
    batch, backlog = [], False
    for m in msgs:
        if len(batch) >= max_messages or m.time > day_cap:
            backlog = True
            break
        batch.append(m)
    last_assistant = ""
    for m in batch:
        if m.role == "user":
            m.prior_assistant_text = last_assistant
        elif m.role == "assistant":
            last_assistant = m.text
    new_wm = min(batch[-1].time, now) if batch else watermark
    return ReadResult(status="data", messages=batch, new_watermark=new_wm, backlog_remaining=backlog)
