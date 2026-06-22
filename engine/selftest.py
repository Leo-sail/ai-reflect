"""冒烟测试：验证确定性核心真的工作（含推送前安全回归）。退出码 0=全过。"""
import sys
import tempfile
import time as _time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ok = True
def check(name, cond):
    global ok
    print(("PASS" if cond else "FAIL"), name)
    ok = ok and cond

# 1. 脱敏 gate
from engine.sanitize import scan_and_redact, assert_clean
r = scan_and_redact("my key is sk-ant-abc123DEF456ghi789JKL and ip 10.0.0.1")
check("sanitize catches anthropic key", any(k == "anthropic_key" for k, _ in r.hits))
check("sanitize catches ip", any(k == "ipv4" for k, _ in r.hits))
check("sanitize redacts text", "sk-ant-" not in r.text)
check("clean text passes", scan_and_redact("just normal profile text about preferences").clean)
try:
    assert_clean("token=ABCDEFGH123456789"); check("assert_clean blocks secret", False)
except ValueError:
    check("assert_clean blocks secret", True)

# 2. 窗口积压硬上限
from engine.readers import Msg, _window
msgs = [Msg(role="user", time=float(i), text=f"m{i}") for i in range(5000)]
res = _window(msgs, watermark=0.0, max_messages=2000, max_days=999)
check("window caps at max_messages", len(res.messages) == 2000)
check("window flags backlog", res.backlog_remaining is True)
check("watermark = batch end not global end", res.new_watermark == 1999.0)

# 3. prior_assistant_text 标注
seq = [Msg(role="assistant", time=1, text="用简洁的句子"), Msg(role="user", time=2, text="好的简洁")]
u = [m for m in _window(seq, 0.0, 2000, 999).messages if m.role == "user"][0]
check("user msg carries prior_assistant_text", u.prior_assistant_text == "用简洁的句子")

# 4. 反馈信号
from engine import feedback
sig = feedback.compute("t", [], watermark_advanced=False, prev={})
check("churn -> rate None (N/A)", sig.correction_rate is None and sig.verdict == "churned")
um = [Msg(role="user", time=1, text="不对，应该用别的", session_id="s1"),
      Msg(role="user", time=2, text="再做一版", session_id="s1")]
sig2 = feedback.compute("t", um, watermark_advanced=True, prev={})
check("correction detected", sig2.corrections >= 1 and sig2.correction_rate is not None)

# --- 安全回归（推送前审计修复）---
# 5. ReDoS：超长恶意串快速返回
big = "a" * 100000 + "@" + "b" * 100000
t0 = _time.time(); scan_and_redact(big)
check("no ReDoS on long input (<0.5s)", _time.time() - t0 < 0.5)

# 6. 未来时间戳投毒被丢弃
rf = _window([Msg(role="user", time=_time.time() + 10**9, text="poison")], 0.0, 2000, 999)
check("future timestamp poison dropped", rf.status == "empty" and rf.new_watermark == 0.0)

# 7. 写入 gate：路径限定 + 脱敏 + 哨兵伪造拒绝
from engine import apply, paths as P
P.SYNCED = Path(tempfile.mkdtemp()) / "synced"; P.SYNCED.mkdir()
P.PREFERENCES = P.SYNCED / "preferences.json"
apply.write_text_gated(P.SYNCED / "p.md", "正常内容")
check("gated write ok", (P.SYNCED / "p.md").exists())
try:
    apply.write_text_gated(P.SYNCED / "p.md", "key sk-ant-" + "x" * 30)
    check("gated write blocks secret", False)
except ValueError:
    check("gated write blocks secret", True)
try:
    apply.write_text_gated(P.SYNCED.parent / "outside.md", "x")
    check("gated write blocks path escape", False)
except ValueError:
    check("gated write blocks path escape", True)
check("is_within ok", P.is_within(P.SYNCED / "a.md", P.SYNCED))
check("is_within blocks traversal", not P.is_within(P.SYNCED / ".." / "x", P.SYNCED))

# 8. 能力侦测：新增/更新/移除都认得
from engine import discover
import os as _os
sk = Path(tempfile.mkdtemp()) / "skills"
(sk / "alpha").mkdir(parents=True)
(sk / "alpha" / "SKILL.md").write_text("---\nname: alpha\nversion: 1.0\ndescription: do A\n---\n", encoding="utf-8")
caps1 = discover.scan_capabilities(str(sk))
check("discover finds a skill", any("alpha" in k for k in caps1))
# 更新 description -> 指纹变 -> updated
(sk / "alpha" / "SKILL.md").write_text("---\nname: alpha\nversion: 1.1\ndescription: do A better\n---\n", encoding="utf-8")
caps2 = discover.scan_capabilities(str(sk))
d = discover.diff(caps1, caps2)
check("discover detects update", len(d["updated"]) == 1 and d["changed"])
# 新增一个 -> added
(sk / "beta").mkdir()
(sk / "beta" / "SKILL.md").write_text("---\nname: beta\ndescription: do B\n---\n", encoding="utf-8")
caps3 = discover.scan_capabilities(str(sk))
check("discover detects add", len(discover.diff(caps2, caps3)["added"]) == 1)
# 移除 -> removed
check("discover detects remove", len(discover.diff(caps3, caps2)["removed"]) == 1)

# 9. vscdb-kv reader（Cursor 方言）：用合成 fixture 验证 KV→Msg 归一与只读
import sqlite3 as _sq
from engine import readers as _rd
vdir = Path(tempfile.mkdtemp())
vdb = vdir / "state.vscdb"
_con = _sq.connect(str(vdb))
_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
import json as _json, time as _t
_base = _t.time() - 3600
_con.execute("INSERT INTO ItemTable VALUES (?,?)",
             ("composerData:c1", _json.dumps({"createdAt": int(_base * 1000)})))
_con.execute("INSERT INTO ItemTable VALUES (?,?)",
             ("bubbleId:c1:b1", _json.dumps({"type": 1, "text": "帮我改个 bug", "createdAt": int((_base+1)*1000)})))
_con.execute("INSERT INTO ItemTable VALUES (?,?)",
             ("bubbleId:c1:b2", _json.dumps({"type": 2, "text": "好的，问题在第3行", "createdAt": int((_base+2)*1000)})))
_con.commit(); _con.close()
_adapter = {"format": "vscdb-kv", "dialect": "cursor",
            "vscdb_sources": [{"db_glob": str(vdir / "state.vscdb"), "table": "ItemTable", "key_like": "bubbleId:%"},
                              {"db_glob": str(vdir / "state.vscdb"), "table": "ItemTable", "key_like": "composerData:%"}]}
_res = _rd.read_tool(_adapter, 0.0, 2000, 999)
check("vscdb cursor reads messages", _res.status == "data" and len(_res.messages) == 2)
check("vscdb maps roles", {m.role for m in _res.messages} == {"user", "assistant"})
check("vscdb carries text", any("bug" in m.text for m in _res.messages))
# 增量：水位线在第一条之后，只回第二条
_res2 = _rd.read_tool(_adapter, _base + 1.5, 2000, 999)
check("vscdb incremental by watermark", len(_res2.messages) == 1 and _res2.messages[0].role == "assistant")
# 未验证方言 -> parse_error，不静默当空
_res3 = _rd.read_tool({"format": "vscdb-kv", "dialect": "trae", "vscdb_sources": []}, 0.0, 2000, 999)
check("vscdb unknown dialect -> parse_error", _res3.status == "parse_error")
# 防注入：非法表名被拒（落 parse_error，不崩）
_res4 = _rd.read_tool({"format": "vscdb-kv", "dialect": "cursor",
                       "vscdb_sources": [{"db_glob": str(vdir / "state.vscdb"), "table": "Item;DROP", "key_like": "%"}]}, 0.0, 2000, 999)
check("vscdb rejects bad table name", _res4.status == "parse_error")

# 8. 运行时自动发现（detect）：分类靠实测，不臆想路径
from engine import detect as _dt

# 8a. 明文 SQLite 魔数 vs 加密库
_pd = Path(tempfile.mkdtemp())
_plain = _pd / "plain.db"
_psql = _sq.connect(str(_plain)); _psql.execute("CREATE TABLE t (x)"); _psql.commit(); _psql.close()
check("detect: plain sqlite magic ok", _dt._sqlite_is_plain(_plain) is True)
_enc = _pd / "enc.db"
_enc.write_bytes(b"\x56\xb1\x90\x4d" + b"\x00" * 64)  # 非 SQLite 魔数（模拟厂商加密库头）
check("detect: encrypted db flagged not-plain", _dt._sqlite_is_plain(_enc) is False)

# 8b. messages 表识别
_mdb = _pd / "msg.db"
_m = _sq.connect(str(_mdb))
_m.execute("CREATE TABLE messages (role TEXT, content TEXT, timestamp REAL, session_id TEXT)")
_m.commit(); _m.close()
check("detect: messages table recognized", _dt._sqlite_has_messages_table(_mdb) is True)
check("detect: non-messages db -> False", _dt._sqlite_has_messages_table(_plain) is False)

# 8c. writeback 目标未确认时不臆想路径（探测一个不存在的 fork 目录）
_klass, _fmt, _dia, _src, _reason, _extra = _dt._classify_vscode_fork(
    "Trae CN", _pd / "nonexistent" / "User")
check("detect: unknown vscode layout -> unknown class", _klass in ("unknown", "writeback"))

# 8d. 写回目标探测：未知 fork（无候选规则目录）返回 (None, None)，绝不臆想路径
_wb, _wbdir = _dt._resolve_writeback_target("NoSuchForkXYZ")
check("detect: writeback target None when nothing exists", _wb is None and _wbdir is None)

# 8e. 哨兵常量必须与 apply 逐字一致，否则 detect 扫不到 apply 写的文件（防漂移）
from engine import apply as _ap
check("detect: sentinel matches apply BEGIN", _dt.SENTINEL_BEGIN == _ap.SENTINEL_BEGIN)

# 8f. scan 策略：扫到带哨兵的已有文件就复用它（不管文件名叫什么），不靠命名
_rules = Path(tempfile.mkdtemp())
(_rules / "我自己起的名字.md").write_text(
    "用户手建的规则，没有哨兵", encoding="utf-8")
_mine = _rules / "rule-9999.md"   # 名字完全不带 ai-reflect，模拟用户自定义命名
_mine.write_text(f"标题\n{_ap.SENTINEL_BEGIN}\n旧内容\n{_ap.SENTINEL_END}\n", encoding="utf-8")
_hit = _dt._scan_dir_for_sentinel(_rules)
check("detect: scan reuses sentinel file regardless of name", _hit == _mine)

# 8g. scan 策略：目录里没有带哨兵的文件 -> 返回 None（让上层用新前缀名新建）
_empty = Path(tempfile.mkdtemp())
(_empty / "别人的规则.md").write_text("无哨兵", encoding="utf-8")
check("detect: scan returns None when no sentinel present",
      _dt._scan_dir_for_sentinel(_empty) is None)

# 9. 写回引擎 scan 模式：apply.resolve_writeback_target / write_back 端到端
# 9a. scan 命中已有哨兵文件 -> 复用其真实路径（文件名用户可改）
_wbdir = Path(tempfile.mkdtemp())
_existing = _wbdir / "用户改的名字.md"
_existing.write_text(f"我的规则\n{_ap.SENTINEL_BEGIN}\n旧画像\n{_ap.SENTINEL_END}\n", encoding="utf-8")
_adp_scan = {"id": "trae-cn", "writeback_strategy": "scan",
             "writeback_dir": str(_wbdir), "global_config": str(_wbdir / "ai-reflect.md")}
check("apply: scan resolves to existing sentinel file",
      _ap.resolve_writeback_target(_adp_scan) == _existing)

# 9b. scan 未命中哨兵 -> 用 global_config 新建名（不臆想，落在真实目录内）
_wbdir2 = Path(tempfile.mkdtemp())
_adp_new = {"id": "trae-cn", "writeback_strategy": "scan",
            "writeback_dir": str(_wbdir2), "global_config": str(_wbdir2 / "ai-reflect.md")}
check("apply: scan falls back to new-name in real dir",
      _ap.resolve_writeback_target(_adp_new) == _wbdir2 / "ai-reflect.md")

# 9c. scan 目录不存在 -> None（不往不存在的目录写）
_adp_gone = {"id": "trae-cn", "writeback_strategy": "scan",
             "writeback_dir": str(_wbdir2 / "已被删"), "global_config": str(_wbdir2 / "x.md")}
check("apply: scan returns None when dir missing",
      _ap.resolve_writeback_target(_adp_gone) is None)

# 9d. write_back 端到端：把目标目录加进白名单后，更新哨兵区块、保留区块外原文
P.ADAPTERS = P.SYNCED / "adapters.json"
P.save_json(P.ADAPTERS, {"tools": [
    {"id": "trae-cn", "enabled": True, "writeback_dir": str(_wbdir),
     "global_config": str(_wbdir / "ai-reflect.md")}]})
_r = _ap.write_back(_adp_scan, "新画像内容", backup=False)
_after = _existing.read_text(encoding="utf-8")
check("apply: write_back writes to scanned file",
      _r["status"] == "written" and _r["target"] == str(_existing))
check("apply: write_back updates block, keeps outside text",
      "新画像内容" in _after and "我的规则" in _after and "旧画像" not in _after)

# 9e. write_back 目录不存在 -> status=skipped，绝不乱写
_r2 = _ap.write_back(_adp_gone, "x", backup=False)
check("apply: write_back skips when target unresolvable", _r2["status"] == "skipped")

print("\nRESULT:", "ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
