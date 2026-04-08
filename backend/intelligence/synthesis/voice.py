"""Voice consistency layer — single advisor tone for all WhatsApp messages.

Every message from YTIP sounds like one deeply informed advisor, not a system.
This module defines the voice rules, banned patterns, and tone guidelines
that the formatter and weekly brief both use.
"""

import re


# ---------------------------------------------------------------------------
# Banned phrases — these never appear in any message to the owner
# ---------------------------------------------------------------------------
BANNED_PHRASES = [
    # System internals
    "our AI", "our system", "the algorithm", "machine learning",
    "our analysis", "our model", "detected by", "flagged by",
    "the system has", "automated analysis", "data pipeline",
    "agent", "ravi", "maya", "arjun", "sara", "priya", "kiran", "chef",
    "quality council", "significance check", "corroboration",
    # Hedging / weak language
    "it seems like", "it appears that", "we think", "possibly",
    "it might be", "there could be", "perhaps", "maybe",
    "it looks like maybe",
    # Condescending
    "as a restaurant owner", "you should know", "as you know",
    "you may not realise", "let me explain",
    # Self-referential
    "I've been analysing", "I've been monitoring", "I noticed that",
    "I've detected", "I found that", "my analysis shows",
    "based on my review", "after careful analysis",
    # Generic / vague
    "your performance seems", "things look", "overall things",
    "in general", "on the whole",
    # Alarming without action
    "your business is at risk", "urgent warning", "critical alert",
    "emergency", "danger",
]

# Compiled regex for fast checking (case-insensitive)
_BANNED_RE = re.compile(
    "|".join(re.escape(p) for p in BANNED_PHRASES),
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Message structure rules
# ---------------------------------------------------------------------------
# Every finding message follows: Opening → Evidence → Action → Impact → Hook
# Every weekly brief follows the 8-section structure from the PRD.

MAX_FINDING_WORDS = 225
MAX_BRIEF_WORDS = 500
MAX_WHATSAPP_CHARS = 4096

# Category → opening tone (confident, direct, no preamble)
CATEGORY_TONE = {
    "revenue": "direct_alert",      # State the revenue fact immediately
    "menu": "discovery",            # Frame as an insight the owner didn't know
    "stock": "operational",         # Prep/waste — practical and specific
    "customer": "relationship",     # Frame around people, not numbers
    "cultural": "forward_looking",  # Frame around what's coming
    "competition": "strategic",     # Frame around market position
    "innovation": "creative",       # Frame as an opportunity
}


# ---------------------------------------------------------------------------
# WhatsApp formatting helpers
# ---------------------------------------------------------------------------
def bold(text: str) -> str:
    """WhatsApp bold: *text*."""
    return f"*{text}*"


def italic(text: str) -> str:
    """WhatsApp italic: _text_."""
    return f"_{text}_"


# ---------------------------------------------------------------------------
# Voice enforcement
# ---------------------------------------------------------------------------
def check_voice(message: str) -> list[str]:
    """Check a message against voice rules. Returns list of violations."""
    violations = []

    # Check banned phrases
    matches = _BANNED_RE.findall(message)
    if matches:
        violations.extend(
            f"banned phrase: '{m}'" for m in set(matches)
        )

    # Check word count
    word_count = len(message.split())
    if word_count > MAX_FINDING_WORDS:
        violations.append(
            f"too long: {word_count} words (max {MAX_FINDING_WORDS})"
        )

    # Check char count
    if len(message) > MAX_WHATSAPP_CHARS:
        violations.append(
            f"exceeds WhatsApp limit: {len(message)} chars (max {MAX_WHATSAPP_CHARS})"
        )

    return violations


def check_brief_voice(message: str) -> list[str]:
    """Check a weekly brief against voice rules."""
    violations = []

    matches = _BANNED_RE.findall(message)
    if matches:
        violations.extend(
            f"banned phrase: '{m}'" for m in set(matches)
        )

    word_count = len(message.split())
    if word_count > MAX_BRIEF_WORDS:
        violations.append(
            f"too long: {word_count} words (max {MAX_BRIEF_WORDS})"
        )

    if len(message) > MAX_WHATSAPP_CHARS:
        violations.append(
            f"exceeds WhatsApp limit: {len(message)} chars (max {MAX_WHATSAPP_CHARS})"
        )

    return violations


def sanitize_message(message: str) -> str:
    """Remove banned phrases from a message (best-effort cleanup)."""
    cleaned = message
    for phrase in BANNED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    # Clean up double spaces from removals
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n ", "\n", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Scoring function — 7 dimensions, target >= 0.80
# ---------------------------------------------------------------------------
def score_message(message: str, has_action: bool = True,
                  has_evidence: bool = True,
                  has_impact_rupees: bool = True) -> dict:
    """Score a message on 7 quality dimensions.

    Returns dict with dimension scores (0.0-1.0) and overall score.
    Target: overall >= 0.80.

    Dimensions:
      1. voice_clean     — no banned phrases
      2. concise         — under word limit
      3. whatsapp_fit    — under char limit
      4. has_evidence    — contains specific numbers
      5. has_action      — contains actionable recommendation
      6. has_impact      — contains rupee impact
      7. no_hedging      — confident tone, no weasel words
    """
    scores = {}

    # 1. Voice clean (no banned phrases)
    banned_matches = _BANNED_RE.findall(message)
    scores["voice_clean"] = 1.0 if not banned_matches else max(
        0.0, 1.0 - len(set(banned_matches)) * 0.25
    )

    # 2. Concise (word count)
    word_count = len(message.split())
    if word_count <= MAX_FINDING_WORDS:
        scores["concise"] = 1.0
    elif word_count <= MAX_FINDING_WORDS * 1.2:
        scores["concise"] = 0.6
    else:
        scores["concise"] = 0.2

    # 3. WhatsApp fit (char count)
    char_count = len(message)
    if char_count <= MAX_WHATSAPP_CHARS:
        scores["whatsapp_fit"] = 1.0
    elif char_count <= MAX_WHATSAPP_CHARS * 1.1:
        scores["whatsapp_fit"] = 0.5
    else:
        scores["whatsapp_fit"] = 0.0

    # 4. Has evidence (specific numbers in the message)
    number_pattern = re.compile(r"[\d,]+\.?\d*[%₹]?|₹[\d,]+")
    numbers_found = number_pattern.findall(message)
    if has_evidence and len(numbers_found) >= 2:
        scores["has_evidence"] = 1.0
    elif len(numbers_found) >= 1:
        scores["has_evidence"] = 0.6
    else:
        scores["has_evidence"] = 0.2

    # 5. Has action (actionable recommendation)
    action_indicators = [
        "move it", "push", "add", "remove", "reduce", "increase",
        "prep", "order", "stock up", "switch", "list", "feature",
        "promote", "try", "reach out", "call", "text", "consider",
        "this week", "today", "by monday", "by friday", "tomorrow",
    ]
    action_found = any(
        ind.lower() in message.lower() for ind in action_indicators
    )
    scores["has_action"] = 1.0 if (has_action and action_found) else (
        0.6 if action_found else 0.2
    )

    # 6. Has impact (rupee amount)
    has_rupee = bool(re.search(r"₹[\d,]+", message))
    scores["has_impact"] = 1.0 if (has_impact_rupees and has_rupee) else (
        0.6 if has_rupee else 0.2
    )

    # 7. No hedging (confident tone)
    hedge_words = [
        "maybe", "perhaps", "possibly", "might", "could be",
        "it seems", "it appears", "we think",
    ]
    hedge_found = any(h in message.lower() for h in hedge_words)
    scores["no_hedging"] = 0.3 if hedge_found else 1.0

    # Overall: weighted average
    weights = {
        "voice_clean": 0.20,
        "concise": 0.10,
        "whatsapp_fit": 0.10,
        "has_evidence": 0.20,
        "has_action": 0.20,
        "has_impact": 0.15,
        "no_hedging": 0.05,
    }
    overall = sum(scores[k] * weights[k] for k in weights)
    scores["overall"] = round(overall, 3)

    return scores
