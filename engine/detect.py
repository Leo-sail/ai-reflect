"""运行时自动发现（模式A 的核心）——不写死任何绝对路径。

设计原则（应"按用户机器实际情况适配，不臆想"的要求）：
- 仓库里只存"工具家族签名"（跨平台候选根目录的相对模式）+ "存储格式分类器"。
- 真正的路径在**用户自己机器上**扫描得到，绝不由作者预填。
- 分类靠**实际打开存储**判定，而非靠家族标签猜：
    readable     能读对话 → 读 + 写回。形式：jsonl / 未加密 messages 表 sqlite / cursor 式 vscdb-kv。
    writeback    读不了对话，但能写回规则文件。形式：厂商加密库 / leveldb / 服务端。
    unknown      发现了工具但存储形态认不出 → 交给用户决定，绝不静默当空。
- 合规底线：对**厂商蓄意加密**的库（SQLite 魔数不符），一律不尝试解密、只归为 writeback。

detect() 的产物喂给 install.plan()，由它生成 adapters.json（路径都是本机实测值）。
"""
from __future__ import annotations
import glob
import json
import sqlite3
from pathlib import Path

# SQLite 合法文件头（未加密）。不符 = 加密/非 SQLite → 绝不解密，只写回。
_SQLITE_MAGIC = b"SQLite format 3\x00"

# 写回哨兵：我们写进第三方规则文件的内容用它包住。识别"哪个文件是我们的"永远靠扫描
# 这个标记，绝不靠文件名——因为像 Trae 这类工具文件名用户可自定义、厂商也可能改命名规则。
# 【必须与 apply.SENTINEL_BEGIN 逐字一致】否则 detect 扫不到 apply 写过的文件。改一处要同步另一处。
SENTINEL_BEGIN = "<!-- ai-reflect:auto BEGIN -->"


def _exists(p: str) -> Path | None:
    pp = Path(p).expanduser()
    return pp if pp.exists() else None


def _first_glob(pattern: str) -> Path | None:
    for m in glob.glob(str(Path(pattern).expanduser()), recursive=True):
        return Path(m)
    return None


def _sqlite_is_plain(path: Path):
    """读前 16 字节判断是否未加密 SQLite。返回 True/False；读不了（被锁/无权限）返回 None=未知。"""
    try:
        with path.open("rb") as fh:
            head = fh.read(16)
        return head == _SQLITE_MAGIC
    except OSError:
        return None


def _sqlite_has_messages_table(path: Path):
    """只读打开，确认存在带 role/content/timestamp 的 messages 表。读不了返回 None。"""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
        try:
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            if not cur.fetchone():
                return False
            cur.execute("PRAGMA table_info(messages)")
            cols = {r[1] for r in cur.fetchall()}
            return {"role", "content", "timestamp"}.issubset(cols)
        finally:
            con.close()
    except sqlite3.DatabaseError:
        return None


def _vscdb_has_keys(path: Path, like: str):
    """只读探测某 vscdb 的 ItemTable/cursorDiskKV 是否含某前缀的 key。读不了返回 None。"""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
        try:
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ItemTable','cursorDiskKV')")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                cur.execute(f"SELECT 1 FROM {t} WHERE key LIKE ? LIMIT 1", (like,))
                if cur.fetchone():
                    return True
            return False
        finally:
            con.close()
    except sqlite3.DatabaseError:
        return None


# ---------------------------------------------------------------------------
# 工具家族签名：每个家族给"跨平台候选根"。根存在才进一步分类。
# 路径里 ~ 会 expanduser；{vscroot} 在 Windows/Mac/Linux 各异，下方按平台展开。
# ---------------------------------------------------------------------------
def _vscode_user_dirs():
    """返回所有可能的 VS Code 系 User 目录候选（含各 fork、各平台、CN/国际/SOLO 变体）。"""
    bases = []
    # Windows
    bases += ["~/AppData/Roaming"]
    # Mac
    bases += ["~/Library/Application Support"]
    # Linux
    bases += ["~/.config"]
    # 各 fork 的应用目录名（含 Trae 全系：国际/CN/SOLO）
    apps = ["Cursor", "Code", "Code - Insiders", "VSCodium",
            "Trae", "Trae CN", "TRAE SOLO", "TRAE SOLO CN", "Windsurf"]
    out = []
    for b in bases:
        for a in apps:
            out.append((a, f"{b}/{a}/User"))
    return out


def _detect_jsonl_family(fam):
    root = _exists(fam["root"])
    if not root:
        return None
    # 确认至少有一个 transcript 文件（否则可能是装了没用 → 仍登记为 readable，empty 由 reader 判定）
    return {
        "id": fam["id"], "display": fam["display"], "klass": "readable",
        "format": fam["format"], "transcript_globs": fam["transcript_globs"],
        "transcript_exclude": fam.get("transcript_exclude", []),
        "global_config": fam["global_config"], "skills_dir": fam.get("skills_dir"),
        "reason": "本机发现，JSONL 对话可读",
    }


def _detect_hermes(fam):
    root = _exists(fam["root"])
    if not root:
        return None
    db = _exists(fam["sqlite_db"])
    if not db:
        return {"id": fam["id"], "display": fam["display"], "klass": "unknown",
                "global_config": fam["global_config"], "skills_dir": fam.get("skills_dir"),
                "reason": "发现 Hermes 但未找到 state.db，待用户确认路径"}
    plain = _sqlite_is_plain(db)
    has_msgs = _sqlite_has_messages_table(db) if plain else False
    if plain and has_msgs:
        klass, reason = "readable", "messages 表未加密，可读"
    elif plain is False:
        klass, reason = "writeback", "库已加密（SQLite 魔数不符），按合规只写回不解密"
    else:
        klass, reason = "unknown", "无法确认 messages 表结构（可能被锁/schema 漂移），待用户确认"
    return {"id": fam["id"], "display": fam["display"], "klass": klass, "format": "sqlite",
            "sqlite_db": str(db), "global_config": fam["global_config"],
            "skills_dir": fam.get("skills_dir"), "reason": reason}


def _classify_vscode_fork(app_name: str, user_dir: Path):
    """对一个 VS Code 系 User 目录做实测分类。返回 (klass, format, dialect, sources, reason, extra)。"""
    gs = user_dir / "globalStorage" / "state.vscdb"
    ws_glob = str(user_dir / "workspaceStorage" / "*" / "state.vscdb")
    # 1) Cursor 式：bubbleId/composerData 在 vscdb 里 → 可读
    cursor_like = None
    for db in [gs] + [Path(p) for p in glob.glob(ws_glob)]:
        if db.exists():
            r = _vscdb_has_keys(db, "bubbleId:%") or _vscdb_has_keys(db, "composerData:%")
            if r:
                cursor_like = True
                break
    if cursor_like:
        sources = [
            {"db_glob": ws_glob, "table": "ItemTable", "key_like": "bubbleId:%"},
            {"db_glob": ws_glob, "table": "ItemTable", "key_like": "composerData:%"},
            {"db_glob": str(gs), "table": "cursorDiskKV", "key_like": "composerData:%"},
            {"db_glob": str(gs), "table": "cursorDiskKV", "key_like": "bubbleId:%"},
        ]
        return ("readable", "vscdb-kv", "cursor", sources,
                "vscdb 含 bubbleId/composerData，可读", {})
    # 2) 厂商加密库：ModularData/ai-agent/database.db 存在且非明文 SQLite → 只写回（Trae 系）
    parent = user_dir.parent  # 应用根
    enc_db = None
    for cand in [parent / "ModularData" / "ai-agent" / "database.db",
                 parent / "ModularData" / "ai-agent" / "db" / "database.db"]:
        if cand.exists():
            enc_db = cand
            break
    if enc_db is not None:
        plain = _sqlite_is_plain(enc_db)
        if plain is False:
            return ("writeback", None, None, [],
                    "对话库 database.db 被厂商加密（SQLite 魔数不符），按合规只写回不解密", {})
        if plain is True:
            # 罕见：明文且像对话库
            if _sqlite_has_messages_table(enc_db):
                return ("readable", "sqlite", None, [],
                        "database.db 未加密且含 messages 表，可读",
                        {"sqlite_db": str(enc_db)})
            return ("unknown", None, None, [],
                    "database.db 未加密但表结构未知，待用户确认", {"sqlite_db": str(enc_db)})
        return ("writeback", None, None, [],
                "database.db 存在但被锁/读不了，保守按只写回处理", {})
    # 3) VS Code/Copilot 式：chatSessions 在文件系统
    if (user_dir / "globalStorage").exists() and gs.exists():
        idx = _vscdb_has_keys(gs, "chat.ChatSessionStore.index")
        sess_dir = next((d for d in [
            user_dir / "globalStorage" / "emptyWindowChatSessions",
        ] if d.exists()), None)
        if idx or sess_dir or list(glob.glob(str(user_dir / "workspaceStorage" / "*" / "chatSessions"))):
            return ("writeback", "vscode-chatsessions", "copilot", [],
                    "对话在文件系统 chatSessions（版本化，需装机后用真实会话验证字段），暂按只写回；"
                    "确认字段后可升级为可读", {})
    return ("unknown", None, None, [], "VS Code 系但未识别对话存储形态，待用户确认", {})


# VS Code 系各 fork 的显示名 + 写回目标【候选】目录（仅用于"探测真实存在的目标"，
# 绝不当成默认路径直接写——目录不存在就标 target_unconfirmed，交用户在 setup 时指认）。
#
# strategy 决定如何在命中的目录里定目标文件：
#   "fixed" — 用固定文件名（Cursor/Copilot 等约定明确的）。
#   "scan"  — 文件名【用户可自定义、厂商可能改命名规则】，绝不假设命名。做法：扫目录里所有
#             .md，逐个读内容找我们的 SENTINEL_BEGIN 哨兵；命中就复用那个文件（不管它叫什么），
#             没命中才新建一个带 ai-reflect 前缀的文件。Trae 系实测为"扫描目录加载、无索引清单"，
#             故用 scan。识别永远靠哨兵，不靠文件名。
# 元组：(显示名, [候选目录...], 新建时的文件名, strategy)
_VSC_FORKS = {
    "Cursor":          ("Cursor",            ["~/.cursor/rules"], "ai-reflect.mdc", "fixed"),
    "Code":            ("VS Code + Copilot", ["~/AppData/Roaming/Code/User/prompts",
                                              "~/Library/Application Support/Code/User/prompts",
                                              "~/.config/Code/User/prompts"], "ai-reflect.instructions.md", "fixed"),
    "Code - Insiders": ("VS Code Insiders",  ["~/AppData/Roaming/Code - Insiders/User/prompts",
                                              "~/.config/Code - Insiders/User/prompts"], "ai-reflect.instructions.md", "fixed"),
    "VSCodium":        ("VSCodium",          ["~/.config/VSCodium/User/prompts"], "ai-reflect.instructions.md", "fixed"),
    # Trae 系：实测（CN 版）真实规则目录是 user_rules（全局/用户级），文件名用户可自定义 → scan 策略。
    # 国际版子目录名无法在本机验证（未安装），故每个家族给多个候选变体，解析时【谁真实存在用谁】——
    # 靠"目录确实在"命中，不靠假设某个名字。都不在 → target_unconfirmed，交用户 setup 时指认。
    "Trae":            ("Trae",              ["~/.trae/user_rules", "~/.trae/rules"], "ai-reflect.md", "scan"),
    "Trae CN":         ("Trae CN",           ["~/.trae-cn/user_rules", "~/.trae-cn/rules"], "ai-reflect.md", "scan"),
    "TRAE SOLO":       ("Trae SOLO",         ["~/.trae/user_rules", "~/.trae/rules"], "ai-reflect.md", "scan"),
    "TRAE SOLO CN":    ("Trae SOLO CN",      ["~/.trae-cn/user_rules", "~/.trae-cn/rules"], "ai-reflect.md", "scan"),
    "Windsurf":        ("Windsurf",          ["~/.codeium/windsurf/memories"], "ai-reflect.md", "fixed"),
}


def _scan_dir_for_sentinel(dirp: Path) -> Path | None:
    """扫描目录里所有 .md，返回第一个内容含 SENTINEL_BEGIN 的文件（=我们上次写的，不管它叫什么）。
    都没有则返回 None。只读，不改任何文件。读不了的文件跳过。"""
    try:
        for f in sorted(dirp.glob("*.md")):
            try:
                if SENTINEL_BEGIN in f.read_text(encoding="utf-8", errors="ignore"):
                    return f
            except OSError:
                continue
    except OSError:
        return None
    return None


def _resolve_writeback_target(app_name: str):
    """只在【真实存在】的规则目录里给出写回目标；找不到返回 (None, None)。绝不臆想路径。

    fixed 策略：命中的目录下用固定文件名。
    scan  策略：先扫目录找带哨兵的已有文件并复用其真实路径（文件名用户可能已改）；
               没有则用带 ai-reflect 前缀的新文件名（下次仍靠哨兵重新识别，不依赖此名）。
    """
    meta = _VSC_FORKS.get(app_name)
    if not meta:
        return None, None
    _display, dirs, fname, strategy = meta
    for d in dirs:
        dp = _exists(d)
        if dp and dp.is_dir():
            if strategy == "scan":
                hit = _scan_dir_for_sentinel(dp)
                if hit is not None:
                    return str(hit), str(dp)        # 复用已存在的我方文件，不管它叫什么
                # 没有我方文件 → 新建。fname 已是 ai-reflect.md，不再重复加前缀。
                return str(dp / fname), str(dp)
            return str(dp / fname), str(dp)
    return None, None


def _detect_vscode_family():
    found = []
    seen = set()
    for app_name, user_pat in _vscode_user_dirs():
        ud = _exists(user_pat)
        if not ud or str(ud) in seen:
            continue
        seen.add(str(ud))
        klass, fmt, dialect, sources, reason, extra = _classify_vscode_fork(app_name, ud)
        display = _VSC_FORKS.get(app_name, (app_name,))[0]
        wb, wb_dir = _resolve_writeback_target(app_name)
        strategy = _VSC_FORKS.get(app_name, (None, None, None, "fixed"))[3]
        tool = {"id": app_name.lower().replace(" ", "-"), "display": display,
                "klass": klass, "user_dir": str(ud),
                "global_config": wb, "skills_dir": None, "reason": reason}
        if wb is not None and strategy == "scan":
            # scan 模式：写回引擎每次写前要重扫 writeback_dir 找哨兵，不认死 global_config 路径
            # （文件名用户可改、厂商命名规则可能变；global_config 只是"当前快照/新建时的名字"）
            tool["writeback_strategy"] = "scan"
            tool["writeback_dir"] = wb_dir
        if wb is None:
            # 探测不到真实写回目标 → 不臆想路径，标记待用户指认
            tool["target_unconfirmed"] = True
            tool["reason"] = reason + "；未在本机找到已存在的规则目录，写回目标待用户在 setup 时指认"
        if fmt:
            tool["format"] = fmt
        if dialect:
            tool["dialect"] = dialect
        if sources:
            tool["vscdb_sources"] = sources
        tool.update(extra)
        found.append(tool)
    return found


# JSONL 家族签名（跨平台候选根）
_JSONL_FAMILIES = [
    {"id": "claude-code", "display": "Claude Code", "root": "~/.claude",
     "format": "claude-jsonl", "transcript_globs": ["~/.claude/projects/**/*.jsonl"],
     "transcript_exclude": ["**/subagents/**", "**/workflows/**", "**/tool-results/**", "**/sessions/**"],
     "global_config": "~/.claude/CLAUDE.md", "skills_dir": "~/.claude/skills"},
    {"id": "codex", "display": "OpenAI Codex", "root": "~/.codex",
     "format": "codex-rollout-jsonl",
     "transcript_globs": ["~/.codex/sessions/**/*.jsonl", "~/.codex/archived_sessions/**/*.jsonl"],
     "transcript_exclude": ["**/plugins/**", "**/.tmp/**"],
     "global_config": "~/.codex/AGENTS.md", "skills_dir": "~/.codex/skills"},
]
_HERMES_FAMILY = {"id": "hermes", "display": "Nous Hermes", "root": "~/.hermes",
                  "sqlite_db": "~/.hermes/state.db", "global_config": "~/.hermes/SOUL.md",
                  "skills_dir": "~/.hermes/skills"}


def detect() -> list[dict]:
    """在本机扫描所有家族，返回探测到的工具列表（路径均为本机实测值）。"""
    tools = []
    for fam in _JSONL_FAMILIES:
        t = _detect_jsonl_family(fam)
        if t:
            tools.append(t)
    h = _detect_hermes(_HERMES_FAMILY)
    if h:
        tools.append(h)
    tools += _detect_vscode_family()
    return tools


if __name__ == "__main__":
    print(json.dumps(detect(), ensure_ascii=False, indent=2))
