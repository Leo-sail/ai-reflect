"""可回滚写入：git 或本地备份（v4 审计修复：哨兵注释、写前备份+哈希、绝不 --no-verify、冲突标记阻断）。"""
from __future__ import annotations
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import paths

SENTINEL_BEGIN = "<!-- ai-reflect:auto BEGIN -->"
SENTINEL_END = "<!-- ai-reflect:auto END -->"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def _git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def append_changelog(line: str) -> None:
    paths.CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    with paths.CHANGELOG.open("a", encoding="utf-8") as f:
        f.write(f"- {_now()} · {line}\n")


def backup_external(target: Path) -> str:
    """对不在 ai-reflect git 仓内的工具配置文件（如 ~/.claude/CLAUDE.md）：写前强制独立备份。"""
    dest_dir = paths.BACKUPS / _ts()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target.name
    if target.exists():
        shutil.copy2(target, dest)
        h = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
    else:
        h = "absent"
    return f"备份={dest} 写前哈希={h}"


def commit_synced(message: str) -> str | None:
    """storage=git 时提交 synced 仓。绝不加 --no-verify（让 pre-commit 钩子有效）。"""
    if not (paths.SYNCED / ".git").exists():
        return None
    _git(["add", "-A"], paths.SYNCED)
    r = _git(["commit", "-m", f"reflect: {message}"], paths.SYNCED)
    if r.returncode != 0:
        # 可能被 pre-commit 钩子（密钥/冲突标记）拦下——这是预期的安全行为
        raise RuntimeError(f"git commit 被阻断（可能命中钩子）：{r.stdout}{r.stderr}")
    short = _git(["rev-parse", "--short", "HEAD"], paths.SYNCED).stdout.strip()
    return short


def write_sentinel_block(target: Path, content: str, backup: bool) -> str:
    """把自动生成内容写进目标文件的哨兵区块之间，便于人工辨识与 revert。返回回滚提示。"""
    note = backup_external(target) if backup else ""
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    block = f"{SENTINEL_BEGIN}\n{content}\n{SENTINEL_END}"
    if SENTINEL_BEGIN in original and SENTINEL_END in original:
        pre = original.split(SENTINEL_BEGIN)[0]
        post = original.split(SENTINEL_END)[1]
        new = pre + block + post
    else:
        new = (original.rstrip() + "\n\n" + block + "\n") if original else block + "\n"
    target.write_text(new, encoding="utf-8")
    return note
