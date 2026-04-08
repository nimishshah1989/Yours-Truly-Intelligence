"""Tests for WhatsApp message formatter — runs against real YoursTruly data.

Connects to production RDS, runs real agents, formats real findings.
Every formatted message must score >= 0.80 on the 7-dimension scale.
"""

import core.models  # noqa: F401 — register Restaurant before intelligence.models

import pytest

from core.database import SessionLocal, SessionReadOnly
from intelligence.agents.base_agent import Finding
from intelligence.synthesis.formatter import WhatsAppFormatter, _format_currency
from intelligence.synthesis.voice import (
    MAX_FINDING_WORDS,
    MAX_WHATSAPP_CHARS,
    check_voice,
    score_message,
)

RESTAURANT_ID = 5  # YoursTruly Cafe


# ---------------------------------------------------------------------------
# Fixtures — real DB sessions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    """Read-write session for the full test module."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def rodb():
    """Read-only session for the full test module."""
    session = SessionReadOnly()
    yield session
    session.close()


@pytest.fixture(scope="module")
def real_findings(db, rodb):
    """Run all 5 agents against real data and collect findings."""
    from intelligence.agents.ravi import RaviAgent
    from intelligence.agents.maya import MayaAgent
    from intelligence.agents.arjun import ArjunAgent
    from intelligence.agents.sara import SaraAgent
    from intelligence.agents.priya import PriyaAgent

    all_findings = []
    for AgentClass in [RaviAgent, MayaAgent, ArjunAgent, SaraAgent, PriyaAgent]:
        try:
            agent = AgentClass(
                restaurant_id=RESTAURANT_ID,
                db_session=db, readonly_db=rodb,
            )
            all_findings.extend(agent.run())
        except Exception:
            pass  # Agents fail silently by design

    return all_findings


@pytest.fixture(scope="module")
def formatter(rodb):
    """WhatsAppFormatter connected to real DB."""
    return WhatsAppFormatter(restaurant_id=RESTAURANT_ID, db_session=rodb)


# ---------------------------------------------------------------------------
# Test: Real findings produce valid messages
# ---------------------------------------------------------------------------

class TestRealFindings:
    """Format real agent findings and verify quality."""

    def test_agents_produce_findings(self, real_findings):
        """At least one agent should produce findings from real data."""
        assert len(real_findings) > 0, (
            "No findings from any agent — check DB has data for restaurant 5"
        )

    def test_every_finding_scores_above_threshold(self, formatter, real_findings):
        """Every real finding must score >= 0.80 overall."""
        for f in real_findings:
            message = formatter.format(f)
            scores = score_message(message)
            assert scores["overall"] >= 0.80, (
                f"[{f.agent_name}] scored {scores['overall']:.3f}. "
                f"Text: {message[:120]}..."
            )

    def test_every_finding_under_word_limit(self, formatter, real_findings):
        for f in real_findings:
            message = formatter.format(f)
            word_count = len(message.split())
            assert word_count <= MAX_FINDING_WORDS, (
                f"[{f.agent_name}] {word_count} words (max {MAX_FINDING_WORDS})"
            )

    def test_every_finding_under_char_limit(self, formatter, real_findings):
        for f in real_findings:
            message = formatter.format(f)
            assert len(message) <= MAX_WHATSAPP_CHARS, (
                f"[{f.agent_name}] {len(message)} chars"
            )

    def test_no_banned_phrases_in_any_finding(self, formatter, real_findings):
        for f in real_findings:
            message = formatter.format(f)
            violations = [
                v for v in check_voice(message) if "banned phrase" in v
            ]
            assert not violations, (
                f"[{f.agent_name}] banned phrases: {violations}"
            )

    def test_no_agent_names_in_any_finding(self, formatter, real_findings):
        agent_names = ["ravi", "maya", "arjun", "sara", "priya", "kiran", "chef"]
        for f in real_findings:
            message = formatter.format(f).lower()
            for name in agent_names:
                assert name not in message, (
                    f"Agent name '{name}' leaked in [{f.agent_name}] message"
                )

    def test_every_finding_has_action_section(self, formatter, real_findings):
        for f in real_findings:
            message = formatter.format(f)
            assert "*Action:*" in message, (
                f"[{f.agent_name}] missing Action section"
            )


class TestRealBatching:
    """Batching logic with real findings."""

    def test_batch_returns_immediate(self, formatter, real_findings):
        if not real_findings:
            pytest.skip("No real findings available")
        batch = formatter.format_batch(real_findings)
        assert batch["immediate"] is not None
        assert "*Action:*" in batch["immediate"]

    def test_batch_queues_remaining(self, formatter, real_findings):
        if len(real_findings) < 2:
            pytest.skip("Need 2+ findings for queue test")
        batch = formatter.format_batch(real_findings)
        assert len(batch["queued"]) == len(real_findings) - 1


class TestCurrencyFormatting:
    """Indian number formatting — no mocks needed."""

    def test_small_amount(self):
        assert _format_currency(15000) == "₹150"

    def test_lakhs(self):
        result = _format_currency(100000_00)
        assert "L" in result

    def test_crores(self):
        result = _format_currency(10_000_000_00)
        assert "Cr" in result

    def test_rupee_symbol_always_present(self):
        for paisa in [100, 5000, 100000, 5000000, 100000000]:
            assert "₹" in _format_currency(paisa)
