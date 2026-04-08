"""Tests for weekly brief generator — runs against real YoursTruly data.

Connects to production RDS, generates a real weekly brief for restaurant 5.
Must have sections, under 500 words, under 4096 chars, no banned phrases.
"""

import core.models  # noqa: F401 — register Restaurant before intelligence.models

import pytest

from core.database import SessionLocal, SessionReadOnly
from intelligence.synthesis.voice import (
    MAX_BRIEF_WORDS,
    MAX_WHATSAPP_CHARS,
    check_brief_voice,
    score_message,
)
from intelligence.synthesis.weekly_brief import WeeklyBriefGenerator

RESTAURANT_ID = 5  # YoursTruly Cafe


# ---------------------------------------------------------------------------
# Fixtures — real DB sessions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def rodb():
    session = SessionReadOnly()
    yield session
    session.close()


@pytest.fixture(scope="module")
def generator(db, rodb):
    return WeeklyBriefGenerator(
        restaurant_id=RESTAURANT_ID,
        db_session=db,
        readonly_db=rodb,
    )


@pytest.fixture(scope="module")
def brief(generator):
    """Generate a real weekly brief from production data."""
    return generator.generate()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWeeklyBriefGeneration:
    """Weekly brief generated from real order data."""

    def test_generates_message(self, brief):
        assert "whatsapp_message" in brief
        assert len(brief["whatsapp_message"]) > 0

    def test_contains_rupee_amounts(self, brief):
        msg = brief["whatsapp_message"]
        assert "₹" in msg, "Brief must contain real rupee amounts"

    def test_has_sections(self, brief):
        assert len(brief["sections"]) >= 2  # performance + hook minimum

    def test_has_conversation_hook(self, brief):
        msg = brief["whatsapp_message"]
        assert "reply" in msg.lower() or "voice note" in msg.lower()

    def test_contains_real_revenue(self, brief):
        """Brief should have actual revenue numbers, not zeros."""
        msg = brief["whatsapp_message"]
        # The performance section should show non-trivial revenue
        assert "₹0" not in msg or "₹0." not in msg, (
            "Brief shows zero revenue — data may be missing"
        )


class TestWeeklyBriefVoice:
    """Voice consistency for real weekly brief."""

    def test_no_banned_phrases(self, brief):
        violations = check_brief_voice(brief["whatsapp_message"])
        voice_violations = [v for v in violations if "banned phrase" in v]
        assert not voice_violations, f"Banned phrases: {voice_violations}"

    def test_no_agent_names(self, brief):
        msg = brief["whatsapp_message"].lower()
        for name in ["ravi", "maya", "arjun", "sara", "priya", "kiran"]:
            assert name not in msg, f"Agent name '{name}' leaked into brief"

    def test_no_system_internals(self, brief):
        msg = brief["whatsapp_message"].lower()
        for phrase in ["quality council", "significance", "corroboration",
                       "our ai", "the algorithm"]:
            assert phrase not in msg, f"System internal '{phrase}' in brief"


class TestWeeklyBriefLimits:
    """Word and character limits for real brief."""

    def test_under_word_limit(self, brief):
        assert brief["word_count"] <= MAX_BRIEF_WORDS, (
            f"Brief is {brief['word_count']} words (max {MAX_BRIEF_WORDS})"
        )

    def test_under_char_limit(self, brief):
        assert brief["char_count"] <= MAX_WHATSAPP_CHARS, (
            f"Brief is {brief['char_count']} chars (max {MAX_WHATSAPP_CHARS})"
        )


class TestWeeklyBriefScoring:
    """Quality scoring on real brief."""

    def test_voice_clean(self, brief):
        scores = score_message(brief["whatsapp_message"])
        assert scores["voice_clean"] >= 0.8

    def test_has_evidence(self, brief):
        scores = score_message(brief["whatsapp_message"])
        assert scores["has_evidence"] >= 0.6, (
            "Brief must contain specific numbers from real data"
        )


class TestWeeklyBriefSectionBuilders:
    """Test section builders with real DB data."""

    def test_performance_section_from_real_data(self, generator, rodb):
        """Performance section should pull real week metrics."""
        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)
        week_start = yesterday - timedelta(days=6)

        this_week = generator._get_week_metrics(week_start, yesterday)
        assert this_week["orders"] > 0, (
            "No orders found for last week — check DB data"
        )
        assert this_week["revenue"] > 0, (
            "Zero revenue for last week — check DB data"
        )

    def test_hook_section_always_present(self, generator):
        section = generator._section_hook()
        body = section["body"].lower()
        assert "reply" in body or "voice" in body
