"""ai-reflect 自升级 —— 只换代码，绝不动你本地数据。

铁律：
- 升级只更新插件代码（git pull 这个 clone 目录），你的 ~/.ai-reflect/（画像/复盘/偏好/适配器/水位线）一概不碰。
- 迁移是**纯增量**：新增的 preferences 默认项，只在“你没设过”时补；已有值绝不覆盖。
- 升级前先 plan：报告“将更新到哪个版本、新增了哪些功能、会做哪些纯增量迁移”，由命令层用选择题让你确认后才 apply。
- 升级不读、不改、不删任何用户内容；只在 apply 后刷新 pre-commit 钩子与 .engine_path（指向新代码）。
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = ENGINE_DIR.parent
sys.path.insert(0, str(PLUGIN_DIR))
from engine import paths, __version__  # noqa: E402

# 版本迁移说明：键=版本，值=该版本新增/变更的“功能要点”（给用户看）+ 纯增量的新 preferences 默认项。
# 绝不在这里写任何会覆盖用户已有值的操作。
MIGRATIONS = {
    "0.4.0": {
        "highlights": ["首个发布版：每日反思、画像、复盘、配置路由、可回滚、脱敏 gate"],
        "new_prefs": {},
    },
    "0.5.0": {
        "highlights": [
            "配置改为零文本输入：安装与每轮确认都用选择题 + 可编辑草稿",
            "侦测其他插件能力变化（新增/更新/移除），每轮都查，变化合并进路由不覆盖本地",
            "新增自升级：只换代码、纯增量迁移、绝不动本地数据",
        ],
        "new_prefs": {"detect_capability_changes": True},
    },
    "0.6.0": {
        "highlights": [
            "新增 VS Code 系支持：Cursor 已可用（vscdb-kv reader，读 state.vscdb 键值表）",
            "Copilot / Trae 框架就绪、默认关闭，待在装有该工具的机器上验证 key 后点亮",
            "声明 Cowork 兼容：同插件格式零改动可用；Cowork 对话数据源暂不接（leveldb 绑账号）",
        ],
        "new_prefs": {},
    },
}


def _git(args):
    return subprocess.run(["git", *args], cwd=str(PLUGIN_DIR), capture_output=True, text=True)


def plan() -> dict:
    """检查远端有无更新，报告将更新到的版本、新功能、拟做的纯增量迁移。不改任何东西。"""
    cur = __version__
    fetch = _git(["fetch", "--quiet", "origin"])
    local = _git(["rev-parse", "HEAD"]).stdout.strip()
    remote = _git(["rev-parse", "@{u}"]).stdout.strip() if not _git(["rev-parse", "@{u}"]).returncode else ""
    behind = _git(["rev-list", "--count", "HEAD..@{u}"]).stdout.strip() if remote else "0"
    # 列出本地缺的、迁移表里登记的功能要点（> 当前版本）
    pending = {v: m["highlights"] for v, m in MIGRATIONS.items() if _ver_gt(v, cur)}
    prefs = paths.load_preferences()
    # 拟补的新默认项：仅在用户没设过时才会补
    additive = {}
    for v, m in MIGRATIONS.items():
        for k, dv in m.get("new_prefs", {}).items():
            if k not in prefs:
                additive[k] = dv
    return {
        "current_version": cur,
        "update_available": bool(remote) and behind != "0",
        "commits_behind": behind,
        "fetch_ok": fetch.returncode == 0,
        "new_feature_highlights": pending,
        "additive_pref_defaults": additive,
        "guarantee": "升级只换代码；你的画像/复盘/偏好/适配器/水位线一概不动；新默认项仅在你没设过时才补。",
    }


def apply() -> dict:
    """拉取新代码并做纯增量迁移。绝不触碰用户数据文件的已有内容。"""
    before = _git(["rev-parse", "HEAD"]).stdout.strip()
    pull = _git(["pull", "--ff-only", "--quiet"])
    if pull.returncode != 0:
        return {"ok": False, "error": "git pull 失败（可能本地代码被改过/非快进）", "detail": pull.stderr.strip()}
    after = _git(["rev-parse", "HEAD"]).stdout.strip()

    # 纯增量迁移：只给用户没设过的新默认项补默认值，已有值绝不动
    prefs = paths.load_preferences()
    added = {}
    for v, m in MIGRATIONS.items():
        for k, dv in m.get("new_prefs", {}).items():
            if k not in prefs:
                prefs[k] = dv
                added[k] = dv
    if added:
        paths.save_json(paths.PREFERENCES, prefs)

    # 刷新指向新代码的 .engine_path 与 pre-commit 钩子（仅当用 git 回滚）
    refreshed = False
    if (paths.SYNCED / ".git").exists():
        try:
            (paths.LOCAL / ".engine_path").write_text(str(ENGINE_DIR), encoding="utf-8")
            import shutil
            hooks = paths.SYNCED / ".git" / "hooks"
            if hooks.exists():
                shutil.copy2(ENGINE_DIR / "hooks" / "pre-commit", hooks / "pre-commit")
            refreshed = True
        except OSError:
            pass

    return {"ok": True, "from": before[:8], "to": after[:8],
            "added_pref_defaults": added, "hook_refreshed": refreshed,
            "note": "用户数据未改动。新功能要点见 plan 的 new_feature_highlights。"}


def _ver_gt(a: str, b: str) -> bool:
    def parts(s):
        return [int(x) for x in s.split(".") if x.isdigit()]
    return parts(a) > parts(b)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "plan"
    if cmd == "plan":
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        print(json.dumps(apply(), ensure_ascii=False, indent=2))
        return 0
    sys.stderr.write("用法: python -m engine.update [plan|apply]\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
