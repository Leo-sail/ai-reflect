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
        if fmt == "vscdb-kv":
            return _read_vscdb(adapter, cutoff_floor, max_messages, max_days)
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


# ---------------------------------------------------------------------------
# VS Code 系（Cursor / Copilot / Trae / Windsurf）：state.vscdb 是 KV 表(ItemTable/cursorDiskKV)
# 塞 JSON blob，不是 messages 关系表。每个工具一个方言映射，把 KV 解析归一到 Msg。
# 只读打开，绝不写/删 state.vscdb（删 global 库会让 Cursor 卡 Loading Chat）。
# 任一工具 key 模式/时间戳不确定 → 落 parse_error，绝不静默当 empty。
# ---------------------------------------------------------------------------
MAX_VSCDB_ROWS = 50_000  # KV 遍历行数硬上限（vscdb 单库可达数万行），防 DoS


def _vscdb_iter(db, table, key_like):
    """只读遍历一个 vscdb 的 KV 表，产出 (key, value)。表名走标识符白名单，key 参数化，防注入。"""
    if not Path(db).exists():
        return
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table or ""):
        raise ValueError(f"非法表名: {table!r}")
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    try:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            raise ValueError(f"表不存在: {table}")
        if key_like:
            cur.execute(f"SELECT key, value FROM {table} WHERE key LIKE ? LIMIT ?",
                        (key_like, MAX_VSCDB_ROWS))
        else:
            cur.execute(f"SELECT key, value FROM {table} LIMIT ?", (MAX_VSCDB_ROWS,))
        for k, v in cur.fetchall():
            yield k, v
    finally:
        con.close()


def _coerce_ts(v):
    """vscdb 时间戳多为毫秒整数或 ISO 串；归一成 unix 秒。认不出返回 None。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v / 1000.0 if v > 1e12 else float(v)  # >1e12 视为毫秒
    if isinstance(v, str):
        try:
            from datetime import datetime
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _dialect_cursor(rows):
    """Cursor 方言：bubbleId:<composerId>:<bubbleId> 的 value 为 JSON，type 1=user 2=assistant；
    composerData:<id> 提供会话级时间，缺戳的 bubble 用其会话时间兜底。"""
    composer_time, bubbles = {}, []
    for key, val in rows:
        if not isinstance(val, str):
            continue
        try:
            obj = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        if key.startswith("composerData:"):
            cid = key.split(":", 1)[1]
            t = _coerce_ts(obj.get("createdAt") or obj.get("lastUpdatedAt"))
            if t:
                composer_time[cid] = t
        elif key.startswith("bubbleId:"):
            parts = key.split(":")
            cid = parts[1] if len(parts) > 1 else ""
            role = {1: "user", 2: "assistant"}.get(obj.get("type"))
            text = obj.get("text") or obj.get("richText") or ""
            if isinstance(text, dict):
                text = text.get("text", "")
            bubbles.append((role, text, _coerce_ts(obj.get("createdAt") or obj.get("timestamp")), cid))
    msgs = []
    for role, text, t, cid in bubbles:
        if role is None:
            continue
        if t is None:
            t = composer_time.get(cid)
        if t is None:
            continue
        msgs.append(Msg(role=role, time=t, text=text or "", session_id=cid))
    return msgs


_VSCDB_DIALECTS = {"cursor": _dialect_cursor}


def _read_vscdb(adapter, watermark, max_messages, max_days):
    dialect = adapter.get("dialect")
    mapper = _VSCDB_DIALECTS.get(dialect)
    if mapper is None:
        # Copilot / Trae 等：框架就绪，但 key 模式须在装有该工具的机器上 dump 确认后才启用，不臆测
        return ReadResult(status="parse_error",
                          note=f"vscdb 方言 '{dialect}' 未在本机验证；请在装有该工具的机器 dump ItemTable 后补 mapping")
    rows, matched_db = [], False
    for spec in adapter.get("vscdb_sources", []):
        table = spec.get("table", "ItemTable")
        key_like = spec.get("key_like")
        for db in glob.glob(_expand(spec["db_glob"]), recursive=True):
            matched_db = True
            for k, v in _vscdb_iter(db, table, key_like):
                rows.append((k, v))
    if not matched_db:
        return ReadResult(status="empty", new_watermark=watermark)  # 没装/没库 = 真实无活动
    msgs_all = mapper(rows)
    if not msgs_all and rows:
        return ReadResult(status="parse_error", note="读到 KV 但无可解析消息，疑似 schema 演进")
    fresh = [m for m in msgs_all if m.time > watermark]
    if not fresh:
        return ReadResult(status="empty", new_watermark=watermark)
    return _window(fresh, watermark, max_messages, max_days)


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
