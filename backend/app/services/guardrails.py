"""
DocuMind AI — Input/Output Guardrails (plan v3, Part 2, Step 1).

Pure rule functions only: zero I/O, zero DB, zero request-path imports.

  - sanitize_pii(text): regex redaction for emails, phone numbers,
    SSN/credit-card patterns and UUIDs -> "[REDACTED:<type>]" tokens.
  - is_injection(text): literal-phrase blocklist ("ignore previous
    instructions" style attempts) plus GUARDRAILS_STRICT-gated
    obfuscation-pattern detection (base64-looking runs, unusual unicode).
    Scope-accurate limitation (mirrors the approved plan wording): the
    injection defense blocks known literal-phrase patterns only — it does
    not prevent prompt injection in general; obfuscated, adversarial, or
    novel injection techniques are out of scope for this feature.
  - validate_output(text): post-generation checks — leaked
    RAG_PROMPT_TEMPLATE fragments and an unsafe-keyword blocklist.
    Explicitly a safety net, not a moderation suite.

Config kill switches: GUARDRAILS_ENABLED (all rules) and GUARDRAILS_STRICT
(base64 / unusual-unicode checks). Every function accepts explicit
enabled / strict overrides; None resolves to the current settings.
"""

import re

from app.config import get_settings

# ---------------------------------------------------------------------------
# PII patterns — sanitization, one pass, no lookaround loops
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_GROUPED_RE = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")
_CC_CONTIGUOUS_RE = re.compile(r"\b\d{13,19}\b")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]?\d{2,4}[\s.-]?\d{4}"
)
_PHONE_CONTIGUOUS_RE = re.compile(r"\b\d{10}\b")

# Replacement order matters (most specific first): UUIDs before the card
# run pattern (uuid digests would otherwise be half-mangled), SSNs before
# phones (identical digit shapes differ only by grouping), and the
# contiguous phone fallback last.
_PII_PASSES = (
    ("uuid", _UUID_RE),
    ("email", _EMAIL_RE),
    ("ssn", _SSN_RE),
    ("credit_card", _CC_GROUPED_RE),
    ("credit_card", _CC_CONTIGUOUS_RE),
    ("phone", _PHONE_RE),
    ("phone", _PHONE_CONTIGUOUS_RE),
)


# ---------------------------------------------------------------------------
# Prompt-injection blocklist — literal, word-bounded, case-insensitive
# ---------------------------------------------------------------------------

INJECTION_PHRASES = (
    "ignore previous instructions",
    "disregard all",
    "system prompt",
    "developer message",
    "jailbreak",
)

_BASE64_LOOKALIKE_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
_UNUSUAL_UNICODE_RE = re.compile(
    "["
    "\u200b-\u200f"      # zero-width space / joiner / bidi format
    "\u202a-\u202e"      # bidi embedding / override marks
    "\u2060-\u206f"      # invisible & deprecated format controls
    "\ufeff"             # BOM / ZWNBSP
    "\uff00-\uffef"      # fullwidth forms
    "]"
)

# ---------------------------------------------------------------------------
# Output validation — leaked system-prompt fragments + unsafe keywords
# ---------------------------------------------------------------------------

# Literal fragments of RAG_PROMPT_TEMPLATE (generation.py). If one of these
# shows up verbatim in an answer, the system prompt leaked into generation.
# Keep in sync when the template changes.
PROMPT_LEAK_FRAGMENTS = (
    "You are an expert AI assistant tasked with answering questions",
    "Context information is below",
    "Multiple chunks may come from the SAME document",
    "If the answer is not contained in the context, say",
    "Do not hallucinate",
)

# Unsafe-content blocklist. Scoped as a safety net, not a moderation suite:
# these are action phrasings, so benign document mentions (e.g. "the policy
# describes ransomware response") are not flagged.
UNSAFE_OUTPUT_KEYWORDS = (
    "deploy malware",
    "install ransomware",
    "steal credentials",
    "extract passwords",
    "sql injection payload",
    "execute arbitrary code",
    "keylog the",
)


def _resolve_flags(enabled, strict):
    """Resolve explicit overrides against current settings (None = use
    settings). Only reads config when a flag was not passed explicitly."""
    if enabled is None or strict is None:
        settings = get_settings()
        if enabled is None:
            enabled = settings.GUARDRAILS_ENABLED
        if strict is None:
            strict = settings.GUARDRAILS_STRICT
    return bool(enabled), bool(strict)


def sanitize_pii(text: str, *, enabled: bool | None = None) -> str:
    """Redact emails, phone numbers, SSNs, credit-card patterns and UUIDs
    into "[REDACTED:<type>]" tokens. Returns the input unchanged when
    guardrails are disabled."""
    enabled, _ = _resolve_flags(enabled, strict=True)
    if not enabled:
        return text
    for kind, pattern in _PII_PASSES:
        text = pattern.sub(f"[REDACTED:{kind}]", text)
    return text


def is_injection(text: str, *, enabled: bool | None = None, strict: bool | None = None) -> tuple[bool, tuple[str, ...]]:
    """Flag prompt-injection attempts. Returns (flagged, reasons).

    Literal blocklist matches are word-bounded and case-insensitive; the
    base64 / unusual-unicode scans run only in strict mode. Guardrail
    disabled (GUARDRAILS_ENABLED=false) means never flagged.
    """
    enabled, strict = _resolve_flags(enabled, strict)
    if not enabled:
        return False, ()

    normalized = " ".join(text.lower().split())
    flagged: list[str] = []
    for phrase in INJECTION_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            flagged.append(f"injection:{phrase}")

    if strict:
        if _BASE64_LOOKALIKE_RE.search(text):
            flagged.append("obfuscation:base64")
        if _UNUSUAL_UNICODE_RE.search(text):
            flagged.append("obfuscation:unicode")

    return bool(flagged), tuple(flagged)


def validate_output(text: str, *, enabled: bool | None = None) -> tuple[bool, tuple[str, ...]]:
    """Post-generation checks: leaked system-prompt fragments and
    unsafe-keyword blocklist. Returns (is_ok, flags); any flag means the
    answer must not be shipped as-is.
    """
    enabled, _ = _resolve_flags(enabled, strict=True)
    if not enabled:
        return True, ()
    if not text:
        return False, ("empty-output",)

    lowered = text.lower()
    flagged: list[str] = []
    for fragment in PROMPT_LEAK_FRAGMENTS:
        if fragment.lower() in lowered:
            flagged.append(f"prompt-leak:{fragment}")
    for keyword in UNSAFE_OUTPUT_KEYWORDS:
        if keyword in lowered:
            flagged.append(f"unsafe:{keyword}")

    return not flagged, tuple(flagged)