"""导入便携包：把导出的 synced/ 内容解到本机 ~/.ai-reflect/synced/。
导入后仍需运行 install.py 完成本机 adapters/心跳配置（模式A）。"""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import paths  # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("用法: python -m engine.import <便携包.zip>\n")
        return 1
    pkg = Path(sys.argv[1])
    if not pkg.exists():
        sys.stderr.write(f"找不到包: {pkg}\n")
        return 1
    paths.SYNCED.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pkg) as z:
        z.extractall(paths.SYNCED)
    print(f"已导入到 {paths.SYNCED}")
    print("下一步：运行 python engine/install.py 完成本机工具扫描/心跳配置（模式A）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
