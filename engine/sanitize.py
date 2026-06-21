"""确定性脱敏 gate（v4 审计核心修复：原方案的脱敏是 vaporware）。

原则：
- 独立于 LLM。任何文本在写入 profile/report/git 之前都必须过这里。
- 检测到强特征密钥 → 替换为占位符；同时返回命中清单，调用方可决定是否阻断。
- 凭证文件在读取层就该被 denylist 排除（见 readers.py），这里是兜底的第二道。
- 局限诚实写明：无正则特征的客户名/项目名，正则挡不住——所以画像写入侧另有"白名单写入"
  规则（只写抽象结论、不逐字摘录对话原文），见 SKILL.md。本模块只负责"有特征的密钥/PII"。
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# 强特征密钥规则（高精度，尽量不误伤普通文本）
_SECRET_PATTERNS = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret", re.compile(r"\baws_secret_access_key\b.{0,4}[:=].{0,4}[A-Za-z0-9/+]{40}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}\b")),
    ("google_api", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b")),
    ("generic_assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|passwd|token|access[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9/_+\-]{12,}")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
]


@dataclass
class ScanResult:
    text: str
    hits: list = field(default_factory=list)  # [(kind, matched_snippet_masked)]

    @property
    def clean(self) -> bool:
        return not self.hits


def scan_and_redact(text: str, extra_terms: list | None = None) -> ScanResult:
    """返回脱敏后的文本与命中清单。extra_terms 为用户自录的敏感词（客户名/项目名）。"""
    hits = []
    out = text
    for kind, pat in _SECRET_PATTERNS:
        def _sub(m, _kind=kind):
            snip = m.group(0)
            hits.append((_kind, snip[:4] + "***"))
            return f"[REDACTED:{_kind}]"
        out = pat.sub(_sub, out)
    for term in (extra_terms or []):
        if term and term in out:
            hits.append(("user_term", term[:2] + "***"))
            out = out.replace(term, "[REDACTED:user_term]")
    return ScanResult(text=out, hits=hits)


def assert_clean(text: str, extra_terms: list | None = None) -> str:
    """写入侧硬门：若仍有命中则抛错，阻断落盘/提交。"""
    r = scan_and_redact(text, extra_terms)
    if not r.clean:
        kinds = ", ".join(sorted({k for k, _ in r.hits}))
        raise ValueError(f"脱敏 gate 阻断：检测到敏感信息 [{kinds}]，已拒绝写入。")
    return r.text
