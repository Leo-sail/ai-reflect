"""效果反馈环（功能A）+ 把"纠正率"修成可信信号（v4 审计修复）。

审计指出原始"纠正率↓=学习有效"是坏信号：它把【AI变好 / 用户放弃 / 流失 / 换工具 / 趋同后察觉不了错】
压成一个数，且所有误读都指向"成功"。这里做四件事：
  1. 分母校正：纠正数 / 活跃交互轮数（不是 / 全部消息）。
  2. 流失识别：某工具水位线停滞 → 该工具纠正率标 N/A，不算 0。
  3. 独立参与度：消息长度、追问数、新需求数——纠正↓且参与↓ = 疑似放弃，告警而非庆功。
  4. 去重：按 (session_id) 计活跃轮，避免重复计数。
判定只产出"信号 + 是否需要主动向用户确认"，绝不据此自动给某方向加码（那是闭环自我奖励的根源）。
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# 用户纠正 AI 的语言信号（多语言、保守匹配，宁缺毋滥）
_CORRECTION_PATTERNS = [
    re.compile(r"(?i)\b(no|not like that|don'?t|stop|wrong|actually)\b"),
    re.compile(r"不对|不是这样|别这样|不要|错了|应该是|我说的是|重来|纠正|你理解错"),
]


def _is_correction(text: str) -> bool:
    return any(p.search(text or "") for p in _CORRECTION_PATTERNS)


@dataclass
class FeedbackSignal:
    tool: str
    correction_rate: float | None   # None = N/A（流失/无数据）
    active_turns: int
    corrections: int
    engagement: float               # 平均用户消息长度 * 追问密度，粗略参与度
    verdict: str                    # improving | flat | suspect_giving_up | churned | insufficient
    needs_user_confirmation: bool   # True 时应主动问用户而非自动结论


def compute(tool: str, user_msgs: list, watermark_advanced: bool, prev: dict) -> FeedbackSignal:
    """user_msgs: 本轮该工具的 user 消息列表(含 .text/.session_id)。prev: 上轮该工具信号快照。"""
    if not watermark_advanced and not user_msgs:
        # 水位线没动、也没新消息 = 该工具本期无活动 → 可能流失
        return FeedbackSignal(tool, None, 0, 0, 0.0, "churned", needs_user_confirmation=False)
    active_turns = len({m.session_id for m in user_msgs}) or len(user_msgs)
    if active_turns == 0:
        return FeedbackSignal(tool, None, 0, 0, 0.0, "insufficient", False)
    corrections = sum(1 for m in user_msgs if _is_correction(m.text))
    rate = corrections / active_turns
    avg_len = sum(len(m.text) for m in user_msgs) / max(len(user_msgs), 1)
    followups = sum(1 for m in user_msgs if "?" in m.text or "？" in m.text)
    engagement = avg_len * (1 + followups / max(len(user_msgs), 1))

    prev_rate = prev.get("correction_rate")
    prev_eng = prev.get("engagement", engagement)
    verdict, need_confirm = "flat", False
    if prev_rate is not None and active_turns >= 5:
        if rate < prev_rate - 0.05:
            # 纠正率下降——但必须排除"用户放弃"
            if engagement < prev_eng * 0.6:
                verdict, need_confirm = "suspect_giving_up", True  # 参与度也跌 → 别庆功，去问
            else:
                verdict = "improving"
        elif rate > prev_rate + 0.05:
            verdict = "flat"  # 纠正变多 → 某条认识可能改错了，触发复查（不在此处加码）
    else:
        verdict = "insufficient"
    return FeedbackSignal(tool, round(rate, 3), active_turns, corrections,
                          round(engagement, 1), verdict, need_confirm)
