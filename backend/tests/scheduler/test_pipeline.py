"""Tests for scheduler/pipeline.py — dependency enforcement,
parallel agents, retry logic."""

import time
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from scheduler.pipeline import (
    PipelineContext,
    run_agents_parallel,
    run_post_agent_pipeline,
    run_daily_pipeline,
    _log_run,
    _retry_etl_step,
    RETRY_BACKOFF_SECONDS,
)


# ---------------------------------------------------------------------------
# Pipeline context
# ---------------------------------------------------------------------------

class TestPipelineContext:
    def test_context_creates_batch_id(self):
        ctx = PipelineContext(restaurant_id=5, run_date=date.today())
        assert ctx.batch_id.startswith("5_")
        assert ctx.etl_ok is True
        assert ctx.agent_findings == []
        assert ctx.approved_findings == []

    def test_context_tracks_errors(self):
        ctx = PipelineContext(restaurant_id=5, run_date=date.today())
        ctx.errors.append("test error")
        assert len(ctx.errors) == 1


# ---------------------------------------------------------------------------
# ETL dependency enforcement
# ---------------------------------------------------------------------------

class TestETLDependencyEnforcement:
    """If ETL fails, agents MUST NOT run."""

    @patch("scheduler.pipeline.SessionLocal")
    @patch("scheduler.pipeline.run_etl_pipeline")
    @patch("scheduler.pipeline.run_agents_parallel")
    @patch("scheduler.pipeline._alert_etl_failure")
    def test_etl_failure_skips_agents(
        self, mock_alert, mock_agents, mock_etl, mock_session
    ):
        """When ETL fails, agents should not be called."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        mock_restaurant = MagicMock()
        mock_restaurant.id = 5
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_restaurant

        # ETL fails
        def etl_side_effect(db, restaurant, target, ctx):
            ctx.etl_ok = False
            ctx.errors.append("etl_orders failed after 3 attempts")
            return False
        mock_etl.side_effect = etl_side_effect

        # Run
        ctx = run_daily_pipeline(restaurant_id=5)

        # Verify: ETL called, agents NOT called
        mock_etl.assert_called_once()
        mock_agents.assert_not_called()
        assert ctx.etl_ok is False
        mock_alert.assert_called_once()

    @patch("scheduler.pipeline.SessionLocal")
    @patch("scheduler.pipeline.run_etl_pipeline")
    @patch("scheduler.pipeline.run_agents_parallel")
    @patch("scheduler.pipeline.run_post_agent_pipeline")
    def test_etl_success_runs_agents(
        self, mock_post, mock_agents, mock_etl, mock_session
    ):
        """When ETL succeeds, agents run."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        mock_restaurant = MagicMock()
        mock_restaurant.id = 5
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_restaurant

        mock_etl.return_value = True
        mock_agents.return_value = []

        ctx = run_daily_pipeline(restaurant_id=5)

        mock_etl.assert_called_once()
        mock_agents.assert_called_once()
        assert ctx.etl_ok is True


# ---------------------------------------------------------------------------
# ETL retry logic
# ---------------------------------------------------------------------------

class TestETLRetry:
    """ETL retries 3x with exponential backoff."""

    @patch("scheduler.pipeline.time.sleep")
    @patch("scheduler.pipeline._log_run")
    def test_retry_succeeds_on_second_attempt(self, mock_log, mock_sleep):
        """ETL step fails once, succeeds on retry."""
        db = MagicMock()
        restaurant = MagicMock()
        ctx = PipelineContext(restaurant_id=5, run_date=date.today())

        call_count = 0

        def flaky_etl(restaurant, db, target_date):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("API timeout")
            return "ok"

        result = _retry_etl_step("etl_orders", flaky_etl, db, restaurant, date.today(), ctx)

        assert result is True
        assert call_count == 2
        mock_sleep.assert_called_once_with(RETRY_BACKOFF_SECONDS[0])

    @patch("scheduler.pipeline.time.sleep")
    @patch("scheduler.pipeline._log_run")
    def test_retry_exhausted_returns_false(self, mock_log, mock_sleep):
        """ETL step fails 3 times — returns False."""
        db = MagicMock()
        restaurant = MagicMock()
        ctx = PipelineContext(restaurant_id=5, run_date=date.today())

        def always_fail(restaurant, db, target_date):
            raise ConnectionError("API down")

        result = _retry_etl_step("etl_orders", always_fail, db, restaurant, date.today(), ctx)

        assert result is False
        assert len(ctx.errors) == 1
        assert "failed after 3 attempts" in ctx.errors[0]
        # 2 sleeps (after attempt 1 and 2, not after attempt 3)
        assert mock_sleep.call_count == 2

    @patch("scheduler.pipeline.time.sleep")
    @patch("scheduler.pipeline._log_run")
    def test_retry_backoff_values(self, mock_log, mock_sleep):
        """Verify exponential backoff: 60s, 180s."""
        db = MagicMock()
        restaurant = MagicMock()
        ctx = PipelineContext(restaurant_id=5, run_date=date.today())

        def always_fail(restaurant, db, target_date):
            raise ConnectionError("down")

        _retry_etl_step("test", always_fail, db, restaurant, date.today(), ctx)

        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [60, 180]


# ---------------------------------------------------------------------------
# Parallel agent execution
# ---------------------------------------------------------------------------

class TestParallelAgents:
    """Agents run in parallel and independent of each other."""

    @patch("scheduler.pipeline.SessionLocal")
    @patch("scheduler.pipeline._log_run")
    def test_agents_run_in_parallel(self, mock_log, mock_session):
        """All 4 agents should start within 5 seconds of each other."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        start_times = []

        class FakeAgent:
            def __init__(self, **kwargs):
                pass

            def run(self, **kwargs):
                start_times.append(time.time())
                time.sleep(0.1)  # Simulate work
                return []

        with patch("scheduler.pipeline.RaviAgent", FakeAgent, create=True), \
             patch("scheduler.pipeline.MayaAgent", FakeAgent, create=True), \
             patch("scheduler.pipeline.ArjunAgent", FakeAgent, create=True), \
             patch("scheduler.pipeline.SaraAgent", FakeAgent, create=True):
            # Patch the imports inside run_agents_parallel
            with patch("intelligence.agents.ravi.RaviAgent", FakeAgent), \
                 patch("intelligence.agents.maya.MayaAgent", FakeAgent), \
                 patch("intelligence.agents.arjun.ArjunAgent", FakeAgent), \
                 patch("intelligence.agents.sara.SaraAgent", FakeAgent):
                ctx = PipelineContext(restaurant_id=5, run_date=date.today())
                run_agents_parallel(5, ctx, ["ravi", "maya", "arjun", "sara"])

        assert len(start_times) == 4
        time_spread = max(start_times) - min(start_times)
        assert time_spread < 5.0, f"Agents didn't start in parallel: spread={time_spread:.2f}s"

    @patch("scheduler.pipeline.SessionLocal")
    @patch("scheduler.pipeline._log_run")
    def test_failed_agent_doesnt_block_others(self, mock_log, mock_session):
        """One agent failing should not prevent others from completing."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        class GoodAgent:
            def __init__(self, **kwargs):
                pass

            def run(self, **kwargs):
                from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
                return [Finding(
                    agent_name="test",
                    restaurant_id=5,
                    category="test",
                    urgency=Urgency.THIS_WEEK,
                    optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                    finding_text="test",
                    action_text="test",
                    evidence_data={},
                    confidence_score=80,
                )]

        class BadAgent:
            def __init__(self, **kwargs):
                raise RuntimeError("Agent init failed")

        with patch("intelligence.agents.ravi.RaviAgent", GoodAgent), \
             patch("intelligence.agents.maya.MayaAgent", BadAgent), \
             patch("intelligence.agents.arjun.ArjunAgent", GoodAgent), \
             patch("intelligence.agents.sara.SaraAgent", GoodAgent):
            ctx = PipelineContext(restaurant_id=5, run_date=date.today())
            findings = run_agents_parallel(5, ctx, ["ravi", "maya", "arjun", "sara"])

        # 3 agents succeeded with 1 finding each, 1 failed
        assert len(findings) == 3


# ---------------------------------------------------------------------------
# Post-agent pipeline: QC → Synthesis → WhatsApp
# ---------------------------------------------------------------------------

class TestPostAgentPipeline:
    """QC runs only after ALL agents complete."""

    @patch("scheduler.pipeline.SessionLocal")
    @patch("scheduler.pipeline._run_quality_council")
    @patch("scheduler.pipeline._run_synthesis_and_send")
    def test_qc_runs_after_agents(self, mock_synth, mock_qc, mock_session):
        """QC is called with all agent findings."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
        findings = [
            Finding(
                agent_name="ravi", restaurant_id=5, category="revenue",
                urgency=Urgency.IMMEDIATE,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text="test", action_text="test",
                evidence_data={}, confidence_score=80,
            ),
        ]
        mock_qc.return_value = findings  # All pass

        ctx = PipelineContext(restaurant_id=5, run_date=date.today())
        approved = run_post_agent_pipeline(5, findings, ctx)

        mock_qc.assert_called_once()
        mock_synth.assert_called_once()
        assert len(approved) == 1

    @patch("scheduler.pipeline.SessionLocal")
    def test_no_findings_skips_qc(self, mock_session):
        """Empty findings list skips QC and Synthesis entirely."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        ctx = PipelineContext(restaurant_id=5, run_date=date.today())
        approved = run_post_agent_pipeline(5, [], ctx)

        assert approved == []


# ---------------------------------------------------------------------------
# Run logging
# ---------------------------------------------------------------------------

class TestRunLogging:
    """agent_run_log populated for every run."""

    def test_log_run_writes_to_db(self):
        """_log_run should add an AgentRunLog entry."""
        mock_db = MagicMock()
        started = datetime.now().astimezone()

        _log_run(
            mock_db, restaurant_id=5, agent_name="ravi",
            started_at=started, status="success",
            findings_count=3, metadata={"batch_id": "test"},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the object added
        log_entry = mock_db.add.call_args[0][0]
        assert log_entry.restaurant_id == 5
        assert log_entry.agent_name == "ravi"
        assert log_entry.status == "success"
        assert log_entry.findings_count == 3


# ---------------------------------------------------------------------------
# Scheduler registration (integration — verifies jobs are registered)
# ---------------------------------------------------------------------------

class TestSchedulerRegistration:
    """Verify APScheduler registers all expected jobs."""

    def test_all_intelligence_jobs_and_cron_schedules(self):
        """start_scheduler() registers Phase 2 intelligence jobs with correct cron schedules."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from etl.scheduler import start_scheduler
        import etl.scheduler as sched_module

        # Use a BackgroundScheduler (doesn't need asyncio loop) for testing
        original = sched_module.scheduler
        test_scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        sched_module.scheduler = test_scheduler
        try:
            start_scheduler()
            jobs = {j.id: j for j in test_scheduler.get_jobs()}

            # --- Job presence ---

            # Phase 2 intelligence jobs
            expected_intelligence_jobs = [
                "daily_intelligence_pipeline",
                "ravi_4h",
                "maya_daily",
                "arjun_scheduled",
                "sara_weekly",
                "priya_daily",
                "priya_deep_scan",
                "weekly_brief_monday",
            ]
            for job_id in expected_intelligence_jobs:
                assert job_id in jobs, f"Missing job: {job_id}"

            # Phase 1 kept jobs
            expected_phase1_jobs = [
                "sync_orders_hourly",
                "daily_reconciliation",
                "daily_digests",
                "weekly_digests",
                "monthly_digests",
                "morning_briefing",
                "weekly_pulse",
            ]
            for job_id in expected_phase1_jobs:
                assert job_id in jobs, f"Missing Phase 1 job: {job_id}"

            # Phase 1 DISABLED jobs should NOT be present
            disabled_jobs = [
                "nightly_cogs",
                "nightly_summary",
                "nightly_insight_cards",
                "nightly_intelligence",
            ]
            for job_id in disabled_jobs:
                assert job_id not in jobs, f"Disabled job still registered: {job_id}"

            # Total job count
            total = len(test_scheduler.get_jobs())
            assert total == 15, f"Expected 15 jobs, got {total}"

            # --- Cron schedule verification ---

            # Daily pipeline: 2am IST
            dp = jobs["daily_intelligence_pipeline"]
            assert str(dp.trigger) == "cron[hour='2', minute='0']"

            # Ravi: 7,11,15,19,23
            ravi = jobs["ravi_4h"]
            assert "7,11,15,19,23" in str(ravi.trigger)

            # Maya: 1am
            maya = jobs["maya_daily"]
            assert "hour='1'" in str(maya.trigger)

            # Arjun: 6,23
            arjun = jobs["arjun_scheduled"]
            assert "6,23" in str(arjun.trigger)

            # Sara: Sunday 1am
            sara = jobs["sara_weekly"]
            assert "sun" in str(sara.trigger)
            assert "hour='1'" in str(sara.trigger)

            # Priya daily: 7:30am
            priya_d = jobs["priya_daily"]
            assert "hour='7'" in str(priya_d.trigger)
            assert "minute='30'" in str(priya_d.trigger)

            # Priya deep: Sunday midnight
            priya_deep = jobs["priya_deep_scan"]
            assert "sun" in str(priya_deep.trigger)
            assert "hour='0'" in str(priya_deep.trigger)

            # Weekly brief: Monday 8am
            brief = jobs["weekly_brief_monday"]
            assert "mon" in str(brief.trigger)
            assert "hour='8'" in str(brief.trigger)

        finally:
            test_scheduler.shutdown(wait=False)
            sched_module.scheduler = original
