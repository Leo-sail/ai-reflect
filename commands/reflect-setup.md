---
description: Re-scan installed AI tools and (re)configure / 重新扫描整机 AI 工具并（重新）配置接入、同步、回滚、时间、风格
---

**English**

Run `python -m engine.install` in Bash. It interactively scans the AI tools installed on this machine, asks for authorization one by one, lets the user choose the sync method (git remote / cloud drive / export package) and rollback method (git / backup), set the daily time, specify the initial speaking style, and installs the OS-level scheduled heartbeat.

If the user mentions in conversation that they just installed a new tool, this command can also be triggered directly for a full re-scan. When a new tool is found, connect it only after the user explicitly authorizes it; never auto-connect an unauthorized directory.

---

**中文**

在 Bash 运行 `python -m engine.install`。它会交互式扫描本机已装 AI 工具、逐个征求授权、让用户选同步方式（git 远程/云盘/导出包）与回滚方式（git/备份）、定每日时间、指定初始沟通风格，并安装 OS 级定时心跳。

若用户在对话里提到刚装了新工具，也可直接触发本命令做全盘复扫。发现新工具时只在征得用户明确授权后才接入，绝不自动连接未授权的目录。
