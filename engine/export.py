"""导出便携包：把 synced/（画像/复盘/偏好）打成 zip，不含任何本机路径/水位线/凭证。
偏好里的 storage_mode/sync_mode/daily_time 等本机相关项会被剥离。"""
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import paths  # noqa: E402
from engine.sanitize import scan_and_redact  # noqa: E402

# 导出时剥离的本机相关偏好（新机重新指定）
LOCAL_PREF_KEYS = {"storage_mode", "sync_mode", "daily_time"}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ai-reflect-export.zip")
    if not paths.SYNCED.exists():
        sys.stderr.write("没有 synced/ 可导出。\n")
        return 1
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in paths.SYNCED.rglob("*"):
            if ".git" in f.parts or not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            # 纵深防御：导出前再脱敏一次
            text = scan_and_redact(text).text
            rel = f.relative_to(paths.SYNCED)
            if f.name == "preferences.json":
                try:
                    d = json.loads(text)
                    for k in LOCAL_PREF_KEYS:
                        d.pop(k, None)
                    text = json.dumps(d, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    pass
            z.writestr(str(rel), text)
    print(f"已导出便携包: {out}（不含本机路径/水位线/凭证）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
