"""真实数据冒烟：用本机真实的 Hermes state.db 验证 sqlite 适配器端到端能读。
仅本地验证用，不进运行时。退出码 0=读到或确认空且无异常。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.readers import read_tool  # noqa: E402

adapter = {
    "id": "hermes", "format": "sqlite",
    "sqlite_db": "~/.hermes/state.db",
}
res = read_tool(adapter, watermark=0.0, max_messages=2000, max_days=3)
print("status:", res.status)
print("messages:", len(res.messages))
print("note:", res.note)
if res.messages:
    m = res.messages[0]
    print("sample role:", m.role, "| has text:", bool(m.text))
sys.exit(0 if res.status in ("data", "empty") else 1)
