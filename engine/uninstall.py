"""卸载：移除 OS 定时心跳；可选保留或删除 ~/.ai-reflect/。不碰各工具自己的文件。"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
from engine import paths, heartbeat  # noqa: E402


def main():
    print("=== ai-reflect 卸载 ===")
    print(heartbeat.remove_schedule())
    keep = input("保留你的画像与复盘（synced/）吗？(y/n) [y] ").strip().lower() or "y"
    if keep.startswith("y"):
        if paths.LOCAL.exists():
            shutil.rmtree(paths.LOCAL, ignore_errors=True)
        print(f"已移除本机绑定（local/）。保留 {paths.SYNCED}（含你的画像/复盘，可同步到别处）。")
    else:
        if paths.ROOT.exists():
            shutil.rmtree(paths.ROOT, ignore_errors=True)
        print(f"已移除全部 {paths.ROOT}。")
    print("注意：各工具自己的 CLAUDE.md/AGENTS.md/SOUL.md 未被删除；")
    print("其中 ai-reflect 自动写入的内容包在 <!-- ai-reflect:auto --> 哨兵之间，可手动删除。")


if __name__ == "__main__":
    main()
