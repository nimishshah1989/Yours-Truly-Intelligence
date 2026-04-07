# YTIP — Production PRD v1.0

> **The single source of truth for Phase 2 build.**
> Read CLAUDE.md every session. Read THIS document for the module you're building.
> Every AI module is defined by: Story (why) + Eval (golden examples + scoring) + Flywheel (how it gets smarter).
> Every non-AI module is defined by: Story + Acceptance Criteria (deterministic pass/fail).
> **Before writing code for any phase, read that phase's section fully. Your code must pass the evals before moving to the next phase.**

---

## SECTION 0: What Already Exists — Do Not Rebuild

### The Restaurant

**YoursTruly Coffee Roaster** — specialty coffee + all-day brunch café in Kolkata. Owner: Piyush Kankaria. PetPooja outlet ID: 407585. This is NOT a traditional Indian restaurant. It's a modern café serving espresso drinks, avocado toast, eggs benedict, croissants, and tiramisu. The customer base is urban, educated, Instagram-friendly, 22-40 age range. Peak hours: Saturday-Sunday brunch (10am-1pm) and weekday evening coffee (5-8pm).

### The Menu (from PetPooja — 40 items)

| Item | Category | Price | Cost | CM% | Notes |
|------|----------|-------|------|-----|-------|
| Cold Brew | Coffee | ₹300 | ₹55 | 81.7% | Highest margin beverage |
| Chai Latte | Specialty | ₹240 | ₹50 | 79.2% | |
| Iced Latte | Coffee | ₹300 | ₹65 | 78.3% | Variant of "Latte" concept |
| Americano | Coffee | ₹220 | ₹50 | 77.3% | |
| Cappuccino | Coffee | ₹260 | ₹60 | 76.9% | High volume staple |
| Latte | Coffee | ₹280 | ₹65 | 76.8% | #1 seller, variant parent |
| Espresso | Coffee | ₹180 | ₹45 | 75.0% | |
| Mocha | Coffee | ₹320 | ₹80 | 75.0% | |
| Hot Chocolate | Specialty | ₹280 | ₹70 | 75.0% | |
| Matcha Latte | Specialty | ₹340 | ₹90 | 73.5% | Trendy, niche |
| Granola Bowl | Breakfast | ₹300 | ₹80 | 73.3% | |
| Brownie | Desserts | ₹220 | ₹60 | 72.7% | |
| Pancakes | Breakfast | ₹360 | ₹100 | 72.2% | Weekend brunch staple |
| Croissant | Bakery | ₹180 | ₹50 | 72.2% | |
| Tiramisu | Desserts | ₹360 | ₹100 | 72.2% | |
| French Toast | Breakfast | ₹340 | ₹95 | 72.1% | |
| Cheesecake | Desserts | ₹320 | ₹95 | 70.3% | |
| Club Sandwich | Sandwiches | ₹320 | ₹100 | 68.8% | |
| Avocado Toast | Sandwiches | ₹380 | ₹120 | 68.4% | Identity item — Instagram star |
| Quinoa Bowl | Salads | ₹400 | ₹130 | 67.5% | |
| Eggs Benedict | Breakfast | ₹420 | ₹140 | 66.7% | Lowest CM%, perishable, high waste risk |

**Key inventory:** Coffee Beans (kg), Milk (litre), Cream (litre), Eggs (dozen), Butter (kg), Flour (kg), Cheese (kg), Chocolate (kg), Avocado (kg)

**Menu graph patterns:** Latte + Iced Latte → concept "Latte" with hot/iced variants. Possible modifiers: Extra Shot, Oat Milk, Almond Milk (if they exist in PetPooja as ₹0 or addon items).

### The Codebase at a Glance

| Layer | Lines | Key Fact |
|-------|-------|----------|
| Backend Python | ~24,000 | 20 routers, 15+ services, Claude chat agent, full PetPooja ETL |
| Frontend TypeScript | ~7,000 | 12 pages, 12 widget types, SWR hooks, mobile-first PWA |
| Database SQL | ~2,000 | 4 schema files (DO NOT modify schema.sql/v2/v3), 43+ tables |
| Intelligence layer | ~2,900 | BaseAgent, Ravi, Maya, MenuGraph builder/query/validator, 12 ORM models |
| Tests | ~750 | conftest with SQLite adapter, tests for Ravi, Maya, menu graph |

### Intelligence Layer — Built vs Stub

| Component | Status | File(s) | Lines |
|-----------|--------|---------|-------|
| BaseAgent | ✅ BUILT | `intelligence/agents/base_agent.py` | 180 |
| Finding dataclass | ✅ BUILT | In base_agent.py | — |
| Ravi (Revenue) | ✅ BUILT | `intelligence/agents/ravi.py` | 683 |
| Maya (Menu/Margin) | ✅ BUILT | `intelligence/agents/maya.py` | 470 |
| MenuGraphBuilder | ✅ BUILT | `intelligence/menu_graph/graph_builder.py` | 474 |
| MenuGraphQuery | ✅ BUILT | `intelligence/menu_graph/semantic_query.py` | 245 |
| MenuGraphValidator | ✅ BUILT | `intelligence/menu_graph/validator.py` | 134 |
| Intelligence ORM models | ✅ BUILT | `intelligence/models.py` | 473 |
| schema_v4.sql | ✅ BUILT | `database/schema_v4.sql` | 322 |
| Arjun (Stock/Waste) | 🔴 NOT BUILT | — | — |
| Sara (Customer) | 🔴 NOT BUILT | — | — |
| Priya (Cultural/Calendar) | 🔴 NOT BUILT | — | — |
| Kiran (Competition) | 🔴 NOT BUILT | — | Post-MVP |
| Chef (Innovation) | 🔴 NOT BUILT | — | Post-MVP |
| Quality Council | 🔴 STUB | `intelligence/quality_council/__init__.py` | 0 |
| Synthesis | 🔴 STUB | `intelligence/synthesis/__init__.py` | 0 |
| Customer Resolution | 🔴 STUB | `intelligence/customer_resolution/__init__.py` | 0 |
| Knowledge Base | 🔴 STUB | `intelligence/knowledge_base/__init__.py` | 0 |
| Agent Scheduler | ⚠️ CLI ONLY | `scheduler/agent_scheduler.py` | Needs rewrite to APScheduler |

### PetPooja API Behaviour — Memorise Every Session

1. **T-1 lag**: Pass D+1 to get day D data. Agents must never assume intraday data exists.
2. **Response key**: `order_json` NOT `orders`
3. **consumed[].price is PER-UNIT**: Total = rawmaterialquantity × price.
4. **Purchase API**: DD-MM-YYYY format, max 1-month range, needs both cookies.
5. **Pagination**: 50 records per page, loop via refId.
6. **Menu API headers**: Hyphenated (`app-key`) not underscored (`app_key`).
7. **Item classification**: prepared (2+ rawmaterials) / retail (0-1) / addon. All food metrics filter `classification = 'prepared'`.

---

## SECTION 1: The Eval Framework — How to Read This Document

### Why Evals, Not Just Prose

Traditional PRD: *"Arjun watches the supply chain and catches waste."*
Result: Claude Code builds something that says "consider reviewing your prep quantities." Useless.

Eval-driven PRD: *"Here's what Arjun sees: Eggs Benedict prepped 25 portions every Saturday at YoursTruly, sold 8 on average. Here's exactly what the finding should look like: 'Reduce Saturday Eggs Benedict prep to 12 portions. Saves ₹1,680/week.' Score >= 0.75 on 4 quality dimensions or it doesn't ship."*
Result: Claude Code has an objective target grounded in real YoursTruly data.

### Three Layers (for every AI module)

**Layer 1 — The Story:** Why this module exists. What Piyush experiences. What failure looks like.

**Layer 2 — The Eval:** Golden input/output pairs using real YoursTruly menu items and scenarios. Scoring function. Quality bar.

**Layer 3 — The Flywheel Hook:** What gets logged. What threshold adjusts. How the module gets smarter over time. Ships with the module, not bolted on later.

### For Non-AI Modules

Layer 1 (Story) + Acceptance Criteria (deterministic pass/fail).

---

## SECTION 2: Build Sequence

```
Phase A: Arjun, Sara, Priya agents                    ← 3 remaining MVP agents
Phase B: Quality Council (3-stage gate)                ← Nothing reaches Piyush without this
Phase C: Synthesis + Weekly Brief + Message Batching   ← WhatsApp delivery layer
Phase D: WhatsApp Onboarding State Machine             ← Profile capture + menu graph bootstrap
Phase E: Agent Scheduler + Orchestration Pipeline      ← 2am daily pipeline, Monday 8am brief
Phase F: Knowledge Base (pgvector RAG)                 ← Research-backed agent reasoning
Phase G: Customer Identity Resolution                  ← Deduplicated customer view for Sara
Phase H: Kiran + Chef agents                           ← Competition + Innovation (post-MVP)
Phase I: External Data Feeds                           ← APMC, IMD, Google Places (post-MVP)
```

**MVP = Phases A through E running on live YoursTruly PetPooja data.**
**The MVP test**: Show the first Monday brief to Piyush. If he says "how did you know that?" or "I need to act on this" — success. If he says "yeah I knew all this" — failure.

### Dependencies

```
A (agents) ← depends on nothing new; BaseAgent + schema_v4 exist
B (QC) ← depends on A (needs findings to vet)
C (synthesis) ← depends on B (only formats QC-passed findings)
D (onboarding) ← independent; can build in parallel with A-C
E (scheduler) ← depends on A+B+C (orchestrates full pipeline)
F (knowledge base) ← independent; agents work without it
G (customer resolution) ← Sara works without it on raw data
```

---

## PHASE A: Remaining MVP Agents

---

### PHASE-A1: Arjun — Stock & Waste Sentinel

**File:** `backend/intelligence/agents/arjun.py`
**Inherits:** `BaseAgent`
**Schedule:** 6am IST (morning prep) + 11pm IST (evening close)
**Max findings per run:** 2

#### Layer 1 — The Story

YoursTruly is a café. The waste profile is completely different from a traditional restaurant. The high-risk items are: Eggs Benedict (₹140 cost, prepped with poached eggs and hollandaise — both perishable and can't be held), fresh baked goods (Croissants, Banana Bread, Scones — baked in the morning, stale by next day), and milk-based drinks (Milk is the #1 inventory item by volume, with limited shelf life once opened).

Arjun's morning prep recommendation tells the kitchen: how many Eggs Benedict portions to prep for brunch, how many croissants to bake, how much milk to have ready. These are decisions that happen at 6am before service — and getting them wrong means either wasted food or angry customers who can't get their order.

The evening analysis is simpler: what actually sold today vs. what was prepped? Over 4 Saturdays, if Eggs Benedict is consistently prepped at 25 and sells 8, that's ₹2,380/week literally in the bin.

Arjun also watches coffee bean and milk procurement. Specialty coffee beans are YoursTruly's identity — a price spike hits every drink on the menu. Milk cost directly affects Latte (₹65 cost), Cappuccino (₹60), Mocha (₹80), and all specialty drinks.

**Failure mode:** "Your food cost seems high" — that's what PetPooja reports already say.
**Success mode:** "Reduce Saturday Eggs Benedict prep from 25 to 12. You've wasted 68% for 4 weeks straight — that's ₹2,380 gone. Your Saturday brunch regulars finish ordering by 1pm, and you've never sold more than 14."

#### Layer 2 — The Eval

**Golden Example 1: Saturday Brunch Prep Recommendation**

```
INPUT:
  restaurant_id: 5
  run_time: 6:00 AM IST, Saturday
  weather_signal: { forecast: "clear", confidence: 0.85 }
  last_4_saturdays: {
    "Eggs Benedict": { orders: [12, 14, 10, 13], avg: 12.25 },
    "Pancakes": { orders: [18, 22, 20, 19], avg: 19.75 },
    "French Toast": { orders: [15, 12, 14, 16], avg: 14.25 },
    "Croissant": { orders: [30, 35, 28, 32], avg: 31.25 },
    "Avocado Toast": { orders: [20, 24, 22, 18], avg: 21.0 }
  }
  cultural_events_next_48h: []
  week_of_month: 1 (salary week)
  profile.has_delivery: True (Swiggy + Zomato)

EXPECTED FINDING:
  agent_name: "arjun"
  category: "stock"
  urgency: "immediate"
  finding_text: "Saturday brunch prep targets based on 4-week pattern. 
                Salary week — expect slight premium uplift."
  action_text: "Saturday prep targets:
                • Eggs Benedict: 15 portions (4-wk avg 12 + salary week buffer)
                • Pancakes: 24 portions (4-wk avg 20 + Saturday peak demand)
                • French Toast: 17 portions (4-wk avg 14 + small buffer)
                • Croissants: 35 (4-wk avg 31 — bake early, these sell out by noon)
                • Avocado Toast: 24 (4-wk avg 21 + salary week uplift on premium items)
                Note: Ensure extra milk stocked — Saturday Latte volume runs 40% above weekday."
  confidence_score: 78
  evidence_data: {
    "day_of_week": "Saturday",
    "weather": "clear",
    "week_of_month": 1,
    "items_adjusted": 5,
    "data_points_count": 4,
    "deviation_pct": 0.15
  }
```

**Golden Example 2: Eggs Benedict Waste Pattern**

```
INPUT:
  item: "Eggs Benedict"
  prep_last_4_saturdays: [25, 25, 25, 25]
  sold_last_4_saturdays: [12, 14, 10, 13]
  waste_pct: 0.51 (51% wasted)
  cost_per_portion_paisa: 14000 (₹140 cost per portion)
  weekly_waste_cost_paisa: 178500  (avg 12.75 wasted × ₹140)
  profile.non_negotiables: ["Never compromise on coffee bean quality", "Always use organic milk"]

EXPECTED FINDING:
  agent_name: "arjun"
  category: "stock"
  urgency: "this_week"
  optimization_impact: "margin_improvement"
  finding_text: "Eggs Benedict: prepping 25 every Saturday, average sale is 12. 
                51% waste rate — 13 portions discarded weekly. That's hollandaise, 
                eggs, and English muffins going straight to waste.
                Cost: ₹1,785/week (₹7,700/month)."
  action_text: "Reduce Saturday Eggs Benedict prep to 16 portions (avg 12 + 30% buffer). 
                Hollandaise has a 2-hour window — prep in two batches (10 at open, 6 at 11:30am) 
                instead of all at once. Saves ₹1,260/week (₹5,400/month). 
                If you sell out by 1pm two Saturdays in a row, bump to 18."
  estimated_impact_paisa: 126000
  evidence_data: {
    "item": "Eggs Benedict",
    "prep_qty": 25,
    "avg_sold": 12.25,
    "waste_ratio": 0.51,
    "weeks_observed": 4,
    "data_points_count": 4,
    "deviation_pct": 0.51,
    "cost_per_portion_paisa": 14000
  }
```

**Golden Example 3: Milk Cost Spike**

```
INPUT:
  external_signal: { signal_type: "apmc_price", signal_key: "milk_kolkata",
                     signal_data: { price_today_per_litre: 7200, price_7d_ago: 5800, change_pct: 0.241 },
                     signal_date: "2026-04-05" }
  menu_items_using_milk: ["Latte", "Iced Latte", "Cappuccino", "Mocha", "Matcha Latte", 
                          "Chai Latte", "Hot Chocolate", "Pancakes", "French Toast"]
  estimated_weekly_milk_consumption_litres: 80
  
EXPECTED FINDING:
  finding_text: "Milk price up 24% in Kolkata this week (₹72/litre vs ₹58 last week). 
                This hits 9 menu items — every coffee drink plus pancakes and french toast. 
                At 80 litres/week, your weekly milk bill just went up by ₹1,120."
  action_text: "This affects your biggest category. Three options:
                1. Absorb short-term — milk price spikes in April are often seasonal and 
                   correct within 2-3 weeks. Check before changing pricing.
                2. If it holds 3+ weeks, a ₹10 increase on Latte/Cappuccino/Mocha covers it 
                   (customers are least price-sensitive on coffee).
                3. Review if your dairy supplier is passing through wholesale increases fairly — 
                   compare with local dairy rates.
                Do NOT switch to non-organic milk — that's a non-negotiable for your brand."
  urgency: "this_week"
  confidence_score: 70
```

Note the last line — Arjun reads the non_negotiables and proactively avoids recommending against them.

**Scoring Function:**

```python
def score_arjun_finding(finding: Finding) -> float:
    score = 0.0
    import re
    
    # 1. Specificity: contains actual portion numbers or Rs amounts — 0.25
    numbers_in_action = len(re.findall(r'\d+', finding.action_text))
    if numbers_in_action >= 3:
        score += 0.25
    elif numbers_in_action >= 1:
        score += 0.10
    
    # 2. Grounded in history: evidence has >= 3 data points — 0.25
    if finding.evidence_data.get("data_points_count", 0) >= 3:
        score += 0.25
    
    # 3. Has ₹ impact estimate — 0.25
    if finding.estimated_impact_paisa and finding.estimated_impact_paisa > 0:
        score += 0.25
    
    # 4. Action is operationally specific to a café kitchen — 0.25
    cafe_ops = ["prep", "reduce", "batch", "bake", "stock", "milk", "portions", 
                "litres", "kg", "order", "supplier"]
    if any(verb in finding.action_text.lower() for verb in cafe_ops):
        score += 0.25
    
    return score
```

**Quality Bar:** >= 0.75 on all 3 golden examples.

#### Layer 3 — The Flywheel Hook

**Signal capture:**
- Morning prep recommendation → log per-item targets in `agent_findings.evidence_data`
- End-of-day: compare actual orders (from daily ETL) vs morning targets per item
- Store accuracy in `agent_run_log.run_metadata`: `{"prep_accuracy": {"Eggs Benedict": 0.81, "Croissant": 0.91}}`

**Threshold adjustment:**
- Item prep accuracy consistently > 0.85 for 4 weeks → boost confidence for that item
- Item prep accuracy < 0.60 for 3 weeks → flag: is a new pattern emerging (new menu promotion, seasonal shift)?
- Owner responds "we already cut Eggs Benedict prep" → mark `owner_acted = true`, learn the new prep baseline

**What Arjun never does:**
- Recommends cheaper coffee beans or non-organic milk (non_negotiables)
- Sends prep recommendations without >= 3 weeks of same-DOW data
- Returns > 2 findings per run
- Assumes intraday data exists

---

### PHASE-A2: Sara — Customer Intelligence

**File:** `backend/intelligence/agents/sara.py`
**Inherits:** `BaseAgent`
**Schedule:** Weekly — Sunday 1:00 AM IST
**Max findings per run:** 2

#### Layer 1 — The Story

YoursTruly's customer base has a distinct pattern. The high-value regulars are the Saturday/Sunday brunch crowd — they come for Eggs Benedict, Avocado Toast, and specialty coffee. They're creatures of habit: same table, same order, tip well, post on Instagram. When one of them stops coming, it matters — a lot more than losing a random Swiggy delivery customer.

The Swiggy/Zomato delivery customers are a different segment. Higher volume, lower loyalty, attracted by discounts. Sara needs to distinguish between these segments and focus Piyush's attention on the regulars worth fighting for.

Sara's limitation with YoursTruly: 50% of orders are dine-in direct (from seed data platform weights), many paid via UPI with phone number captured. Swiggy/Zomato orders have customer data. But pure walk-in cash customers may be anonymous. Sara must state her data coverage.

#### Layer 2 — The Eval

**Golden Example 1: Lapsed Brunch Regular**

```
INPUT:
  customer: "Ananya S" (phone: 919830456789)
  visits: [Jan 11 Sat, Jan 18 Sat, Jan 25 Sat, Feb 8 Sat, Feb 15 Sat, Mar 1 Sat]
  last_visit: Mar 1 (37 days ago as of Apr 7)
  avg_spend_paisa: 112000 (₹1,120 — typically orders Eggs Benedict + Latte + Brownie)
  total_spend_paisa: 672000 (₹6,720 over 6 visits)
  top_items: ["Eggs Benedict", "Latte", "Brownie"]
  pattern: Saturday brunch, 11am arrival, always dine-in, table T4

EXPECTED FINDING:
  finding_text: "Ananya S — a Saturday brunch regular (6 visits, ₹1,120 avg spend) — 
                hasn't been in since March 1. That's 37 days — she used to come every 
                Saturday. Orders: Eggs Benedict, Latte, Brownie. Always sits at T4. 
                Lifetime: ₹6,720."
  action_text: "Ananya was your textbook Saturday regular — same day, same table, same order. 
                37 days of absence breaks the weekly habit loop. After 60 days, recovery 
                drops below 15%. A personal touch works: 'Hey Ananya, we've got a new 
                single-origin pour-over this Saturday — your usual table is waiting.' 
                This isn't a discount play — it's a relationship play."
  urgency: "this_week"
  confidence_score: 82
  estimated_impact_paisa: 112000
  evidence_data: {
    "customer_name": "Ananya S",
    "visit_count": 6,
    "days_since_last": 37,
    "avg_frequency_days": 8,
    "avg_spend_paisa": 112000,
    "lifetime_spend_paisa": 672000,
    "top_items": ["Eggs Benedict", "Latte", "Brownie"],
    "pattern": "Saturday brunch",
    "data_points_count": 6
  }
```

**Golden Example 2: First-Visit Conversion Rate Drop**

```
INPUT:
  cohort_analysis:
    Feb 2026: { first_timers: 38, returned_within_30d: 14, conversion: 0.368 }
    Mar 2026: { first_timers: 45, returned_within_30d: 9, conversion: 0.200 }
  8_week_baseline_conversion: 0.33
  march_notable: New staff member started March 5. Average fulfillment time increased 
                 from 12min to 18min in March.

EXPECTED FINDING:
  finding_text: "First-time customer return rate crashed from 37% (Feb) to 20% (Mar). 
                Of 45 new customers in March, only 9 came back. 
                That's 13 points below your 33% baseline — the steepest drop in 6 months."
  action_text: "Something turned off first-timers in March. Most likely cause: your average 
                fulfillment time went from 12 to 18 minutes in March (a café's #1 churn driver). 
                Check if the new staff member needs more barista training. For a specialty 
                café, a 6-minute wait increase is the difference between 'I'll come back' 
                and 'too slow for my morning routine.'
                Target: get fulfillment back under 13 minutes within 2 weeks."
  urgency: "this_week"
  confidence_score: 80
  evidence_data: {
    "cohort_feb": {"first_timers": 38, "returned": 14, "rate": 0.368},
    "cohort_mar": {"first_timers": 45, "returned": 9, "rate": 0.200},
    "baseline_rate": 0.33,
    "deviation_pct": 0.39,
    "data_points_count": 83
  }
```

**Golden Example 3: High-LTV Customer Profile**

```
INPUT:
  top_20pct_customers (by total_spend):
    common_patterns: {
      "avg_visit_day": "Saturday",
      "avg_visit_hour": 11,
      "top_items": ["Eggs Benedict", "Latte", "Avocado Toast"],
      "avg_order_value_paisa": 115000,
      "pct_dine_in": 0.92,
      "avg_visits_per_month": 3.4
    }
  overall_avg_order_value_paisa: 58000

EXPECTED FINDING:
  finding_text: "Your top 20% customers share a clear pattern: Saturday/Sunday brunch, 
                dine-in, ordering Eggs Benedict or Avocado Toast with a Latte. They spend 
                ₹1,150/visit (98% above your ₹580 average) and come 3.4 times/month. 
                92% are dine-in — these are the people who sit for an hour, not delivery orders."
  action_text: "This is your ideal customer profile. Two actions:
                1. Saturday 10am-1pm is your highest-value window — your best barista and most 
                   attentive server should always be on this shift. No exceptions.
                2. When a first-timer orders Eggs Benedict + Latte on a Saturday, that's a 
                   high-LTV signal. Make their experience exceptional — they're potentially 
                   worth ₹47,000/year each (₹1,150 × 3.4 visits × 12 months)."
  urgency: "strategic"
  confidence_score: 75
```

**Scoring Function:**

```python
def score_sara_finding(finding: Finding) -> float:
    score = 0.0
    import re
    
    # 1. Names specific customers or uses specific cohort numbers — 0.25
    has_specifics = bool(re.search(r'(\d+ visit|\d+ customer|\d+%|\d+ day)', finding.finding_text))
    if has_specifics:
        score += 0.25
    
    # 2. Action references a retention/relationship mechanism — 0.25
    retention_terms = ["return", "reach", "personal", "recover", "habit", 
                       "loyalty", "repeat", "conversion", "relationship", "touch"]
    if any(term in finding.action_text.lower() for term in retention_terms):
        score += 0.25
    
    # 3. Includes ₹ values (lifetime, avg spend, potential) — 0.25
    if "₹" in finding.finding_text:
        score += 0.25
    
    # 4. Evidence has >= 3 data points — 0.25
    if finding.evidence_data.get("data_points_count", 0) >= 3:
        score += 0.25
    
    return score
```

**Quality Bar:** >= 0.75 on all 3 golden examples.

#### Sara's Data Coverage

```python
coverage = orders_with_customer_id / total_orders
if coverage < 0.60:
    finding.finding_text = f"[Based on {coverage*100:.0f}% of orders with customer ID] " + finding.finding_text
    finding.confidence_score = max(30, finding.confidence_score - int((1 - coverage) * 50))
```

#### Layer 3 — The Flywheel Hook

- Owner replies "Ananya moved to Bangalore" → store as learned fact, exclude from future lapsed alerts
- Owner acts on lapsed alert and customer returns within 14 days → log "recovery_successful"
- Track recovery rate of lapsed alerts: if < 10% after 2 months → raise days threshold from 45 to 60
- If owner consistently ignores cohort findings → downweight to strategic urgency

---

### PHASE-A3: Priya — Cultural & Calendar Intelligence

**File:** `backend/intelligence/agents/priya.py`
**Inherits:** `BaseAgent`
**Schedule:** Daily 7:30 AM IST + full scan Sunday midnight
**Max findings per run:** 2 (daily) / 3 (weekly deep scan)

#### Layer 1 — The Story

YoursTruly in Kolkata has a specific cultural context. The catchment is 52% Bengali Hindu (celebrates Durga Puja, not strict Navratri fasting), 27% Muslim (Ramzan and Eid affect eating patterns), 2% Jain (negligible), and 19% other. This means:

- **Durga Puja** (October) = MASSIVE. The biggest event for this café's customers. Pandal-hopping crowds flood the streets. Evening foot traffic surges 30-40%. People want coffee, desserts, and a place to sit after walking. This is a ₹50K incremental revenue opportunity.
- **Navratri** = Low relevance. Bengali Hindus don't fast for Navratri the way Gujarati or Marwari communities do. Sending a "Navratri fasting menu" alert to Piyush would be tone-deaf.
- **Ramzan** = Moderate. 27% Muslim catchment means noticeable shift in daytime orders during Ramzan, with Iftar-time evening surge.
- **Salary week** = High relevance. Kolkata corporate crowd splurges on premium coffee in week 1.

Priya must NEVER apply pan-Indian cultural assumptions to YoursTruly. The whole point is catchment-specific intelligence.

#### Layer 2 — The Eval

**Golden Example 1: Navratri — Low Relevance for Kolkata Café**

```
INPUT:
  restaurant: YoursTruly Coffee Roaster, Kolkata
  catchment_demographics: {"hindu_bengali": 0.52, "muslim": 0.27, "jain": 0.02, "other": 0.19}
  event: "navratri_sharada" from cultural_events table
  event.city_weights: {"kolkata": 0.40}
  event.primary_communities: ["hindu_north", "hindu_maharashtrian", "jain"]
  days_until_event: 12

EXPECTED FINDING:
  finding_text: "Navratri Sharada starts in 12 days. Minimal impact for your café 
                (relevance: 21/100). Your Kolkata catchment is 52% Bengali Hindu — they 
                celebrate Durga Puja, not Navratri fasting. Your Jain segment is only 2%. 
                You might see a slight dip in non-veg orders from the small North Indian 
                segment, but nothing that requires a menu change."
  action_text: "No action needed. Don't create a Navratri special menu — it wouldn't 
                resonate with your core customer base. If anything, add one satvik option 
                to the specials board as a gesture for the 2-3% who do observe."
  urgency: "strategic"
  confidence_score: 70
```

**Golden Example 2: Durga Puja — HIGH Relevance**

```
INPUT:
  same restaurant
  event: "durga_puja" from cultural_events table
  event.city_weights: {"kolkata": 1.00}
  event.primary_communities: ["hindu_bengali"]
  event.behavior_impacts: {"evening_dine_in": +2.5, "premium_desserts": +2.0, 
                           "delivery_demand": -1.5, "foot_traffic": +3.0}
  days_until_event: 10

EXPECTED FINDING:
  finding_text: "Durga Puja is 10 days away — this is your biggest week of the year. 
                Relevance: 85/100 (52% of your customers are Bengali Hindu). 
                Expect: +35% evening dine-in (pandal-hopping crowds will stop in for coffee), 
                +25% dessert orders (festive indulgence — Tiramisu, Cheesecake, Brownie), 
                -15% delivery (everyone's walking around, not ordering in)."
  action_text: "Three actions with 10 days lead time:
                1. Staff up Thursday-Sunday evenings (7-11pm — this will be your busiest 
                   window of the year)
                2. Double your Tiramisu, Cheesecake, and Brownie prep for the 5-day peak
                3. Shift 15% of delivery-focused prep to dine-in — your tables will be 
                   full with pandal-hopping crowds wanting coffee and dessert
                4. Consider extended hours till midnight on Ashtami and Navami nights
                Revenue opportunity: ₹35,000-50,000 incremental over the 5-day peak 
                if you're staffed and stocked for it."
  urgency: "this_week"
  confidence_score: 85
  estimated_impact_paisa: 3500000
```

**Golden Example 3: Salary Week for Corporate Kolkata**

```
INPUT:
  today: April 3 (week 1 of month)
  profile.catchment_type: "mixed" (with significant corporate presence)
  historical:
    week_1_avg_ticket_paisa: 82000 (₹820)
    week_4_avg_ticket_paisa: 61000 (₹610)
    week_1_cold_brew_share: 0.18
    week_4_cold_brew_share: 0.09
    week_1_eggs_benedict_share: 0.12
    week_4_eggs_benedict_share: 0.06

EXPECTED FINDING:
  finding_text: "Salary week (April 1-7). Your customers spend 34% more per order in 
                week 1 vs week 4 (₹820 vs ₹610). Cold Brew orders double (18% vs 9% share). 
                Eggs Benedict orders double too (12% vs 6%). Your corporate crowd treats 
                themselves when the salary hits."
  action_text: "This week, push your premium items hard:
                • Cold Brew (₹300, 81.7% margin — your most profitable drink) 
                • Eggs Benedict (₹420 — highest ticket brunch item)
                • Matcha Latte (₹340 — the trendy splurge option)
                Put a 'Barista's Pick' table card featuring Cold Brew this week. 
                Your customers are 2x more likely to trade up right now."
  urgency: "immediate"
  confidence_score: 75
```

**Scoring Function:**

```python
def score_priya_finding(finding: Finding) -> float:
    score = 0.0
    import re
    
    # 1. Filters through actual catchment (mentions Bengali, Kolkata, specific communities) — 0.30
    catchment_terms = ["bengali", "kolkata", "your catchment", "your customers", "your café",
                       "muslim", "jain", "corporate", "52%", "27%"]
    generic_terms = ["india", "nationally", "across the country", "all restaurants"]
    if any(t in finding.finding_text.lower() for t in catchment_terms):
        if not any(t in finding.finding_text.lower() for t in generic_terms):
            score += 0.30
    
    # 2. Specific behavioral prediction with numbers — 0.25
    if re.search(r'[+-]?\d+%', finding.finding_text):
        score += 0.25
    
    # 3. Action includes timing / lead time — 0.20
    if re.search(r'\d+ day', finding.finding_text.lower() + finding.action_text.lower()):
        score += 0.20
    
    # 4. Includes relevance score — 0.25
    if "relevance" in finding.finding_text.lower() or "/100" in finding.finding_text:
        score += 0.25
    
    return score
```

**Quality Bar:** >= 0.75 on all 3 golden examples. PLUS:
- Navratri relevance for YoursTruly Kolkata MUST be "strategic" urgency (not "this_week" or "immediate"): **binary PASS/FAIL**
- Durga Puja relevance for YoursTruly Kolkata MUST be "this_week" or "immediate": **binary PASS/FAIL**

#### Priya's Relevance Calculation

```python
def calculate_catchment_relevance(event, profile) -> int:
    """0-100 score. Only events > 20 become findings."""
    relevance = 0.0
    catchment = profile.catchment_demographics or {}
    city_weight = (event.city_weights or {}).get(profile.city.lower(), 0.0)
    
    for community in event.primary_communities:
        community_share = catchment.get(community, 0.0)
        max_impact = max(abs(v) for v in (event.behavior_impacts or {}).values()) / 3.0
        relevance += community_share * city_weight * max_impact * 100
    
    return min(100, int(relevance))
```

#### Layer 3 — The Flywheel Hook

- After every cultural event: compare Priya's predicted behavior vs actual orders
- Store accuracy: `{"durga_puja_2026": {"predicted_evening_uplift": 0.35, "actual": 0.42, "error": 0.07}}`
- If owner says "Actually we now have a lot of Marwari families in the area" → update catchment_demographics
- Salary week predictions: compare predicted premium item uplift vs actual per item

**Seeding cultural_events:** Phase A3 includes a one-time migration script that reads docs/CULTURAL_MODEL.md and inserts all 18 events into the `cultural_events` table.

---

## PHASE B: Quality Council — The Sacred Gate

**Files:**
- `backend/intelligence/quality_council/significance.py`
- `backend/intelligence/quality_council/corroboration.py`
- `backend/intelligence/quality_council/actionability.py`
- `backend/intelligence/quality_council/council.py`

**Nothing reaches Piyush without passing all 3 stages. Ever.**

#### Layer 1 — The Story

The QC is the difference between YTIP and noise. If Arjun sends a waste alert every day, Piyush ignores it after a week. If Maya sends margin findings that conflict with his "always organic milk" principle, he loses trust. If Ravi flags a single bad Monday as a revenue crisis, the system looks stupid.

The QC ensures: the signal is real (Stage 1), something else confirms it (Stage 2), and the recommended action is specific, timely, and doesn't violate Piyush's values (Stage 3).

#### Layer 2 — The Eval

**Stage 1: Significance — 6 Golden Examples**

```
CASE 1 (PASS): revenue deviation 22%, 5 data points, z-score 2.2
  → (True, 0.22, "passed")

CASE 2 (FAIL): deviation 30% but only 2 data points
  → (False, 0, "insufficient_data_points")

CASE 3 (FAIL): revenue deviation only 8% (below 15% threshold)
  → (False, 0.08, "below_significance_threshold")

CASE 4 (PASS): Latte CM% dropped 12% (menu category, 10% threshold)
  → (True, 0.12, "passed")

CASE 5 (FAIL): 18% deviation but baseline_std is huge (z-score 0.48 < 1.5)
  → (False, 0.48, "not_statistically_significant")

CASE 6 (PASS): Eggs Benedict waste 51% (stock category, 30% threshold)
  → (True, 0.51, "passed")
```

**Thresholds:**

| Category | Min Deviation | Min Data Points | Min z-score |
|----------|---------------|-----------------|-------------|
| revenue | 15% | 3 | 1.5 |
| menu | 10% | 3 | 1.5 |
| stock | 30% | 3 | 1.5 |
| customer | 15% | 3 | 1.5 |

**Stage 2: Corroboration — 4 Golden Examples**

```
CASE 1 (PASS): Ravi flags Saturday revenue drop + Arjun flags brunch waste increase
  → corroborated (demand-supply mismatch signal)

CASE 2 (HOLD): Maya flags Matcha Latte as dead SKU, no other agent sees anything
  → hold 1 cycle, re-check next run

CASE 3 (PASS solo): Ravi flags 35% revenue drop, immediate urgency, confidence 90
  → solo high-urgency exception passes

CASE 4 (ESCALATE): Ravi says delivery revenue UP 25%, Sara says delivery customers DOWN 15%
  → contradiction detected, hold BOTH, flag for review
```

**Stage 3: Actionability + Identity — 5 Golden Examples**

```
CASE 1 (PASS): "Reduce Saturday Eggs Benedict prep to 16 portions" with deadline 3 days
  → passed

CASE 2 (FAIL): "Consider reviewing things" — vague, < 20 chars meaningful content
  → action_text_too_vague

CASE 3 (FAIL): Good action but no deadline
  → no_deadline

CASE 4 (REWORK): "Switch to non-organic milk to save ₹4,000/month"
  profile.non_negotiables: ["Always use organic milk"]
  → REWORKED to: "Your organic milk premium costs ₹4,000/month. To maintain your organic 
    commitment, consider a ₹10 price increase on Latte, Cappuccino, and Mocha to 
    recover the premium. At your current volumes, that covers the full difference."
  qc_notes: "action_reworked: conflict with 'Always use organic milk'"

CASE 5 (FAIL): "Feature Cold Brew on Swiggy" — duplicate of finding sent 3 days ago
  → duplicate_of_recent_finding
```

**Identity conflict detection uses Claude:**
```python
def action_violates_non_negotiable(action_text: str, non_negotiable: str) -> bool:
    """Claude call (max_tokens=5) to check conflict. Necessary because both are free-text."""
    prompt = f"""Does this action conflict with this non-negotiable? YES or NO only.
    ACTION: {action_text}
    NON-NEGOTIABLE: {non_negotiable}"""
    return "YES" in call_claude(prompt).upper()
```

**Overall QC Quality Bar:**
- 15 test cases (6+4+5): >= 14 correct (93%+)
- Identity filter catches ALL non-negotiable conflicts: 5/5
- Duplicates blocked within 7 days: PASS/FAIL
- Max 3 hold cycles before reject: PASS/FAIL

#### Layer 3 — The Flywheel Hook

- Track QC pass rates per agent: if Arjun has 90% pass rate and Sara has 40%, Sara's findings need work
- Track owner action rate by category: if Piyush always acts on stock findings but ignores customer findings → lower customer threshold (fewer, higher-signal)
- After 30 days: agents with highest QC pass rate get +5 confidence boost

---

## PHASE C: Synthesis + Weekly Brief

**Files:**
- `backend/intelligence/synthesis/formatter.py`
- `backend/intelligence/synthesis/weekly_brief.py`
- `backend/intelligence/synthesis/voice.py`

#### Layer 1 — The Story

Every message Piyush receives sounds like one deeply informed advisor. Not a system report. Not multiple agents. One voice that knows his café, his customers, his milk costs, and his non-negotiables.

#### Layer 2 — The Eval

**Golden Example 1: Cold Brew Hidden Star → WhatsApp**

```
INPUT (validated Finding from Maya):
  finding_text: "Cold Brew has 81.7% margin but only ranks 6th in orders. 
                It's your most profitable drink but most customers don't see it."
  action_text: "Move Cold Brew to top 3 in Swiggy beverages. Feature it on the 
                counter menu board. Staff should recommend it."
  estimated_impact_paisa: 450000

EXPECTED MESSAGE:
  "Your Cold Brew is quietly your best business decision — 82% margin, higher than 
  any other drink on your menu. But it's only your 6th most ordered coffee.

  Most customers are defaulting to Latte and Cappuccino. They're not seeing the Cold Brew.

  Quick wins:
  1. Move it to the top of your Swiggy beverages listing (takes 2 minutes in PetPooja)
  2. Put it on the counter board as 'Barista's Recommendation'
  3. Ask your baristas to suggest it when someone orders an Iced Latte — same price, 
     better margins for you, and honestly a better product

  Even a 20% volume increase means ₹4,500/month in extra contribution from one menu move.

  Reply if you want me to find more hidden margin gems in your menu."
```

**Golden Example 2: Weekly Brief**

```
EXPECTED MESSAGE (Monday 8am):

"Saturday brunch broke a record — your best weekend in 6 weeks. Here's your Monday brief.

📊 *Last Week*
Revenue: ₹3,12,000 (+14% vs prev week)
Orders: 478 (+11%)  
Avg ticket: ₹653 (+3%)

🏆 *Wins*
1. Saturday brunch did ₹68,000 — your best this quarter. Eggs Benedict sold out by 12:30pm
2. Cold Brew orders up 22% after you moved it on the menu board — nice
3. Swiggy rating held at 4.4 despite a delivery spike Wednesday

⚡ *This Week*
1. Eggs Benedict sold out Saturday at 12:30 — prep 18 instead of 15 this week
2. Matcha Latte has had 2 orders in 30 days — ₹340 of menu real estate doing nothing
3. Wednesday lunch is still your weakest slot (₹8,200 avg vs ₹22,000 Saturday lunch)

📅 *Week Ahead*
• Salary week (April 1-7) — push Cold Brew and Eggs Benedict, your highest-margin premium items
• Clear weather all week — expect normal dine-in/delivery split
• No cultural events

💡 *Idea*
Mango season is here. A Mango Cheesecake or Mango Smoothie Bowl could work as a limited 
special — your dessert category has room and mango cost is at its seasonal low right now.

📌 *From Last Week*
The Eggs Benedict waste alert (51% waste rate) — you reduced prep to 16 and it sold out. 
Suggest trying 18 this Saturday.

Reply with any questions about these numbers."
```

**Scoring Function:**

```python
def score_whatsapp_message(message: str, finding: dict) -> float:
    score = 0.0
    
    # 1. Under 225 words — 0.15
    if len(message.split()) <= 225:
        score += 0.15
    
    # 2. No preamble in first 50 chars — 0.15
    bad_openings = ["i've been", "based on", "our system", "our ai", "after analysing"]
    if not any(p in message[:50].lower() for p in bad_openings):
        score += 0.15
    
    # 3. Contains ₹ amounts — 0.15
    if "₹" in message:
        score += 0.15
    
    # 4. Time-specific action — 0.15
    if any(t in message.lower() for t in ["this week", "today", "saturday", "monday"]):
        score += 0.15
    
    # 5. No agent names or system internals — 0.20
    banned = ["ravi", "maya", "arjun", "priya", "sara", "quality council", 
              "agent", "algorithm", "z-score", "our system detected"]
    if not any(b in message.lower() for b in banned):
        score += 0.20
    
    # 6. Conversation hook at end — 0.10
    if any(h in message[-100:].lower() for h in ["reply", "want me to", "questions"]):
        score += 0.10
    
    # 7. Under 4096 chars — 0.10
    if len(message) <= 4096:
        score += 0.10
    
    return score
```

**Quality Bar:** >= 0.80 on both examples.

**Weekly Brief:** all 8 sections present, under 500 words, specific ₹ numbers in every section, no agent names. **PASS/FAIL.**

**Message Batching:** if 3 findings pass QC simultaneously, only the highest-ranked sends immediately. Others queue for 4 hours or weekly brief. **PASS/FAIL.**

#### Layer 3 — The Flywheel Hook

- Owner response time tracked per message type
- If Piyush responds to margin findings 80% but stock findings 30% → stock findings go to weekly brief, margin findings send individually
- If Piyush always reads Monday brief (replies or asks follow-ups) → brief is working, don't change format

---

## PHASE D: WhatsApp Onboarding State Machine

**File:** `backend/services/onboarding_service.py`
**States:** INITIAL → IDENTITY_CAPTURE → BUSINESS_FACTS → VISION_AND_VALUES → CATCHMENT → MENU_VALIDATION → PREFERENCES → COMPLETE

Read docs/ONBOARDING_FLOW.md before building this. That document has the full conversation design.

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| All hard facts captured after COMPLETE | cuisine_type, city, has_delivery, has_dine_in are non-null |
| Non-negotiables captured as array with >= 1 entry | profile.non_negotiables is list, len >= 1 |
| owner_description non-empty | len > 20 chars |
| Voice notes accepted and transcribed | Send audio in BUSINESS_FACTS → transcription in response |
| Resumable across sessions | Start flow, go silent 2 hours, send "hi" → picks up at last state |
| Menu graph bootstrapped on COMPLETE | menu_graph_nodes has rows for restaurant_id |
| Max 8 validation questions in MENU_VALIDATION | Even if 20 low-confidence nodes exist |
| Non-negotiables reflected back for confirmation | System echoes as bullet list before storing |
| Under 25 minutes total | Design ceiling |

#### Flywheel: Owner corrections during MENU_VALIDATION → `menu_graph_learned_facts`. Time-per-state tracking for conversation optimization.

---

## PHASE E: Agent Scheduler + Orchestration Pipeline

**File:** `backend/scheduler/agent_scheduler.py` (REWRITE from CLI to APScheduler)

#### 2am Daily Pipeline

```
1. Fetch yesterday's PetPooja orders     → ingestion/petpooja_orders.py
2. Fetch yesterday's inventory/COGS      → ingestion/petpooja_inventory.py  
3. Fetch stock snapshot                   → ingestion/petpooja_stock.py
4. Compute daily_summary                  → compute/daily_summary.py
5. Run Ravi, Maya, Arjun, Sara           → PARALLEL
6. Quality Council vets all findings      → quality_council/council.py
7. Synthesis formats validated findings   → synthesis/formatter.py
8. Send WhatsApp nudges                   → services/whatsapp_service.py
```

**Monday 8am: Weekly Brief** (gather all 7-day findings + Priya forward calendar → synthesis/weekly_brief.py → WhatsApp)

#### Agent Schedule

| Agent | Schedule | Rationale |
|-------|----------|-----------|
| Ravi | 7am, 11am, 3pm, 7pm, 11pm | Every 4 hours during trading |
| Maya | 1am daily | After day close data |
| Arjun | 6am + 11pm | Before kitchen, after close |
| Sara | Sunday 1am | Weekly customer analysis |
| Priya | 7:30am daily + Sunday midnight | Calendar check + deep scan |
| QC + Synthesis | Event-triggered | Runs when findings exist |
| Weekly Brief | Monday 8am | Start of business week |

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Pipeline runs at 2am IST automatically | APScheduler cron visible in logs |
| If ETL fails, agents don't run | Dependency enforcement |
| Agents run in parallel | Start within 5 sec of each other |
| QC runs after ALL agents complete | QC start > max(agent end times) |
| Total pipeline < 5 min | Single restaurant, 90 days data |
| Monday 8am brief fires | Visible in logs |
| Failed agent doesn't block others | Ravi crash → Maya/Arjun/Sara still run |
| agent_run_log populated | Row per agent run with timing + findings_count + error |
| ETL retry: 3x with exponential backoff | 1min, 3min, 9min |

#### Failure Handling

| Failure | Behavior |
|---------|----------|
| ETL fails all retries | Skip agents. Alert Nimish (not Piyush). |
| One agent fails | Return []. Log. Others continue. |
| QC fails | Hold all findings. Retry next cycle. |
| WhatsApp API down | Queue. Retry 3x. If all fail, email Nimish. |
| Claude API down | Agent returns []. Retry next cycle. |

---

## PHASE F: Knowledge Base (pgvector RAG)

**Files:** `backend/intelligence/knowledge_base/ingestor.py`, `retriever.py`, `embedder.py`

| Parameter | Value |
|-----------|-------|
| Embedding model | OpenAI text-embedding-3-small (1536 dims) |
| Chunk size | ~500 tokens, 50-token overlap |
| Storage | pgvector on RDS PostgreSQL |
| Admin endpoint | POST /api/knowledge-base/ingest |

**Acceptance:** PDF upload → chunks created → `query_knowledge_base("specialty coffee pricing elasticity")` returns relevant chunks in < 500ms.

**Flywheel:** Track which chunks agents cite. High-use chunks = high-value content. Frequently-retrieved-but-never-cited chunks = possible low quality.

---

## PHASE G: Customer Identity Resolution

**File:** `backend/intelligence/customer_resolution/resolver.py`

1. Exact phone match → merge
2. Exact email match → merge  
3. Fuzzy name + similar order pattern → candidate at confidence 70
4. Same PetPooja customer_id with different phones → merge

**Acceptance:** Resolver is idempotent. "Ananya S" and phone 919830456789 with matching orders merge into one resolved_customer. Running twice = same result.

---

## SECTION Z: Cross-Cutting Constraints

### Monetary Values

| Context | Convention |
|---------|-----------|
| Phase 1 tables (orders, etc.) | BigInteger paisa (₹500 = 50000) |
| Intelligence tables (estimated_impact_paisa) | BigInteger paisa |
| Computed ratios (CM%, waste_ratio) | NUMERIC(15,2) — never float |
| WhatsApp display | ₹ with Indian formatting |

### Agent Error Pattern (mandatory for every agent)

```python
def run(self) -> list[Finding]:
    findings = []
    try:
        for analysis in [self._analyze_x, self._analyze_y]:
            try:
                result = analysis()
                if result:
                    findings.append(result)
            except Exception as e:
                logger.warning("%s.%s failed: %s", self.agent_name, analysis.__name__, e)
                continue
    except Exception as e:
        logger.error("%s failed entirely: %s", self.agent_name, e)
        return []
    findings.sort(key=lambda f: f.confidence_score, reverse=True)
    return findings[:self.MAX_FINDINGS]
```

### File Size: 300 lines max (routers 400). Split if growing.

### Claude Model: `claude-sonnet-4-6` for all agent/QC/synthesis calls. `text-embedding-3-small` for embeddings. Whisper for voice.

### T-1 Reality: Agents run on yesterday's close. Never say "today's revenue" — say "yesterday" or "as of close yesterday."

### Cost Per Restaurant Per Month

| Component | ~Cost |
|-----------|-------|
| Claude (agents + QC + synthesis) | ₹3,800 |
| Claude (ad-hoc chat) | ₹1,000 |
| OpenAI (embeddings + whisper) | ₹300 |
| **Total** | **~₹5,100/month** |

### Testing

| Module | Approach |
|--------|---------|
| Agents | Unit tests with in-memory SQLite (conftest.py exists). Use golden examples from this PRD. |
| Quality Council | Unit tests with pre-constructed Finding objects. Test all 15 cases from Phase B. |
| Synthesis | Unit tests. Input: Finding → Output: string. Score with scoring function. |
| Onboarding | Integration test: simulate conversation via function calls. Verify profile populated. |
| Scheduler | Integration test on test DB. Verify sequence + timing. |

---

## CLAUDE.md Addition

Add to the routing table:

```
| Building any Phase 2 module | docs/PRODUCTION_PRD.md — find the PHASE section for your module |
```

Add to "Current Build State":

```
Phase 2 (intelligence layer) — IN PROGRESS
Build order: docs/PRODUCTION_PRD.md. Each phase has eval criteria that must pass before proceeding.
```

Read Section 0 and Section 1 once at session start. Then read ONLY the PHASE section for the module you're building. Do not read other phases unless tracing a dependency.

---

*End of Production PRD v1.0*
*Every module defined. Every eval uses real YoursTruly menu data.*
*Cold Brew at 81.7% margin. Eggs Benedict at 66.7% with waste risk. Latte + Iced Latte as variant cluster.*
*The directive: read the phase, read the golden examples, make the score go up, ship when it hits the bar.*
