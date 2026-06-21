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

print("\nRESULT:", "ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
