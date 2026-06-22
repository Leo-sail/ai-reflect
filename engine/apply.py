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
import sys
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


def _scan_dir_for_sentinel(dirp: Path) -> Path | None:
    """扫目录里所有 .md，返回第一个内容含 SENTINEL_BEGIN 的文件（=我们上次写的，不管它叫什么）。
    都没有则 None。只读、不改任何文件，读不了的文件跳过。与 detect._scan_dir_for_sentinel 同源逻辑，
    但在【写回时刻】重新扫，以当下目录实际状态为准（用户可能刚重命名了文件）。"""
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


def resolve_writeback_target(adapter: dict) -> Path | None:
    """按 adapter 解析【当下】真实写回文件。绝不臆想路径。

    scan 策略（Trae 系：文件名用户可改、厂商命名规则可能变）：写回时刻重扫 writeback_dir 找哨兵；
      命中就复用那个文件（不管叫什么），没命中用 global_config 给的新建名。目录不存在 → None。
    其它（fixed/缺省）：直接用 global_config。
    返回 None 表示目标不可解析（目录不存在等），调用方应跳过、不写。
    """
    gc = adapter.get("global_config")
    if adapter.get("writeback_strategy") == "scan":
        wd = adapter.get("writeback_dir")
        if not wd:
            return None
        dirp = Path(wd).expanduser()
        if not dirp.is_dir():
            return None  # 目录已不在（用户卸载/改路径）→ 不臆想、不新建到不存在的目录
        hit = _scan_dir_for_sentinel(dirp)
        if hit is not None:
            return hit
        return Path(gc).expanduser() if gc else dirp / "ai-reflect.md"
    return Path(gc).expanduser() if gc else None


def write_back(adapter: dict, content: str, backup: bool = True) -> dict:
    """Skill 写回入口：按 adapter 解析真实目标（scan 模式重扫哨兵）后写哨兵区块。
    返回 {status, target?, note?, reason?}。目标不可解析时 status=skipped，绝不乱写。"""
    target = resolve_writeback_target(adapter)
    if target is None:
        return {"status": "skipped",
                "reason": "写回目标不可解析（目录不存在或未确认），跳过，不臆想路径"}
    note = write_sentinel_block(target, content, backup)
    return {"status": "written", "target": str(target), "note": note}


def main(argv):
    """CLI：echo '{"adapter":{...},"content":"...","backup":true}' | python -m engine.apply write-back
    供 Skill 确定性写回——引擎自己按 adapter 解析真实目标（scan 模式重扫哨兵），不让 LLM 拼路径。
    退出码 0=已写 / 已安全跳过；1=出错或被安全门拒。"""
    import json as _json
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd != "write-back":
        sys.stderr.write("用法: echo '<json>' | python -m engine.apply write-back\n")
        return 2
    try:
        payload = _json.loads(sys.stdin.read())
        adapter = payload["adapter"]
        content = payload["content"]
        backup = payload.get("backup", True)
    except (ValueError, KeyError) as e:
        sys.stderr.write(f"载荷解析失败（需 JSON: adapter/content[/backup]）：{e}\n")
        return 1
    try:
        result = write_back(adapter, content, backup)
    except ValueError as e:  # 安全门拒绝（越界/伪造哨兵/命中密钥）
        sys.stdout.write(_json.dumps({"status": "rejected", "reason": str(e)}, ensure_ascii=False) + "\n")
        return 1
    sys.stdout.write(_json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
