"""Daily pipeline orchestrator — ETL → Agents → QC → Synthesis → WhatsApp.

This module contains the pipeline logic. Cron registration lives in etl/scheduler.py.
All jobs open their own DB sessions and close them on exit.

Dependency enforcement:
  - If ANY ETL step fails after 3 retries, agents are SKIPPED for that restaurant
  - If one agent fails, others still run (agents return [] on failure by design)
  - QC runs only after ALL agents in a batch complete
  - Synthesis runs only after QC
  - WhatsApp sends only after Synthesis
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal

logger = logging.getLogger("ytip.pipeline")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RESTAURANT_ID = 5  # YoursTruly — single-tenant for now
MAX_ETL_RETRIES = 3
RETRY_BACKOFF_SECONDS = [60, 180, 540]  # 1min, 3min, 9min


# ---------------------------------------------------------------------------
# Pipeline context — tracks per-restaurant state through the pipeline
# ---------------------------------------------------------------------------
@dataclass
class PipelineContext:
    """Tracks pipeline execution state for a single restaurant."""

    restaurant_id: int
    run_date: date
    batch_id: str = ""
    etl_ok: bool = True
    agent_findings: list = field(default_factory=list)
    approved_findings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def __post_init__(self):
        self.batch_id = f"{self.restaurant_id}_{self.run_date}_{int(time.time())}"


# ---------------------------------------------------------------------------
# Run logging helper
# ---------------------------------------------------------------------------
def _log_run(
    db: Session,
    restaurant_id: int,
    agent_name: str,
    started_at: datetime,
    status: str,
    findings_count: int = 0,
    error_message: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Write a row to agent_run_log."""
    from intelligence.models import AgentRunLog

    ended_at = datetime.now().astimezone()
    log_entry = AgentRunLog(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        run_started_at=started_at,
        run_ended_at=ended_at,
        status=status,
        findings_count=findings_count,
        error_message=(error_message[:1000] if error_message else None),
        run_metadata=metadata or {},
    )
    db.add(log_entry)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to write agent_run_log for %s: %s", agent_name, exc)


# ---------------------------------------------------------------------------
# ETL steps with retry
# ---------------------------------------------------------------------------
def _retry_etl_step(
    step_name: str,
    step_fn,
    db: Session,
    restaurant,
    target_date: date,
    ctx: PipelineContext,
) -> bool:
    """Run an ETL step with up to 3 retries and exponential backoff.

    Returns True on success, False on failure after all retries.
    """
    for attempt in range(MAX_ETL_RETRIES):
        started_at = datetime.now().astimezone()
        try:
            result = step_fn(restaurant, db, target_date)
            db.commit()
            _log_run(db, ctx.restaurant_id, step_name, started_at, "success",
                     metadata={"attempt": attempt + 1, "result": str(result),
                               "batch_id": ctx.batch_id})
            logger.info(
                "[pipeline] %s OK (attempt %d): %s",
                step_name, attempt + 1, result,
            )
            return True
        except Exception as exc:
            db.rollback()
            logger.warning(
                "[pipeline] %s FAILED (attempt %d/%d): %s",
                step_name, attempt + 1, MAX_ETL_RETRIES, exc,
            )
            if attempt < MAX_ETL_RETRIES - 1:
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                logger.info("[pipeline] Retrying %s in %ds", step_name, backoff)
                time.sleep(backoff)
            else:
                error_msg = (
                    f"{step_name} failed after "
                    f"{MAX_ETL_RETRIES} attempts: {exc}"
                )
                ctx.errors.append(error_msg)
                _log_run(db, ctx.restaurant_id, step_name, started_at, "failure",
                         error_message=str(exc),
                         metadata={"attempt": attempt + 1, "batch_id": ctx.batch_id})
                return False


def run_etl_pipeline(
    db: Session, restaurant, target_date: date, ctx: PipelineContext,
) -> bool:
    """Run ETL steps sequentially: orders → inventory → stock → daily_summary.

    Returns True if all succeed, False if any fail after retries.
    On failure, ctx.etl_ok is set to False.
    """
    from ingestion.petpooja_orders import ingest_orders
    from ingestion.petpooja_inventory import ingest_inventory_cogs
    from ingestion.petpooja_stock import ingest_all_outlets
    from compute.daily_summary import compute_daily_summary

    # Step 1: Orders
    if not _retry_etl_step("etl_orders", ingest_orders, db, restaurant, target_date, ctx):
        ctx.etl_ok = False
        return False

    # Step 2: Inventory/COGS
    if not _retry_etl_step("etl_inventory", ingest_inventory_cogs, db, restaurant, target_date, ctx):
        ctx.etl_ok = False
        return False

    # Step 3: Stock (different signature — wraps to match)
    def _stock_wrapper(restaurant, db, target_date):
        return ingest_all_outlets(restaurant.id, db, target_date)

    if not _retry_etl_step("etl_stock", _stock_wrapper, db, restaurant, target_date, ctx):
        ctx.etl_ok = False
        return False

    # Step 4: Daily summary (different signature — wraps to match)
    def _summary_wrapper(restaurant, db, target_date):
        return compute_daily_summary(db, restaurant.id, target_date)

    if not _retry_etl_step("etl_summary", _summary_wrapper, db, restaurant, target_date, ctx):
        ctx.etl_ok = False
        return False

    logger.info("[pipeline] ETL complete for restaurant %d, date %s", ctx.restaurant_id, target_date)
    return True


# ---------------------------------------------------------------------------
# Agent execution — parallel
# ---------------------------------------------------------------------------
def _run_single_agent(
    agent_class,
    agent_name: str,
    restaurant_id: int,
    db: Session,
    rodb: Session,
    batch_id: str,
    **kwargs,
) -> list:
    """Run a single agent, log the run, return findings."""
    started_at = datetime.now().astimezone()
    try:
        agent = agent_class(restaurant_id=restaurant_id, db_session=db, readonly_db=rodb)
        findings = agent.run(**kwargs)
        _log_run(
            db, restaurant_id, agent_name, started_at, "success",
            findings_count=len(findings),
            metadata={"batch_id": batch_id},
        )
        logger.info("[pipeline] Agent %s produced %d findings", agent_name, len(findings))
        return findings
    except Exception as exc:
        _log_run(
            db, restaurant_id, agent_name, started_at, "failure",
            error_message=str(exc),
            metadata={"batch_id": batch_id},
        )
        logger.error("[pipeline] Agent %s failed: %s", agent_name, exc)
        return []


def run_agents_parallel(
    restaurant_id: int,
    ctx: PipelineContext,
    agent_names: Optional[list[str]] = None,
    priya_weekly: bool = False,
) -> list:
    """Run agents in parallel using threads (they're synchronous).

    Default agents for daily pipeline: ravi, maya, arjun, sara.
    Returns combined list of findings from all agents.
    """
    from intelligence.agents.ravi import RaviAgent
    from intelligence.agents.maya import MayaAgent
    from intelligence.agents.arjun import ArjunAgent
    from intelligence.agents.sara import SaraAgent
    from intelligence.agents.priya import PriyaAgent
    from intelligence.agents.kiran import KiranAgent
    from intelligence.agents.chef import ChefAgent

    all_agents = {
        "ravi": (RaviAgent, {}),
        "maya": (MayaAgent, {}),
        "arjun": (ArjunAgent, {}),
        "sara": (SaraAgent, {}),
        "priya": (PriyaAgent, {"weekly": priya_weekly}),
        "kiran": (KiranAgent, {}),
        "chef": (ChefAgent, {}),
    }

    if agent_names is None:
        agent_names = ["ravi", "maya", "arjun", "sara"]

    import concurrent.futures

    all_findings = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_names)) as executor:
        futures = {}
        for name in agent_names:
            if name not in all_agents:
                logger.warning("[pipeline] Unknown agent: %s", name)
                continue
            agent_class, kwargs = all_agents[name]
            # Each thread gets its own DB session
            db = SessionLocal()
            rodb = SessionLocal()
            future = executor.submit(
                _run_single_agent,
                agent_class, name, restaurant_id, db, rodb,
                ctx.batch_id, **kwargs,
            )
            futures[future] = (name, db, rodb)

        for future in concurrent.futures.as_completed(futures):
            name, db, rodb = futures[future]
            try:
                findings = future.result(timeout=300)  # 5 min max per agent
                all_findings.extend(findings)
            except Exception as exc:
                logger.error("[pipeline] Agent %s thread failed: %s", name, exc)
            finally:
                db.close()
                rodb.close()

    ctx.agent_findings = all_findings
    logger.info(
        "[pipeline] All agents complete: %d total findings from %s",
        len(all_findings), agent_names,
    )
    return all_findings


# ---------------------------------------------------------------------------
# Post-agent pipeline: QC → Synthesis → WhatsApp
# ---------------------------------------------------------------------------
def run_post_agent_pipeline(
    restaurant_id: int,
    findings: list,
    ctx: PipelineContext,
) -> list:
    """Run QC → Synthesis → WhatsApp for a batch of findings.

    Returns list of approved findings.
    """
    if not findings:
        logger.info("[pipeline] No findings to process — skipping QC/Synthesis")
        return []

    db = SessionLocal()
    try:
        # --- QC ---
        approved = _run_quality_council(db, restaurant_id, findings, ctx)

        # --- Synthesis + WhatsApp ---
        if approved:
            _run_synthesis_and_send(db, restaurant_id, approved, ctx)

        return approved
    finally:
        db.close()


def _run_quality_council(
    db: Session,
    restaurant_id: int,
    findings: list,
    ctx: PipelineContext,
) -> list:
    """Vet findings through Quality Council. Returns approved findings."""
    from intelligence.quality_council.council import QualityCouncil

    started_at = datetime.now().astimezone()
    try:
        qc = QualityCouncil(db_session=db, readonly_db=db)
        results = qc.vet_batch(findings, restaurant_id=restaurant_id)

        approved = []
        for passed, reason, enriched in results:
            if passed:
                approved.append(enriched)
            else:
                logger.debug("[pipeline] QC rejected: %s — %s", enriched.category, reason)

        ctx.approved_findings = approved
        _log_run(
            db, restaurant_id, "quality_council", started_at, "success",
            findings_count=len(approved),
            metadata={"input_count": len(findings), "batch_id": ctx.batch_id},
        )
        logger.info(
            "[pipeline] QC: %d/%d findings approved",
            len(approved), len(findings),
        )
        return approved
    except Exception as exc:
        _log_run(
            db, restaurant_id, "quality_council", started_at, "failure",
            error_message=str(exc),
            metadata={"batch_id": ctx.batch_id},
        )
        logger.error("[pipeline] QC failed: %s", exc)
        return []


def _run_synthesis_and_send(
    db: Session,
    restaurant_id: int,
    approved_findings: list,
    ctx: PipelineContext,
) -> None:
    """Format approved findings and send via WhatsApp."""
    from intelligence.synthesis.formatter import WhatsAppFormatter

    started_at = datetime.now().astimezone()
    try:
        formatter = WhatsAppFormatter(restaurant_id=restaurant_id, db_session=db)
        result = formatter.format_batch(approved_findings)

        immediate_msg = result.get("immediate")
        if immediate_msg:
            _send_whatsapp(immediate_msg)

        _log_run(
            db, restaurant_id, "synthesis", started_at, "success",
            findings_count=len(approved_findings),
            metadata={
                "immediate_sent": bool(immediate_msg),
                "queued_count": len(result.get("queued", [])),
                "batch_id": ctx.batch_id,
            },
        )
        logger.info(
            "[pipeline] Synthesis: immediate=%s, queued=%d",
            bool(immediate_msg), len(result.get("queued", [])),
        )
    except Exception as exc:
        _log_run(
            db, restaurant_id, "synthesis", started_at, "failure",
            error_message=str(exc),
            metadata={"batch_id": ctx.batch_id},
        )
        logger.error("[pipeline] Synthesis failed: %s", exc)


def _send_whatsapp(message: str, retries: int = 3) -> bool:
    """Send WhatsApp message with retry."""
    from core.config import settings

    owner_phone = getattr(settings, "owner_whatsapp", None)
    if not owner_phone:
        logger.warning("[pipeline] OWNER_WHATSAPP not set — message not sent")
        return False

    for attempt in range(retries):
        try:
            import asyncio
            from services.whatsapp_service import send_text_message

            # Run async send in a new event loop if we're in a sync context
            try:
                loop = asyncio.get_running_loop()
                # We're inside an async context — create a task
                loop.create_task(send_text_message(owner_phone, message))
            except RuntimeError:
                # No running loop — create one
                asyncio.run(send_text_message(owner_phone, message))

            logger.info("[pipeline] WhatsApp sent (attempt %d)", attempt + 1)
            return True
        except Exception as exc:
            logger.warning(
                "[pipeline] WhatsApp send failed (attempt %d/%d): %s",
                attempt + 1, retries, exc,
            )
            if attempt < retries - 1:
                time.sleep(30)

    logger.error("[pipeline] WhatsApp send failed after %d attempts", retries)
    return False


# ---------------------------------------------------------------------------
# Alert — ETL failure notification to Nimish
# ---------------------------------------------------------------------------
def _alert_etl_failure(restaurant_id: int, errors: list[str]) -> None:
    """Alert owner on ETL failure (WhatsApp)."""
    msg = (
        f"*ETL Pipeline Failed*\n\n"
        f"Restaurant ID: {restaurant_id}\n"
        f"Date: {date.today()}\n\n"
        f"Errors:\n" + "\n".join(f"- {e}" for e in errors) +
        "\n\nAgents skipped. Will retry next cycle."
    )
    _send_whatsapp(msg, retries=2)


# ---------------------------------------------------------------------------
# Full daily pipeline (called by cron at 2am IST)
# ---------------------------------------------------------------------------
def run_daily_pipeline(restaurant_id: int = RESTAURANT_ID) -> PipelineContext:
    """Execute the full 2am daily pipeline for a restaurant.

    Sequence: ETL → Agents (parallel) → QC → Synthesis → WhatsApp
    If ETL fails, agents are skipped and owner is alerted.
    """
    yesterday = date.today() - timedelta(days=1)
    ctx = PipelineContext(restaurant_id=restaurant_id, run_date=yesterday)

    logger.info(
        "[pipeline] === Daily pipeline start === restaurant=%d date=%s batch=%s",
        restaurant_id, yesterday, ctx.batch_id,
    )

    db = SessionLocal()
    try:
        from models import Restaurant
        restaurant = db.query(Restaurant).filter_by(id=restaurant_id).first()
        if not restaurant:
            logger.error("[pipeline] Restaurant %d not found", restaurant_id)
            return ctx

        # Step 1-4: ETL
        etl_ok = run_etl_pipeline(db, restaurant, yesterday, ctx)

        if not etl_ok:
            logger.error("[pipeline] ETL failed — skipping agents. Errors: %s", ctx.errors)
            _alert_etl_failure(restaurant_id, ctx.errors)
            return ctx

    finally:
        db.close()

    # Step 5: Run agents in parallel (Ravi, Maya, Arjun, Sara)
    findings = run_agents_parallel(restaurant_id, ctx, ["ravi", "maya", "arjun", "sara"])

    # Step 6-8: QC → Synthesis → WhatsApp
    run_post_agent_pipeline(restaurant_id, findings, ctx)

    logger.info(
        "[pipeline] === Daily pipeline complete === batch=%s findings=%d approved=%d errors=%d",
        ctx.batch_id, len(ctx.agent_findings), len(ctx.approved_findings), len(ctx.errors),
    )
    return ctx


# ---------------------------------------------------------------------------
# Standalone agent run (for individual cron schedules)
# ---------------------------------------------------------------------------
def run_standalone_agent(
    agent_name: str,
    restaurant_id: int = RESTAURANT_ID,
    **kwargs,
) -> list:
    """Run a single agent on its own schedule, then QC → Synthesis → WhatsApp.

    Used for: Ravi 4-hourly, Maya daily, Arjun morning/evening, etc.
    """
    from intelligence.agents.ravi import RaviAgent
    from intelligence.agents.maya import MayaAgent
    from intelligence.agents.arjun import ArjunAgent
    from intelligence.agents.sara import SaraAgent
    from intelligence.agents.priya import PriyaAgent

    agent_map = {
        "ravi": RaviAgent,
        "maya": MayaAgent,
        "arjun": ArjunAgent,
        "sara": SaraAgent,
        "priya": PriyaAgent,
    }

    agent_class = agent_map.get(agent_name)
    if not agent_class:
        logger.error("[pipeline] Unknown agent: %s", agent_name)
        return []

    ctx = PipelineContext(restaurant_id=restaurant_id, run_date=date.today())

    logger.info("[pipeline] Standalone %s run — restaurant=%d", agent_name, restaurant_id)

    db = SessionLocal()
    rodb = SessionLocal()
    try:
        findings = _run_single_agent(
            agent_class, agent_name, restaurant_id, db, rodb,
            ctx.batch_id, **kwargs,
        )
    finally:
        db.close()
        rodb.close()

    # Post-agent: QC → Synthesis → WhatsApp
    if findings:
        run_post_agent_pipeline(restaurant_id, findings, ctx)

    return findings


# ---------------------------------------------------------------------------
# Weekly brief (Monday 8am IST)
# ---------------------------------------------------------------------------
def run_weekly_brief(restaurant_id: int = RESTAURANT_ID) -> Optional[dict]:
    """Generate and send the Monday morning weekly brief."""
    from intelligence.synthesis.weekly_brief import WeeklyBriefGenerator

    logger.info("[pipeline] Weekly brief — restaurant=%d", restaurant_id)

    db = SessionLocal()
    started_at = datetime.now().astimezone()
    try:
        generator = WeeklyBriefGenerator(
            restaurant_id=restaurant_id,
            db_session=db,
            readonly_db=db,
        )
        result = generator.generate()

        msg = result.get("whatsapp_message")
        if msg:
            _send_whatsapp(msg)

        _log_run(
            db, restaurant_id, "weekly_brief", started_at, "success",
            metadata={
                "word_count": result.get("word_count", 0),
                "char_count": result.get("char_count", 0),
                "sections": len(result.get("sections", [])),
            },
        )
        logger.info(
            "[pipeline] Weekly brief sent: %d chars, %d sections",
            result.get("char_count", 0), len(result.get("sections", [])),
        )
        return result
    except Exception as exc:
        _log_run(
            db, restaurant_id, "weekly_brief", started_at, "failure",
            error_message=str(exc),
        )
        logger.error("[pipeline] Weekly brief failed: %s", exc)
        return None
    finally:
        db.close()
