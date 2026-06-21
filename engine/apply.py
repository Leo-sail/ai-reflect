"""可回滚写入：git 或本地备份（v4 + 安全审计修复）。

硬安全保证（不靠 LLM、不靠 git 钩子）：
- 所有落盘内容无条件过 sanitize.assert_clean（接所有写出口，backup 模式也不裸奔）。
- write_sentinel_block 的 target 必须在 allowed_config_targets() 白名单内（防提示注入写越界文件）。
- 哨兵区块拒绝 content 内嵌 BEGIN/END 标记（防伪造吞原文）。
- commit 前 Python 侧自跑密钥+冲突标记扫描，不依赖 pre-commit 钩子（钩子是冗余兜底）。
"""
from __future__ import annotations
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .sanitize import assert_clean, scan_and_redact

SENTINEL_BEGIN = "<!-- ai-reflect:auto BEGIN -->"
SENTINEL_END = "<!-- ai-reflect:auto END -->"
_CONFLICT = ("<<<<<<<", "=======", ">>>>>>>")


def _terms() -> list:
    return paths.load_preferences().get("sensitive_terms", [])


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
    dest_dir = paths.BACKUPS / _ts()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target.name
    if target.exists():
        shutil.copy2(target, dest)
        h = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
    else:
        h = "absent"
    return f"备份={dest} 写前哈希={h}"


def _scan_tree_for_problems(root: Path) -> list:
    problems = []
    for f in root.rglob("*"):
        if ".git" in f.parts or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for mk in _CONFLICT:
            if any(l.startswith(mk) for l in text.splitlines()):
                problems.append(f"{f.name}: 冲突标记 {mk}")
        r = scan_and_redact(text, _terms())
        if not r.clean:
            problems.append(f"{f.name}: 敏感信息 {sorted({k for k, _ in r.hits})}")
    return problems


def commit_synced(message: str) -> str | None:
    """storage=git 时提交 synced 仓。提交前 Python 侧自查，绝不 --no-verify。"""
    if not (paths.SYNCED / ".git").exists():
        return None
    problems = _scan_tree_for_problems(paths.SYNCED)
    if problems:
        raise RuntimeError("提交前自检阻断：" + "; ".join(problems))
    # 防钩子被旁路：核对 core.hooksPath 未被改向到仓外
    hp = _git(["config", "--get", "core.hooksPath"], paths.SYNCED).stdout.strip()
    if hp and not paths.is_within(Path(hp), paths.SYNCED / ".git"):
        raise RuntimeError(f"core.hooksPath 被指向仓外({hp})，拒绝提交。")
    _git(["add", "-A"], paths.SYNCED)
    r = _git(["commit", "-m", f"reflect: {message}"], paths.SYNCED)
    if r.returncode != 0:
        raise RuntimeError(f"git commit 被阻断：{r.stdout}{r.stderr}")
    return _git(["rev-parse", "--short", "HEAD"], paths.SYNCED).stdout.strip()


def write_text_gated(target: Path, content: str) -> None:
    """落盘 synced 内的画像/复盘：无条件过脱敏 gate（命中即抛错阻断）。"""
    if not paths.is_within(target, paths.SYNCED):
        raise ValueError(f"拒绝写入 synced 之外的路径：{target}")
    safe = assert_clean(content, _terms())
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(safe, encoding="utf-8")
    tmp.replace(target)


def write_sentinel_block(target: Path, content: str, backup: bool) -> str:
    """把自动内容写进目标文件哨兵区块之间。target 必须在白名单内；content 过脱敏 gate。"""
    if not any(paths.is_within(target, a) for a in paths.allowed_config_targets()):
        raise ValueError(f"拒绝写入授权清单之外的文件：{target}")
    if SENTINEL_BEGIN in content or SENTINEL_END in content:
        raise ValueError("content 含哨兵标记，拒绝写入（防伪造）。")
    safe = assert_clean(content, _terms())
    note = backup_external(target) if backup else ""
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    block = f"{SENTINEL_BEGIN}\n{safe}\n{SENTINEL_END}"
    if SENTINEL_BEGIN in original and SENTINEL_END in original:
        pre, _, rest = original.partition(SENTINEL_BEGIN)
        _, _, post = rest.partition(SENTINEL_END)
        new = pre + block + post
    else:
        new = (original.rstrip() + "\n\n" + block + "\n") if original else block + "\n"
    target.write_text(new, encoding="utf-8")
    return note
