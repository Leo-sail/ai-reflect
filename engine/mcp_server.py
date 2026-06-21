"""ai-reflect MCP server：让任何支持 MCP 的工具实时只读这份共享画像（功能C）。

只读暴露 profile / 分面画像 / 复盘 / 当前沟通风格。绝不暴露 local/（水位线、备份、报告）。
所有返回都再过一遍脱敏 gate（纵深防御）。

依赖：mcp（pip install mcp）。若环境无 mcp，server 退化为打印提示并退出，不影响其余功能。
"""
from __future__ import annotations
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write("未安装 mcp 包，MCP server 不可用。pip install mcp 后重试。\n")
    sys.exit(0)

from engine import paths  # noqa: E402
from engine.sanitize import scan_and_redact  # noqa: E402

mcp = FastMCP("ai-reflect-memory")


def _terms():
    return paths.load_preferences().get("sensitive_terms", [])


def _safe_read(p) -> str:
    try:
        return scan_and_redact(p.read_text(encoding="utf-8"), _terms()).text
    except FileNotFoundError:
        return ""


@mcp.tool()
def get_user_profile() -> str:
    """返回当前用户画像（语言风格/习惯/技术水平/协同节奏），供本工具更贴合用户地回应。"""
    return _safe_read(paths.PROFILE) or "（画像尚未建立）"


@mcp.tool()
def get_communication_style() -> str:
    """返回用户**指定**的沟通风格偏好（由用户设定，非 AI 推断）。回应时应遵循它。"""
    prefs = paths.load_preferences()
    style = prefs.get("communication_style", "").strip()
    return style or "（用户未指定特定风格，用默认得体风格即可）"


@mcp.tool()
def list_retros() -> str:
    """列出项目复盘（解决的难题/走过的弯路/有效解法），供跨工具复用经验。"""
    if not paths.RETROS.exists():
        return "（暂无复盘）"
    return "\n".join(f"- {f.stem}" for f in sorted(paths.RETROS.glob("*.md")))


@mcp.tool()
def get_retro(name: str) -> str:
    """读取某个项目复盘全文。"""
    # 路径穿越防护：只接受 list_retros 暴露的精确白名单 stem
    valid = {f.stem for f in paths.RETROS.glob("*.md")} if paths.RETROS.exists() else set()
    if name not in valid:
        return f"（无此复盘：{name}）"
    f = paths.RETROS / f"{name}.md"
    if not paths.is_within(f, paths.RETROS):
        return "（拒绝：路径越界）"
    return _safe_read(f) or f"（无此复盘：{name}）"


if __name__ == "__main__":
    mcp.run()
