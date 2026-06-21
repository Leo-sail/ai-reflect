"""侦测其他工具的扩展能力（skill/agent）变化（新增/更新/移除）。

为什么不只看"新增"：别的插件**升级**时，往往是改了已有 skill 的 version 或 description，
文件名不变。所以这里给每个能力存一个指纹（name + version + description 的哈希），
每次跑都和上轮指纹比对，能同时发现"新装的"和"已有的被更新了"。

只读、不改任何第三方文件。结果交给 reflect Skill，由它把变化**合并进**各工具配置的路由提示，不覆盖本地已有内容。
"""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

# 极简 frontmatter 取值（只用标准库，避免引入 yaml 依赖）
_FM = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _field(front: str, key: str) -> str:
    m = re.search(rf"^{key}\s*:\s*(.+)$", front, re.MULTILINE)
    if not m:
        return ""
    val = m.group(1).strip().strip('"\'')
    return val[:300]


def _read_manifest(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = _FM.search(text)
    front = m.group(1) if m else ""
    name = _field(front, "name") or path.parent.name if path.name.upper().startswith("SKILL") else path.stem
    version = _field(front, "version")
    desc = _field(front, "description")
    fp = hashlib.sha256(f"{name}|{version}|{desc}".encode("utf-8")).hexdigest()[:16]
    return {"name": name or path.stem, "version": version, "description": desc, "fingerprint": fp}


def scan_capabilities(skills_dir: str | None) -> dict:
    """扫一个工具的 skills 目录，返回 {能力id: 指纹信息}。能力id 用相对路径，稳定。"""
    out = {}
    if not skills_dir:
        return out
    base = Path(skills_dir).expanduser()
    if not base.exists():
        return out
    # SKILL.md（子目录式 skill）与顶层 *.md（命令式 agent）都扫
    for p in list(base.glob("*/SKILL.md")) + list(base.glob("*.md")) + list(base.glob("*/AGENT.md")):
        info = _read_manifest(p)
        if info:
            out[str(p.relative_to(base))] = info
    return out


def diff(prev: dict, now: dict) -> dict:
    """对比上轮与本轮指纹，分出 新增/更新/移除。prev/now 形如 scan_capabilities 的返回。"""
    added, updated, removed = [], [], []
    for cid, info in now.items():
        if cid not in prev:
            added.append({"id": cid, **info})
        elif prev[cid].get("fingerprint") != info.get("fingerprint"):
            updated.append({"id": cid, "from": prev[cid], "to": info})
    for cid in prev:
        if cid not in now:
            removed.append({"id": cid, **prev[cid]})
    return {"added": added, "updated": updated, "removed": removed,
            "changed": bool(added or updated or removed)}
