# YTIP — Agent Specifications

> Full mandate for each of the 7 agents and the Quality Council.
> Read the relevant section before building any agent.

---

## Agent Architecture Overview

Each agent is a Python class inheriting from `BaseAgent`. Every agent:
- Reads only from the semantic data layer (menu graph + resolved customers) — never from raw PetPooja tables directly
- Reads the restaurant profile before every run — identity filter is applied at agent level AND at QC level
- Returns a list of `Finding` objects — never sends messages, never writes to DB directly
- Fails silently — wraps everything in try/except, logs errors, returns []
- Is completely stateless within a run — all state comes from DB reads

**One rule above all others:**
> An agent that is uncertain produces zero findings. An agent that is confident produces one finding. Producing many uncertain findings is worse than producing none.

---

## Agent 1: Ravi — Revenue & Orders

**File:** `backend/intelligence/agents/ravi.py`

**Mandate:** Watch order flow. Know what normal looks like. Fire when meaningful deviation occurs.

### Data Queries Ravi Runs

```python
# 1. Current period revenue vs. baseline
# Compare today/this week to the same day/week for the past 8 weeks
# Group by: day_part (morning/lunch/evening/dinner), platform, payment_mode

# 2. Day-part performance breakdown
# For each day-part: actual_revenue vs. expected_revenue (8-week avg)
# Flag if deviation > 15% for 3+ consecutive occurrences

# 3. Platform mix analysis
# Dine-in vs. delivery vs. takeaway percentage
# Flag if platform mix shifts > 20% vs. 4-week average

# 4. Discount analysis
# Total discount as % of gross revenue
# Flag if discount_rate trending up for 3+ weeks without volume increase

# 5. Void and cancellation rate
# Voids / total orders
# Flag if > 5% (threshold calibrated per restaurant over time)

# 6. Weather correlation check
# Pull today's IMD forecast
# Check if delivery/dine-in behaved as historically expected for this weather
```

### Signals Ravi Layers In

```python
# Salary cycle (from Priya's cultural model)
week_of_month = get_week_of_month()
# Week 1 (1st-7th): expect premium dish orders up
# Week 4 (24th+): expect value-seeking behaviour

# IPL/Cricket match tonight?
is_match_night = check_cricket_schedule()  # from external signal store
# Match night: delivery spike expected post-7pm, dine-in drop expected

# Weather today
weather = get_weather_signal()
# Rain: delivery surge expected, dine-in drop expected
```

### Finding Templates Ravi Uses

**Revenue Dip (sustained):**
```
finding_text: "Tuesday lunch revenue has declined [X]% over the past [N] weeks 
               vs. the 8-week baseline (₹[actual] vs ₹[expected] average)"
action_text: "Investigate Tuesday lunch slot — check if any operational change 
              coincides with the drop. Consider a Tuesday lunch special to 
              stimulate demand."
evidence_data: {
    week_by_week: [...],
    baseline_avg: ...,
    latest_value: ...,
    deviation_pct: ...,
    day_part: "lunch",
    day_of_week: "Tuesday"
}
```

**Platform Mix Shift:**
```
finding_text: "Delivery share has dropped from [X]% to [Y]% over [N] weeks 
               while dine-in has increased proportionally"
action_text: "Check your aggregator listing quality — photos, menu accuracy, 
              ratings. A delivery drop without a corresponding dine-in revenue 
              increase suggests lost orders, not conversion."
```

**Delivery-Weather Disconnect:**
```
finding_text: "Heavy rain forecast today but delivery orders are [X]% below 
               your historical rainy-day average at this time"
action_text: "Send a WhatsApp broadcast to your regular customers or run a 
              quick 15% off promotion on Swiggy for the next 3 hours."
```

### What Ravi Specifically Does NOT Do
- Flag single-day anomalies (minimum 3 occurrences)
- Compare to industry benchmarks (only this restaurant's own history)
- Generate findings about events that Priya has already flagged as expected cultural behavior
- Send more than 2 findings per run cycle

---

## Agent 2: Maya — Menu & Margin Guardian

**File:** `backend/intelligence/agents/maya.py`

### Margin Calculation

Maya calculates contribution margin at dish level daily:
```
CM% = (selling_price - food_cost) / selling_price × 100

food_cost per dish:
  For each ingredient in dish recipe:
    ingredient_cost = current_apmc_price × quantity_used
  Sum all ingredient costs
  Add overhead_factor (packaging, utilities estimate — from profile)
```

Note: If recipe cost data is not in PetPooja, Maya uses category-level cost estimates from industry benchmarks until owner provides actual recipe costs. She flags this assumption explicitly.

### BCG Matrix Recalculation (weekly)

```python
# Segment all active menu items into quadrants
all_items = menu_graph.get_active_standalone_items()

volume_median = median([i.order_count_30d for i in all_items])
margin_median = median([i.contribution_margin_pct for i in all_items])

for item in all_items:
    if item.orders > volume_median and item.cm_pct > margin_median:
        item.bcg = "star"       # push hard
    elif item.orders > volume_median and item.cm_pct <= margin_median:
        item.bcg = "cash_cow"   # protect, optimise price
    elif item.orders <= volume_median and item.cm_pct > margin_median:
        item.bcg = "question"   # investigate, fix or retire
    else:
        item.bcg = "dog"        # retire unless identity-critical
```

### Review Sentiment Monitoring

Maya scrapes and processes reviews weekly:
- Sources: Zomato, Swiggy, Google Maps (public reviews)
- Extracts: dish mentions, sentiment per dish, recurring complaint themes
- Tracks: review velocity change (accelerating negative reviews = early warning)

```python
# Alert trigger: dish with >3 negative reviews in 7 days that is in top 10 by volume
# = rating crisis in development — owner must act before rating drops
```

### Key Finding Templates

**Margin Erosion:**
```
finding_text: "[Dish] CM% has dropped from [X]% to [Y]% over [N] weeks due to 
               [ingredient] price increase of [Z]% at APMC"
action_text: "Option A: Increase [Dish] price by ₹[X] to restore margin to [Y]%. 
              Option B: Switch [ingredient] supplier — [supplier] at [market] 
              currently [Z]% cheaper. Option C: Reduce portion by [X]g 
              (below your quality threshold, excluded per your non-negotiables)."
```

**Hidden Star:**
```
finding_text: "[Dish] is your [N]th most profitable item (CM: [X]%) but only 
               [Y]th in your Swiggy menu listing — most customers never see it"
action_text: "Move [Dish] to top 3 in its category on Swiggy. 
              Estimated visibility increase: 40-60%. 
              Estimated additional monthly contribution: ₹[X]-₹[Y]."
```

**Dead SKU:**
```
finding_text: "[Dish] has received [N] orders in the past 30 days. 
               It occupies menu real estate and adds prep complexity."
action_text: "Consider removing [Dish] from the menu. 
              Before removing: confirm it's not identity-critical. 
              If removed, redirect prep capacity to [high-demand dish]."
```

**Review Early Warning:**
```
finding_text: "[Dish] has received [N] negative reviews in the past 7 days — 
               all mentioning [common theme]. Your rating hasn't dropped yet, 
               but this trajectory leads there within 2-3 weeks."
action_text: "Inspect [Dish] prep process today. Common issue: [specific from reviews]. 
              Address before it compounds into a rating drop."
```

---

## Agent 3: Arjun — Stock & Waste Sentinel

**File:** `backend/intelligence/agents/arjun.py`

### Morning Prep Recommendation Algorithm

Arjun generates a daily prep recommendation at 6am:

```python
# For each menu item:
def forecast_demand(item, restaurant_id):
    # Base: average of same day-of-week for past 4 weeks
    base = avg_orders_same_dow_4wks(item, restaurant_id)
    
    # Modifier 1: Weather
    weather = get_today_weather()
    if weather.rain and item.is_delivery_friendly:
        base *= 1.35  # delivery surge
    elif weather.very_hot:
        base *= 0.85  # heavy food drop
    
    # Modifier 2: Cultural calendar (from Priya)
    cultural_context = get_active_cultural_events()
    if "navratri" in cultural_context and item.has_non_veg:
        base *= 0.30  # severe non-veg drop
    if "navratri" in cultural_context and item.is_satvik:
        base *= 2.20
    
    # Modifier 3: Salary cycle
    week = get_week_of_month()
    if week == 1 and item.is_premium:
        base *= 1.20
    elif week == 4 and item.is_value:
        base *= 1.15
    
    # Modifier 4: Day-part trending
    recent_trend = get_3day_trend(item)
    base *= recent_trend
    
    return round(base)  # Recommended prep quantity
```

### Waste Pattern Detection

```python
# Weekly waste analysis
# For each item: compare prep_quantity to actual_consumption
# If prep > consumption by >30% for 3+ consecutive weeks = chronic overprep

waste_finding_threshold = 0.30  # 30% waste ratio triggers finding
waste_weeks_threshold = 3       # 3 consecutive weeks makes it chronic
```

### Supplier Price Spike Detection

```python
# Daily: compare today's APMC prices to 30-day moving average
# Spike threshold: >15% above 30-day average
# Trigger: immediate finding if spike affects >20% of menu cost base

spike_threshold = 0.15
cost_base_impact_threshold = 0.20
```

### Key Finding Templates

**Morning Prep Brief (daily — not a "finding" per se, but a scheduled push):**
```
Format:
"Good morning [owner_name]. Today's prep guide:

↑ Prep more:
• [Dish A]: 45 portions (your Thurs rain pattern + 3 rainy days forecasted)
• [Dish B]: 28 portions (Week 1, premium dish trending up)

↓ Prep less:
• [Dish C]: 12 portions (trending -20% this week)
• [Dish D]: 8 portions (Navratri — non-veg drop expected)

→ Note: Tomato prices up 28% at Vashi APMC today. Check quantities for 
   Shakshuka and Tomato Soup."
```

**Chronic Waste Alert:**
```
finding_text: "[Dish] is being prepped [X] portions on average [Day] but only 
               [Y] are sold — [Z] portions wasted weekly. 
               At current food cost this is ₹[W] in weekly waste."
action_text: "Reduce [Dish] prep on [Day] to [recommended_qty] portions. 
              If demand picks up, prep more is always possible. 
              Projected weekly saving: ₹[W]."
```

**Commodity Buy Opportunity:**
```
finding_text: "MCX futures show [commodity] prices expected to rise [X]% 
               in the next 3-4 weeks. Your monthly consumption is [Y]kg."
action_text: "Consider buying [2×monthly_consumption]kg of [commodity] now 
               to lock in current prices. Estimated saving: ₹[Z] over 2 months."
```

---

## Agent 4: Priya — Cultural & Calendar Intelligence

**File:** `backend/intelligence/agents/priya.py`

### The 14-Day Forward Scan

Priya's core job is to always know what is coming in the next 14 days and what it means for this specific restaurant.

```python
def run_forward_scan(restaurant_id: int) -> list[CulturalAlert]:
    profile = load_profile(restaurant_id)
    catchment = profile.catchment_demographics  # {community: pct}
    city = profile.city
    
    upcoming_events = get_events_next_14_days(city)
    
    alerts = []
    for event in upcoming_events:
        # Weight by catchment relevance
        relevance = calculate_catchment_relevance(event, catchment)
        if relevance < 0.20:
            continue  # Less than 20% catchment relevance — skip
        
        # Calculate behavior impact
        impact = calculate_behavior_impact(event, profile)
        
        # Check lead time — is there still time to act?
        days_until = (event.start_date - today()).days
        if days_until < 2:
            urgency = "immediate"
        elif days_until < 7:
            urgency = "this_week"
        else:
            urgency = "strategic"
        
        # Generate specific action for this restaurant
        action = generate_action(event, profile, impact, days_until)
        
        alerts.append(CulturalAlert(
            event=event,
            relevance_score=relevance,
            behavior_impact=impact,
            urgency=urgency,
            action=action,
            days_until=days_until
        ))
    
    return sorted(alerts, key=lambda a: a.relevance_score * a.urgency_weight, reverse=True)
```

### Catchment Relevance Calculation

```python
def calculate_catchment_relevance(event, catchment_demographics):
    # Sum the percentage of communities in catchment that observe this event
    relevant_pct = 0
    for community in event.primary_communities:
        relevant_pct += catchment_demographics.get(community, 0)
    
    # Apply city weight
    city_weight = event.city_weights.get(profile.city_key, 0.5)
    
    return min(relevant_pct / 100 * city_weight, 1.0)
```

### Generational Behavior Overlay

```python
# Based on profile's target customer age band
if profile.primary_age_band == "18-35":
    # Loose observers — plant-based framing, Instagram angle
    satvik_modifier = "modern plant-based menu"
    messaging_angle = "Instagram-worthy seasonal special"
elif profile.primary_age_band == "35-55":
    # Moderate observers
    satvik_modifier = "festive thali option"
    messaging_angle = "family occasion menu"
else:  # 55+
    # Traditional observers
    satvik_modifier = "traditional satvik thali"
    messaging_angle = "authentic festive menu"
```

### Priya's Key Finding Template

```
finding_text: "[Event] starts in [N] days. Your catchment is [X]% [community] — 
               this event has [high/medium] relevance for your customers. 
               Expected impact: [specific behavior change with %]."

action_text: "Add [specific dishes] to your menu by [date — 2 days before event]. 
              [Dishes] have [Y]% contribution margin based on current ingredient costs. 
              Remove or reduce [dishes affected negatively] from prominent placement. 
              [Optional: WhatsApp broadcast angle if delivery restaurant]"

estimated_impact: "Not acting: estimated [Z]% [revenue drop/missed opportunity]. 
                   Acting: estimated ₹[W] additional contribution over [event duration]."
```

---

## Agent 5: Kiran — Competition & Market Radar

**File:** `backend/intelligence/agents/kiran.py`

### Weekly Scan Routine

```python
def weekly_scan(restaurant_id):
    profile = load_profile(restaurant_id)
    
    # 1. New restaurant detection
    new_places = google_places_new_listings(
        lat=profile.lat, lng=profile.lng,
        radius_km=profile.delivery_radius_km,
        since_days=7,
        categories=get_relevant_categories(profile.cuisine_type)
    )
    
    # 2. Competitor rating changes
    top_competitors = get_tracked_competitors(restaurant_id)
    for comp in top_competitors:
        current_rating = google_places_rating(comp.place_id)
        if abs(current_rating - comp.last_rating) > 0.2:
            flag_rating_change(comp, current_rating)
    
    # 3. Trend signals
    city_food_trends = google_trends_food(
        city=profile.city,
        lookback_days=30
    )
    trending_dishes = filter_relevant_trends(city_food_trends, profile)
    
    # 4. Aggregator discovery
    swiggy_trending = scrape_swiggy_trending(profile.area, profile.city)
    zomato_trending = scrape_zomato_trending(profile.area, profile.city)
```

### Relevance Filter

Not every competitive signal is relevant. Kiran filters aggressively:

```python
def is_relevant_threat(new_restaurant, profile):
    # Check cuisine overlap
    if cuisine_overlap(new_restaurant.cuisine, profile.cuisine_type) < 0.3:
        return False  # Different cuisine, not a direct threat
    
    # Check price point overlap
    if abs(new_restaurant.avg_price - profile.avg_order_value) > 200:
        return False  # Very different price point
    
    # Check positioning overlap
    if not positioning_overlap(new_restaurant, profile):
        return False
    
    return True
```

### Key Finding Templates

**New Competitor:**
```
finding_text: "[Restaurant Name] opened [X] days ago, [Y]m from you on [platform]. 
               Cuisine: [type]. Price point: ₹[Z] average. 
               Current rating: [R]. Trajectory: [trending up/down/flat]."
action_text: "Visit or order from them this week — understand what they're doing. 
              Their [specific dish/aspect] is generating [specific feedback from reviews]. 
              Your equivalent is [your dish] — [how you compare based on your reviews]."
```

**Competitor Rating Surge:**
```
finding_text: "[Competitor] has gone from [old_rating] to [new_rating] in [N] weeks. 
               Their recent reviews highlight: [top 3 themes]. 
               [Correlation: your delivery in their radius has dropped X% in same period]."
action_text: "Read their recent reviews — the [specific theme] mentions are instructive. 
              [Specific action based on what they're doing that you could match or counter]."
```

**Trend Entering Market:**
```
finding_text: "[Dish type] searches in [city] are up [X]% over the past 30 days. 
               Currently [N] restaurants are serving this in your area. 
               Early movers are rating [R] on average."
action_text: "[Relevant or not relevant based on profile]. [If relevant]: Chef can 
              suggest a version that fits your positioning. 
              [If not relevant]: This trend is noted but doesn't fit [restaurant name]'s identity."
```

---

## Agent 6: Chef — Recipe & Innovation Catalyst

**File:** `backend/intelligence/agents/chef.py`

### Idea Generation Pipeline

Chef's ideas are never random. Every suggestion is the intersection of:

```
Trend signal (from Kiran) 
    × Seasonal ingredient (from Arjun — cheap + available)
    × Cultural timing (from Priya — upcoming food moment)
    × Menu gap (from Maya — unserved occasion/dietary need)
    × Identity filter (from profile — fits this restaurant)
    × Financial viability (CM% > 50%, else don't suggest)
```

### Contribution Margin Pre-Calculation

```python
def calculate_suggested_dish_margin(dish_ingredients, current_prices):
    total_food_cost = sum(
        ingredient.qty_per_serving * current_prices[ingredient.name]
        for ingredient in dish_ingredients
    )
    packaging = profile.avg_packaging_cost
    overhead_factor = 1.10  # 10% overhead
    
    total_cost = (total_food_cost + packaging) * overhead_factor
    
    # Suggest pricing at 2.5x-3.5x food cost (standard F&B)
    min_price = total_food_cost * 2.5
    target_price = total_food_cost * 3.0
    
    margin_at_target = (target_price - total_cost) / target_price
    
    return {
        "food_cost": total_food_cost,
        "total_cost": total_cost,
        "suggested_price": target_price,
        "margin_pct": margin_at_target
    }
```

### Key Finding Template

```
finding_text: "Opportunity to add [Dish] before [Event/Season] — 
               [Trend signal: searches up X%] + [Season: ingredient Y is cheap this month] + 
               [Menu gap: you have nothing for Z occasion]"

action_text: "Add [Dish] to your menu by [date].
              Suggested price: ₹[X] (₹[Y] above similar in your area)
              Projected CM: [Z]% (₹[W] per cover)
              Ingredients: [list with current market prices and sources]
              Prep complexity: [low/medium/high] — [1-line description]
              Why now: [2-sentence timing rationale]"

estimated_impact: "At [N] orders/week (conservative based on similar launches), 
                   ₹[X] additional weekly contribution."
```

### What Chef Never Does
- Suggest a dish that Maya has flagged as similar to a dead SKU in the same restaurant
- Suggest a dish above "medium" prep complexity if the restaurant profile shows team_size_kitchen < 3
- Suggest a dish with CM% < 50%
- Suggest more than one new dish per weekly cycle (one suggestion, done well, beats three suggestions nobody acts on)

---

## Agent 7: Sara — Customer Intelligence

**File:** `backend/intelligence/agents/sara.py`

### RFM Segmentation (weekly recalculation)

```python
def calculate_rfm(restaurant_id):
    customers = get_resolved_customers(restaurant_id)
    today = date.today()
    
    for customer in customers:
        # Recency: days since last order
        recency = (today - customer.last_order_date).days
        
        # Frequency: orders in last 90 days
        frequency = count_orders(customer.canonical_id, days=90)
        
        # Monetary: total spend in last 90 days
        monetary = sum_spend(customer.canonical_id, days=90)
    
    # Score each dimension 1-5 using this restaurant's own distribution
    # (Not absolute thresholds — relative to this restaurant's customer base)
    
    # Segment labels:
    # Champions: R>=4, F>=4, M>=4
    # Loyal: R>=3, F>=4
    # At Risk: R<=2, F>=3 (was loyal, stopped coming)
    # Cannot Lose: R<=2, F>=4, M>=4 (high-value, stopped coming)
    # New: first order in last 30 days
    # Hibernating: R<=1, F>=2
```

### Key Metrics Sara Tracks

```python
metrics = {
    "new_customer_30d_return_rate": ...,  # % who came back within 30 days
    "champion_count": ...,
    "at_risk_count": ...,
    "cannot_lose_count": ...,
    "avg_orders_per_customer_90d": ...,
    "top_20pct_revenue_concentration": ...,  # % of revenue from top 20% customers
    "cohort_retention_m1": ...,  # of customers from last month, how many came back
}
```

### Key Finding Templates

**High-Value Customer Lapsing:**
```
finding_text: "[N] customers who visited 4+ times in the past 3 months 
               haven't ordered in [X]+ days. Combined historical spend: ₹[Y]."
action_text: "For delivery restaurants: [platform] allows you to send a 'we miss you' 
              offer to lapsed customers from your restaurant dashboard. 
              For dine-in: consider a WhatsApp message via PetPooja's customer export. 
              A 10% return offer on ₹[Y] annual spend = ₹[Z] recovered revenue."
```

**New Customer Conversion Drop:**
```
finding_text: "Your new customer 30-day return rate has dropped from [X]% to [Y]% 
               over the past 2 months. This is the most important early warning 
               metric — it suggests the first visit experience is declining."
action_text: "Investigate what changed 2 months ago — menu, staff, quality, 
              service timing. The data alone can't tell you why, but it's telling 
              you something changed. Review your recent 1-3 star reviews for clues."
```

---

## The Quality Council

**File:** `backend/intelligence/quality_council/council.py`

### Stage 1: Significance Check

```python
def significance_check(finding: Finding, restaurant_id: int) -> tuple[bool, float, str]:
    evidence = finding.evidence_data
    
    # Check 1: Minimum data points
    if evidence.get("data_points_count", 0) < 3:
        return False, 0, "insufficient_data_points"
    
    # Check 2: Deviation magnitude threshold by category
    thresholds = {
        "revenue": 0.15,   # 15% deviation
        "menu": 0.10,      # 10% CM change
        "stock": 0.30,     # 30% waste ratio
        "customer": 0.15,  # 15% retention change
    }
    threshold = thresholds.get(finding.category, 0.15)
    
    if evidence.get("deviation_pct", 0) < threshold:
        return False, evidence["deviation_pct"], "below_significance_threshold"
    
    # Check 3: Statistical significance (simplified z-score against baseline)
    baseline_std = evidence.get("baseline_std", None)
    baseline_mean = evidence.get("baseline_mean", None)
    current_value = evidence.get("current_value", None)
    
    if all([baseline_std, baseline_mean, current_value]) and baseline_std > 0:
        z_score = abs(current_value - baseline_mean) / baseline_std
        if z_score < 1.5:
            return False, z_score, "not_statistically_significant"
    
    return True, evidence.get("deviation_pct", 0), "passed"
```

### Stage 2: Corroboration Check

```python
def corroboration_check(finding: Finding, restaurant_id: int) -> tuple[bool, list, str]:
    # Get all findings from other agents in the last 7 days
    recent_findings = get_recent_validated_findings(
        restaurant_id, 
        exclude_agent=finding.agent_name,
        days=7
    )
    
    corroborating = []
    
    for f in recent_findings:
        if signals_align(finding, f):
            corroborating.append(f.agent_name)
    
    if len(corroborating) >= 1:
        return True, corroborating, "corroborated"
    
    # No corroboration — check if this is a high-confidence immediate finding
    if (finding.urgency == "immediate" and 
        finding.confidence_score >= 85 and
        finding.category in ["competition", "cultural"]):
        # Competition and cultural signals are often first-mover — solo acceptable
        return True, [], "solo_high_confidence_exception"
    
    return False, [], "no_corroboration"


def signals_align(f1: Finding, f2: Finding) -> bool:
    """Check if two findings point in the same direction."""
    # Revenue drop + waste increase = same underlying issue
    # Margin erosion + ingredient price spike = same underlying issue
    # Competitor opening + revenue drop = same underlying issue
    
    alignment_map = {
        ("revenue", "ravi"): [("stock", "arjun"), ("customer", "sara")],
        ("menu", "maya"): [("stock", "arjun"), ("competition", "kiran")],
        ("cultural", "priya"): [("revenue", "ravi"), ("stock", "arjun")],
        ("competition", "kiran"): [("revenue", "ravi"), ("customer", "sara")],
    }
    
    key = (f1.category, f1.agent_name)
    aligned_pairs = alignment_map.get(key, [])
    return (f2.category, f2.agent_name) in aligned_pairs
```

### Stage 3: Actionability + Identity Filter

```python
def actionability_check(finding: Finding, restaurant_id: int) -> tuple[bool, str]:
    profile = load_profile(restaurant_id)
    
    # Check 1: Has specific action
    if not finding.action_text or len(finding.action_text) < 20:
        return False, "action_text_too_vague"
    
    # Check 2: Has deadline
    if not finding.action_deadline:
        return False, "no_deadline"
    
    # Check 3: Not a duplicate of recent finding
    recent_sent = get_sent_findings(restaurant_id, days=7)
    for sent in recent_sent:
        if findings_too_similar(finding, sent):
            return False, "duplicate_of_recent_finding"
    
    # Check 4: Identity filter — check non-negotiables
    for non_neg in profile.non_negotiables:
        if action_violates_non_negotiable(finding.action_text, non_neg):
            # Rework finding to respect non-negotiable
            finding.action_text = rework_action_for_non_negotiable(
                finding.action_text, non_neg
            )
            finding.qc_notes = f"action_reworked: conflict with non-negotiable '{non_neg}'"
    
    # Check 5: Timing — enough lead time to act?
    if finding.action_deadline and (finding.action_deadline - date.today()).days < 0:
        return False, "action_deadline_already_passed"
    
    # Check 6: Operational capacity filter
    if requires_high_kitchen_complexity(finding) and profile.team_size_kitchen < 3:
        # Downgrade or rework
        finding.action_text = simplify_for_small_kitchen(finding.action_text)
    
    return True, "passed"
```

### Finding Deduplication Logic

```python
def findings_too_similar(f1: Finding, f2: Finding) -> bool:
    # Same category + same agent + similar action = duplicate
    if f1.category == f2.category and f1.agent_name == f2.agent_name:
        # Use simple token overlap on action_text
        overlap = jaccard_similarity(f1.action_text, f2.action_text)
        if overlap > 0.6:
            return True
    return False
```

---

## Outcome Tracking & Learning Loop

After every finding is sent, the system tracks what happens:

```python
# When owner responds to a WhatsApp nudge:
def process_owner_response(finding_id, response_text, restaurant_id):
    finding = get_finding(finding_id)
    
    # Detect intent from response
    if indicates_action_taken(response_text):
        update_finding(finding_id, owner_acted=True)
        # Boost confidence weight for this agent + category combination
        adjust_confidence_weight(finding.agent_name, finding.category, +0.05)
    
    elif indicates_dismissal(response_text):
        update_finding(finding_id, owner_acted=False)
        # Check if this is a pattern of dismissal for this type of finding
        dismissal_count = count_dismissals(finding.agent_name, finding.category, days=60)
        if dismissal_count >= 3:
            # This finding type isn't resonating — adjust framing or threshold
            adjust_significance_threshold(finding.agent_name, finding.category, +0.05)
    
    # Track outcome 2 weeks later
    schedule_outcome_check(finding_id, check_date=date.today() + timedelta(days=14))
```

This creates a feedback loop where:
- Consistently acted-upon findings → lower threshold to surface similar findings faster
- Consistently ignored findings → higher threshold or different framing required
- Acted-upon findings that led to positive outcomes → highest confidence, surface similar fast

---

## Agent Prompt Architecture

Each agent calls Claude with a structured prompt. Template:

```python
AGENT_PROMPT_TEMPLATE = """
You are {agent_name}, a specialist analyst for {restaurant_name}.

RESTAURANT PROFILE:
{profile_summary}

NON-NEGOTIABLES (never recommend against these):
{non_negotiables}

YOUR MANDATE:
{agent_mandate}

CURRENT DATA:
{data_summary}

KNOWLEDGE BASE CONTEXT:
{kb_chunks}

ANALYSIS TASK:
{specific_analysis_task}

RESPONSE FORMAT:
Return a JSON array of findings. Each finding must have:
- finding_text: what you found (internal, specific, with numbers)
- action_text: exactly what the owner should do (specific action, not vague guidance)
- action_deadline: YYYY-MM-DD
- urgency: immediate/this_week/strategic
- confidence_score: 0-100
- estimated_impact_paisa: integer or null
- evidence_data: object with supporting numbers

Rules:
- Return [] if nothing is significant enough to flag
- Return maximum 2 findings per run
- Every finding must have a specific action and deadline
- Never recommend anything that contradicts the non-negotiables
- Be specific with numbers — never use "approximately" or "around"
"""
```
