# ============================================================================
# MODIFICATIONS TO: backend/agent/system_prompt.py
# ============================================================================
# 
# The existing build_system_prompt() function assembles schema + café context.
# We need to ADD intelligence context: recent findings + conversation memory.
#
# CHANGE 1: Add this import at the top of the file
# ----------------------------------------------------------------------------

from models import IntelligenceFinding, InsightsJournal, ConversationMemory
from database import SessionLocal

# CHANGE 2: Add this function BEFORE build_system_prompt()
# ----------------------------------------------------------------------------

def _get_intelligence_context(restaurant_id: int) -> str:
    """Fetch recent intelligence findings + conversation memory for prompt injection."""
    db = SessionLocal()
    try:
        # Last 10 intelligence findings (most recent, highest severity first)
        findings = (
            db.query(IntelligenceFinding)
            .filter(IntelligenceFinding.restaurant_id == restaurant_id)
            .order_by(
                IntelligenceFinding.finding_date.desc(),
                IntelligenceFinding.severity.desc(),
            )
            .limit(10)
            .all()
        )

        # Last 3 insights journal entries
        journal = (
            db.query(InsightsJournal)
            .filter(InsightsJournal.restaurant_id == restaurant_id)
            .order_by(InsightsJournal.created_at.desc())
            .limit(3)
            .all()
        )

        # Last 10 conversation memory entries
        memories = (
            db.query(ConversationMemory)
            .filter(ConversationMemory.restaurant_id == restaurant_id)
            .order_by(ConversationMemory.created_at.desc())
            .limit(10)
            .all()
        )

        parts = []

        if findings:
            parts.append("RECENT INTELLIGENCE FINDINGS (from automated pattern detection):")
            for f in findings:
                impact = ""
                if f.rupee_impact:
                    impact = f" [Est. annual impact: ₹{f.rupee_impact // 100:,}]"
                parts.append(f"  [{f.severity.upper()}] {f.finding_date}: {f.title}{impact}")

        if journal:
            parts.append("\nWEEKLY ANALYSIS OBSERVATIONS (from Claude batch analysis):")
            for j in journal:
                parts.append(f"  Week of {j.week_start}: {j.observation_text[:300]}")
                if j.suggested_action:
                    parts.append(f"    → Suggested: {j.suggested_action[:200]}")

        if memories:
            parts.append("\nRECENT OWNER INTERACTIONS (what the owner has been asking about):")
            for m in memories:
                cat = f" [{m.query_category}]" if m.query_category else ""
                parts.append(f"  {m.created_at.strftime('%b %d')}{cat}: {m.query_text[:150]}")

        if parts:
            return "\n".join(parts)
        return ""

    except Exception as exc:
        # Don't break the agent if intelligence tables don't exist yet
        return ""
    finally:
        db.close()


# CHANGE 3: In the existing build_system_prompt() function, ADD this block
# right before the final return statement, appending to the system prompt string:
# ----------------------------------------------------------------------------
#
#   intelligence_context = _get_intelligence_context(restaurant_id)
#   if intelligence_context:
#       system_prompt += f"""
#
#   --- ACCUMULATED INTELLIGENCE (use this to give more specific, contextual answers) ---
#
#   {intelligence_context}
#
#   When answering, reference these findings where relevant. If the owner asks about
#   something you have intelligence on, lead with the specific finding rather than
#   querying from scratch. Connect dots across findings when possible.
#   """
#
# ============================================================================


# ============================================================================
# MODIFICATIONS TO: backend/routers/chat.py
# ============================================================================
#
# After the agent returns a response, log the interaction to conversation_memory.
#
# CHANGE 1: Add import
# ----------------------------------------------------------------------------

from models import ConversationMemory

# CHANGE 2: After the agent call returns (text_response, widgets), add:
# ----------------------------------------------------------------------------
#
#   # Log to conversation memory
#   try:
#       memory = ConversationMemory(
#           restaurant_id=restaurant_id,
#           channel="web",
#           query_text=message,
#           response_summary=text_response[:500],  # truncate for storage
#           query_category=_categorize_query(message),  # simple keyword classifier
#           owner_engaged=False,  # updated if follow-up question comes
#       )
#       db.add(memory)
#       db.commit()
#   except Exception:
#       pass  # never break chat for memory logging failure

# CHANGE 3: Add this helper function
# ----------------------------------------------------------------------------

def _categorize_query(query: str) -> str:
    """Simple keyword-based query categorization."""
    q = query.lower()
    if any(w in q for w in ["food cost", "cogs", "ingredient", "portion", "recipe", "consumption"]):
        return "food_cost"
    if any(w in q for w in ["menu", "item", "dish", "star", "dog", "margin"]):
        return "menu"
    if any(w in q for w in ["zomato", "swiggy", "channel", "delivery", "commission", "aggregator"]):
        return "channel"
    if any(w in q for w in ["vendor", "purchase", "supplier", "price"]):
        return "vendor"
    if any(w in q for w in ["staff", "labor", "employee", "shift"]):
        return "staffing"
    if any(w in q for w in ["revenue", "sales", "order", "ticket"]):
        return "revenue"
    return "general"


# ============================================================================
# MODIFICATIONS TO: backend/routers/home.py
# ============================================================================
#
# Add "money_found" to the executive summary response.
#
# Somewhere in the home endpoint, add a query:
#
#   money_found = (
#       db.query(func.sum(IntelligenceFinding.rupee_impact))
#       .filter(
#           IntelligenceFinding.restaurant_id == restaurant_id,
#           IntelligenceFinding.rupee_impact.isnot(None),
#       )
#       .scalar()
#   ) or 0
#
#   # Add to response:
#   "money_found_paisa": money_found,
#   "money_found_display": f"₹{money_found // 100:,}",
#
# ============================================================================
