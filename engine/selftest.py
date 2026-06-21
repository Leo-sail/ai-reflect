"""冒烟测试：验证确定性核心真的工作（不只是能编译）。退出码 0=全过。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ok = True
def check(name, cond):
    global ok
    print(("PASS" if cond else "FAIL"), name)
    ok = ok and cond

# 1. 脱敏 gate 真能抓密钥
from engine.sanitize import scan_and_redact, assert_clean
r = scan_and_redact("my key is sk-ant-abc123DEF456ghi789JKL and ip 10.0.0.1")
check("sanitize catches anthropic key", any(k == "anthropic_key" for k, _ in r.hits))
check("sanitize catches ip", any(k == "ipv4" for k, _ in r.hits))
check("sanitize redacts text", "sk-ant-" not in r.text)
check("clean text passes", scan_and_redact("just normal profile text about preferences").clean)
try:
    assert_clean("token=ABCDEFGH123456789")
    check("assert_clean blocks secret", False)
except ValueError:
    check("assert_clean blocks secret", True)

# 2. 窗口积压硬上限
from engine.readers import Msg, _window
msgs = [Msg(role="user", time=float(i), text=f"m{i}") for i in range(5000)]
res = _window(msgs, watermark=0.0, max_messages=2000, max_days=999)
check("window caps at max_messages", len(res.messages) == 2000)
check("window flags backlog", res.backlog_remaining is True)
check("watermark advances to batch end, not global end", res.new_watermark == 1999.0)

# 3. prior_assistant_text 标注（风格回声检测前提）
seq = [Msg(role="assistant", time=1, text="用简洁的句子"), Msg(role="user", time=2, text="好的简洁")]
res2 = _window(seq, 0.0, 2000, 999)
u = [m for m in res2.messages if m.role == "user"][0]
check("user msg carries prior_assistant_text", u.prior_assistant_text == "用简洁的句子")

# 4. 反馈：流失标 N/A 而非 0
from engine import feedback
sig = feedback.compute("toolx", user_msgs=[], watermark_advanced=False, prev={})
check("churn -> rate is None (N/A) not 0", sig.correction_rate is None and sig.verdict == "churned")

# 5. 反馈：纠正率算的是 /活跃轮 且能识别纠正语
um = [Msg(role="user", time=1, text="不对，应该用别的", session_id="s1"),
      Msg(role="user", time=2, text="再做一版", session_id="s1"),
      Msg(role="user", time=3, text="谢谢", session_id="s2")]
sig2 = feedback.compute("toolx", um, watermark_advanced=True, prev={})
check("correction detected & rate computed", sig2.corrections >= 1 and sig2.correction_rate is not None)

print("\nRESULT:", "ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
