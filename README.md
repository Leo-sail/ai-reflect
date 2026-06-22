<div align="center">

# ai-reflect

**Make your AI assistants understand you better the more you use them.**

It quietly reviews your conversations with AI each day, learns who you are,
how you work, and what pitfalls you have hit, then feeds that understanding
back into every AI tool you use.

**English** · [中文](#中文)

</div>

---

## Why I built this

After using AI to write and build things for a while, one thing gets more and more annoying:

It does not remember you.

Today you spend half an hour telling it your preferred style, your technical background, the full context of your project. Tomorrow you open a new window and everything resets. You explain it all again. You corrected a bad habit of its last week, and this week it does the same thing. It always meets you as if for the first time.

What I want is simple: an assistant that **grows alongside me**. As I get better, its understanding of me should keep up. The preferences I have stated again and again, it should remember. The pitfalls we walked into together, it should help me avoid next time. Ideally it understands what I need right now better than I do.

Most "memory" solutions out there either dump your entire chat history somewhere, or stand up a heavy database. For someone like me who just wants to use a few tools quietly on their own machine, that is both too heavy and too cold.

So ai-reflect exists. It does not store all your chats. It does something harder: from your real daily conversations, it distills a **small, accurate, and expirable** set of judgments into a little profile you can open and edit anytime. It keeps correcting and trimming itself so the profile never grows bloated. Then it feeds that understanding back to your tools, each in its own format.

In one line: **it helps your AI remember you, and helps you get more out of AI over time.**

— by leochang (leochang210@gmail.com)

---

## What it does for you

**Reviews automatically every day.** Without you asking, it reads your new conversations in the background and gradually figures out how you speak, how you work, your technical depth, and the pace you prefer, recording it into a profile that gets more accurate over time.

**Remembers lessons from projects.** What hard problems you and the AI solved, what detours you took, and how you finally got it working: it saves all of that so similar situations later can reuse it.

**Wakes up neglected features.** You have installed plenty of extensions for your AI tools, and many may never get used. Based on your habits, it reminds the AI in the right places that "this kind of task should use that capability," so they do not sit idle.

**Gets leaner as you go.** As your level rises, the verbose hand-holding meant for beginners should be removed. It automatically deletes the stale, merges the duplicated, and keeps the profile short and accurate.

**Gives you a report on demand.** Just ask, and it produces a report built entirely from **real data**: how often you used it, which features, how much time and cost, what projects you did, what problems came up and how they were solved, and what you and the AI each gained.

**You decide the speaking style.** The tone the AI uses with you is set by you and changeable anytime. It will not secretly imitate your way of talking (why not is explained under "Before you use it").

**No text boxes: you pick and edit, never type from scratch.** After every run (including the first), it does not ask you to type a reply. It shows you its draft, you can edit it, and wherever possible the choices are presented as options to pick rather than blanks to fill. Nothing syncs to your files until you confirm.

**Notices when your other tools get updated.** Every run it checks whether your other AI tools' extensions changed (newly installed, upgraded, or removed), not just once a week. When something changed, it folds the new capability into the routing hints so it actually gets used, editing only its own marked block and never touching what you wrote.

**Updates itself without touching your data.** When a new version of ai-reflect is out, it first tells you what is new and what it would add, then updates only the plugin code after you confirm. Your profile, project lessons, preferences, connected tools, and progress are never modified; new settings are filled in only where you never set a value.

---

## A few deliberate design choices

Each one exists to dodge a real pitfall.

**Judgment goes to the AI, certainty goes to code.** "What in this conversation is worth keeping" and "is this preference stable" need a brain, so the AI handles them. "Read files, query data, strip secrets, save" must be reliable and never guessed, so plain code handles them.

**It has to know whether it is doing well.** It watches one signal: whether the number of times you correct it goes down over time. But fewer corrections is not always good. You might just be tired of correcting it, or have stopped using it. So it also watches how engaged you still are. When both drop together, it does not congratulate itself; it asks you directly, and never quietly hands itself a reward.

**Before changing your stuff, it shows you first.** By default it does not touch your config directly. It collects what it "plans to change" into a draft, and only applies it once you approve. Once you trust it, you can switch to automatic writes, and every change keeps a backup you can roll back.

**A tool that saves you money must not waste it.** It only reads new conversations each day, with a cap. Even if you have not opened your machine for days and a pile has built up, it digests it in batches rather than blowing up in one run. On days with no new conversations, it just checks in and stops.

---

## Where the inspiration came from

This direction was not something I made up. Several public pieces of research and products all point down the same road:

- In **Stanford's "virtual town" experiment**, the AI characters periodically recall their experiences, distill scattered events into more useful summaries about themselves, and use those summaries to guide later behavior. ai-reflect's "review" learns from this, with one extra step: every review forces it to ask "which of my current judgments about the user is most likely wrong," so it does not drift further off.
- **The Letta project** made a point: a lot of information is known ahead of time, so rather than thinking it through only when you ask, think it through during idle time. ai-reflect doing its work in the background while you are away is exactly this idea.
- **Claude itself has a similar mechanism** (extracted by the community from its install package): also reviewing memory during idle time, merging new things, deleting the outdated, and keeping the index clean. It happened to line up with my approach, which is some reassurance the road is right.

To be clear: ai-reflect did not copy code or text from any of the above. It just took the plain idea they all point to and made it into a small thing that runs on your own machine, across several tools, and that you can undo anytime.

---

## How to install

You need Python (version 3.9 or higher). git and mcp are optional; it runs without them, you just lose two abilities (rollback, and letting other tools read the profile live).

The smoothest way is as a Claude Code plugin: install it, then run `/reflect-setup`. Setup is presented as choices you pick and a draft you can edit, not a list of blanks to type into:

1. Which detected AI tools to connect (off by default; connected only if you choose to).
2. How the profile syncs across devices: cloud drive, private git remote, or manual export.
3. How to keep an undo path: git or local backup.
4. Apply mode: draft (shows changes first, recommended) or direct write.
5. What time each day it reviews, picked from presets or a custom time.
6. An initial speaking style from presets, or leave it default.
7. Optional extra sensitive terms (client names, project codenames) that get replaced when writing the profile and reports.

When you confirm, it registers a scheduled task in your OS that runs daily on its own, with no babysitting and no dependency on any app staying open.

Prefer the command line? `python -m engine.install plan` prints the draft setup, and `python -m engine.install apply` applies it after you edit the draft.

**Supported tools.** Out of the box: Claude Code, Codex, Hermes, and Cursor. Also runs inside Anthropic's Cowork (same plugin format, no changes). VS Code + Copilot and Trae have their adapters built but turned off until verified on a machine that has them; see [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). Any other tool can be added by hand in three steps.

---

## Daily use

Normally you do nothing; it runs itself each day. After every run it shows you a draft and lets you pick what to apply, then syncs only after you confirm. To call it manually, use these commands:

```text
Review right now             ->  /reflect
Produce a report             ->  /reflect-report        (pick weekly / monthly / yearly / custom)
Change the AI speaking style ->  /reflect-style         (pick from presets, or type your own)
Re-scan your installed tools ->  /reflect-setup
Update ai-reflect itself     ->  /reflect-update        (shows what is new; never touches your data)
```

Done with it: `python engine/uninstall.py`. It removes the scheduled task and asks whether to keep the profile.

---

## Roughly how it runs

Your data lives in two places, which is the key to using it across devices:

- **Travels with you** (syncable to other devices): your profile, project lessons, preference settings.
- **Bound to this machine** (never synced): local file paths, how far it has read, device id, backups.

When you switch computers, sync the "travels with you" part over, re-scan tools on the new machine, and the old machine's paths will not tag along and cause trouble.

More detail on the internal design, security practices, and sync methods is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md), and [docs/SYNC.md](docs/SYNC.md).

**Want to connect Codex, Hermes, Open Claw, or other tools?** Full setup steps and instructions are in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

Before this was made, I picked it apart in two rounds (one checking whether the logic holds, one checking for security holes); the process and fixes are recorded in [docs/AUDIT.md](docs/AUDIT.md).

---

## Before you use it

- **It can only see conversations on your own machine.** Web chat data lives on someone else's server; the local side cannot reach it, so it is out of scope.
- **It will not secretly learn your speaking style, on purpose.** If it auto-learned your wording and fed it back, you would be nudged to use those words more, it would then see "you use them even more," learn to imitate harder, and eventually your tones blur together and it cannot tell what was originally yours. Leaving the style for you to set manually means this loop never forms.
- **Auto-detecting sensitive info is not foolproof.** Keys and passwords with a fixed shape can be caught; things without a pattern (like a client name) cannot, so they rely on the sensitive terms you entered at install. There is also a hard rule: the profile only writes summarized conclusions, never quoting your conversations verbatim.
- **What goes online cannot be fully deleted.** If some sensitive info slips through and gets pushed to the cloud, deleting the file is not enough; you have to rewrite history specifically.
- **Syncing via cloud drive means handing the profile to the cloud provider.** If that bothers you, choose private git remote or manual export.
- **It edits the config files of your other tools.** Everything it writes automatically is wrapped in a clearly visible pair of `<!-- ai-reflect:auto BEGIN/END -->` comments, easy to spot and to delete. It never changes a single word in the body of others' extensions, at most touching a trigger description.

---

## License and attribution

This project is made by **leochang (leochang210@gmail.com)**.

- **Personal, learning, research, and other noncommercial use**: free to use and modify; please keep the attribution.
- **Commercial use**: requires prior permission from the author at **leochang210@gmail.com**; commercial use without authorization is not permitted.

Full terms in [LICENSE](LICENSE).

---
---

<div align="center">

<a name="中文"></a>
# ai-reflect（中文）

**让你的 AI 助手，越用越懂你。**

每天悄悄回顾你和 AI 的对话，记住你是谁、你怎么干活、你踩过哪些坑，
然后把这份了解喂回给你用的每一个 AI 工具。

[English](#ai-reflect) · **中文**

</div>

---

## 为什么做这个

用 AI 写东西、做项目久了，有件事会越来越让人烦：

它不记得你。

今天你跟它磨了半天，告诉它你喜欢的写法、你的技术底子、你这个项目的来龙去脉。明天换个窗口，一切归零，又得从头说一遍。你上周纠正过它的毛病，这周它照犯。它永远是第一次见你的样子。

我想要的其实很简单：一个**陪着我一起成长**的助手。我在变强，它对我的了解也该跟着更新；我反复说过的偏好，它该记住；我们一起趟过的坑，下次别再掉进去。它甚至应该比我更清楚，我现在到底需要什么。

市面上的"记忆"方案，要么是把聊天记录一股脑存起来，要么搭一套很重的数据库，对我这种就想在自己电脑上、安安静静用好几个工具的人来说，太重也太冷。

所以有了 ai-reflect。它不存你的全部聊天，它做的是一件更难的事：从你每天的真实对话里，提炼出**少量、准确、会过期**的判断，写成一份你随时能打开看、能改的小档案，并且不断自我修正、自我精简，不让它越长越啰嗦。然后把这份了解，按每个工具自己的规矩，喂回给它们。

一句话：**它帮你的 AI 记住你，也帮你把 AI 越用越顺手。**

— 作者 leochang（leochang210@gmail.com）

---

## 它能帮你做什么

**每天自动回顾。** 不用你开口，它在后台读你新产生的对话，慢慢摸清你说话的方式、做事的习惯、技术的深浅、喜欢的节奏，记成一份越来越准的个人档案。

**记住项目里的经验。** 你和 AI 一起解决了什么难题、走过哪些弯路、最后怎么弄好的，它都帮你存下来，下次遇到类似的事能直接复用。

**让冷落的功能动起来。** 你装了不少 AI 工具的扩展能力，很多可能从来没被用上。它会根据你的习惯，在合适的地方提醒 AI "这种活该用那个能力"，让它们别闲着。

**越用越精简。** 你水平涨了，那些当初照顾新手的啰嗦提示就该撤掉。它会自动删旧的、合重复的，让这份档案永远短而准，不浪费。

**随时要一份报告。** 你说一声，它就给你一份**全是真实数据**的报告：这段时间你用得多不多、用了哪些功能、花了多少时长和成本、做了哪些项目、遇到过什么问题又是怎么解决的、你和 AI 各自有哪些长进。

**说话风格你说了算。** AI 用什么口气跟你聊，是你定的，随时能改。它不会偷偷学你的腔调（为什么不这么做，下面"使用前请知道"里有说明）。

**不用打字：你来挑、来改，不用从头写。** 每次跑完（包含首次）它都不让你在文本框输入，而是把草稿给你看，你能编辑，能做选择的地方尽量给你选项点，而不是留空让你填。确认之前，什么都不会同步到你的文件里。

**别的工具更新了它马上知道。** 每次跑它都查你其他 AI 工具的扩展能力有没有变化（新装的、升级的、删掉的），不是一周才查一次。一旦有变化，它把新能力补进路由提示让它真正被用上，且只改自己那块带标记的内容，绝不动你写的东西。

**自己升级，但不动你的数据。** ai-reflect 出新版时，它先告诉你更新了哪些功能、会新增什么，你确认后才只更新插件代码。你的画像、项目经验、偏好、接入的工具、读取进度，一概不改；新设置只在你从没设过的地方才补上。

---

## 几个想清楚了才这么做的选择

每一条，都是为了躲开一个真实的坑。

**判断的事交给 AI，确定的事交给程序。** "这段对话里哪点值得记""这个偏好稳不稳"，需要脑子，交给 AI 来想。"读文件、查数据、删敏感信息、存档"，必须靠谱、不能瞎猜，交给固定的程序来干。

**它得能自己知道做得好不好。** 它会盯着一个信号：你纠正它的次数，是不是随时间变少了。但变少不一定是好事，也可能是你嫌烦不想纠正了，甚至不用了。所以它会同时看你还热不热衷于跟它聊，两样一起降的时候，它不会自我感觉良好，而是主动问你一句，绝不闷头给自己邀功。

**改你的东西之前，先给你看。** 默认它不直接动你的配置，而是把"打算怎么改"先攒成一份草稿，你点头才落实。等你信得过了，再开成自动写入，而且每次都留备份，随时能撤回。

**一个帮你省钱的工具，自己不能乱花。** 它每天只读新增的对话，还设了上限，哪怕你好几天没开机，攒了一大堆，它也是分几次慢慢消化，不会某一次撑爆。没有新对话的日子，它打个卡就收工。

---

## 灵感从哪来

这个方向不是我拍脑袋想的，有几个公开的研究和产品都指向了同一条路：

- **斯坦福的"虚拟小镇"实验**里，那些 AI 小人会定期回想自己的经历，把零碎的小事提炼成对自己更有用的总结，再拿这些总结指导后面的行为。ai-reflect 的"回顾"就是学的这个，还多加了一步：每次回顾都强迫自己问一句"我现在对用户的判断，哪条最可能是错的"，免得越想越偏。
- **Letta 这个项目**讲过一个道理：很多信息其实早就有了，与其等你问的时候才现想，不如趁空闲先把它想透。ai-reflect 选在你不用电脑的时候在后台干活，就是这个意思。
- **Claude 自己也有一套类似机制**（社区从它的安装包里扒出来的），同样是趁空闲回顾记忆、合并新东西、删掉过时的、保持目录清爽。它跟我的做法撞了个正着，也算反过来证明这条路走得对。

需要说明：ai-reflect 没有抄上面任何一家的代码或文案，只是把它们共同指向的那个朴素道理，做成了一个能在你自己电脑上、跨好几个工具、还能随时反悔的小东西。

---

## 怎么装

需要先有 Python（3.9 以上版本）。git 和 mcp 是选装的，没有也能跑，只是少两个能力（回滚和让别的工具实时读档案）。

最顺的方式是当作 Claude Code 插件装好，然后跑 `/reflect-setup`。配置是**给你选项点、给草稿改**，不是列一堆空让你填：

1. 接入哪些已探测到的 AI 工具（默认不接，你选了才接）。
2. 档案怎么在多台设备间同步：网盘、私有 git 远程、或手动导出。
3. 怎么留后悔药：git 或本地备份。
4. 应用模式：草稿（先给你看，推荐）或直接写入。
5. 每天几点回顾，从预设里挑或自定。
6. 从预设里挑个初始说话风格，或保持默认。
7. 可选的额外敏感词（客户名、项目代号），写档案和报告时会替换掉。

你确认后，它在系统里挂一个定时任务，每天到点自己跑，不用你管，也不依赖任何软件一直开着。

喜欢命令行？`python -m engine.install plan` 打印草稿配置，编辑好草稿后 `python -m engine.install apply` 落地。

**支持哪些工具。** 开箱即用：Claude Code、Codex、Hermes、Cursor。也能在 Anthropic 的 Cowork 里跑（同插件格式、零改动）。VS Code + Copilot 和 Trae 的适配器已经写好但默认关着，要在装有它们的机器上验证后才点亮，见 [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)。其他任何工具都能照三步手动加。

---

## 平时怎么用

平时你什么都不用做，它自己每天跑。每次跑完它把草稿给你看、让你挑要应用哪些，确认后才同步。想手动叫它，用这几个命令：

```text
立刻回顾一次           →  /reflect
出一份报告              →  /reflect-report        （挑 周报 / 月报 / 年报 / 自定义）
改 AI 的说话风格        →  /reflect-style         （从预设里挑，或自己写）
重新扫描你装的工具      →  /reflect-setup
升级 ai-reflect 自身    →  /reflect-update        （先告诉你有啥新功能；绝不动你的数据）
```

不想用了：`python engine/uninstall.py`，它会撤掉定时任务，并问你档案要不要留着。

---

## 它大概怎么运转

你的数据放两个地方，这是能在多台设备间用的关键：

- **跟着你走的**（可同步到别的设备）：你的个人档案、项目经验、偏好设置。
- **绑在这台电脑上的**（绝不同步）：本机的文件路径、读到哪了、设备编号、备份。

换电脑时，把"跟着你走的"那份同步过去，在新电脑上重新扫一遍工具就行，旧电脑的路径不会带过去添乱。

更细的内部设计、安全做法、同步方式，分别在 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)、[docs/SECURITY.md](docs/SECURITY.md)、[docs/SYNC.md](docs/SYNC.md)。

**想接入 Codex、Hermes、Open Claw 等其他工具？** 完整的配置步骤和说明在 [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)。

这套东西在做出来之前，被我反复挑过两轮毛病（一轮查逻辑通不通，一轮查有没有安全漏洞），过程和修复都记在 [docs/AUDIT.md](docs/AUDIT.md) 里。

---

## 使用前请知道

- **只能看你本机的对话。** 网页版的聊天数据在人家服务器上，本地拿不到，所以管不着。
- **它不会偷学你的说话风格，这是故意的。** 如果让它自动学你的措辞再用回给你，你会被它带着更常用那些词，它下次又看到"你更爱用了"，于是越学越像，最后你俩的腔调混成一团，它自己都分不清哪些是你本来的、哪些是它学来的。把风格交给你手动定，这个怪圈从根上就不会出现。
- **自动认敏感信息不是万能的。** 有固定样子的密钥、密码能认出来；没规律的（比如某个客户名）认不出来，得靠你装的时候填的那几个敏感词。另外有条铁规矩：档案里只写概括性的结论，绝不原话照抄你的对话。
- **传到网上的东西删不干净。** 万一有敏感信息漏了网、还推到了云端，光删文件没用，得专门重写历史记录。
- **用网盘同步，等于把档案交给网盘公司。** 介意的话就选私有云仓或手动导出。
- **它会改你别的工具的配置文件。** 凡是它自动写进去的内容，都用一对醒目的注释包起来，一眼能认出来，也能手动删。别人写的扩展能力，它正文一个字都不改，最多动一下触发说明。

---

## 授权与署名

本项目由 **leochang（leochang210@gmail.com）** 制作。

- **个人、学习、研究等非商业用途**：免费使用、修改，请保留署名。
- **商业用途**：需事先联系作者 **leochang210@gmail.com** 申请授权，未经授权不得商用。

完整条款见 [LICENSE](LICENSE)。
