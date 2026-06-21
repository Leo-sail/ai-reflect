"""导出便携包：把 synced/（画像/复盘/偏好）打成 zip，不含任何本机路径/水位线/凭证。
偏好里的 storage_mode/sync_mode/daily_time 等本机相关项会被剥离。"""
from __future__ import annotations
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import paths  # noqa: E402
from engine.sanitize import scan_and_redact  # noqa: E402

LOCAL_PREF_KEYS = {"storage_mode", "sync_mode", "daily_time"}
# 把本机绝对路径（含用户名）抹成占位符，防导出包泄露目录结构
_PATH_SCRUB = [
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\/:*?\"<>|\r\n]+"), r"C:\\Users\\<user>"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/<user>"),
    (re.compile(r"/home/[^/\s]+"), "/home/<user>"),
]


def _scrub(text: str, terms) -> str:
    text = scan_and_redact(text, terms).text
    for pat, repl in _PATH_SCRUB:
        text = pat.sub(repl, text)
    return text


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ai-reflect-export.zip")
    if not paths.SYNCED.exists():
        sys.stderr.write("没有 synced/ 可导出。\n")
        return 1
    terms = paths.load_preferences().get("sensitive_terms", [])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in paths.SYNCED.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(paths.SYNCED)
            # 排除 .git 与任何点开头内部文件（如 .engine_path）
            if any(part == ".git" or part.startswith(".") for part in rel.parts):
                continue
            text = _scrub(f.read_text(encoding="utf-8", errors="ignore"), terms)
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
