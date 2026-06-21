"""CLI 脱敏检查：echo "text" | python -m engine.sanitize_check  → 退出码 0=干净 1=命中。
供 Skill 在落盘前做硬门校验。也可传文件路径逐个检查。"""
import sys
from pathlib import Path
from engine.sanitize import scan_and_redact


def main(argv):
    texts = []
    if len(argv) > 1:
        for p in argv[1:]:
            texts.append(Path(p).read_text(encoding="utf-8", errors="ignore"))
    else:
        texts.append(sys.stdin.read())
    bad = False
    for t in texts:
        r = scan_and_redact(t)
        if not r.clean:
            bad = True
            for kind, snip in r.hits:
                sys.stderr.write(f"命中 {kind}: {snip}\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
