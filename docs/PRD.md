# YTIP — Product Requirements Document

> Full product specification. Read this for feature scope decisions, module boundaries, and product philosophy.
> Last updated: March 2026

---

## 1. Product Vision

### What We Are Building

YoursTruly Intelligence Platform (YTIP) is a continuously operating restaurant intelligence system. It ingests data from every relevant source — the restaurant's own POS, supplier prices, competitor activity, cultural calendars, customer behavior, food trend signals, research publications — reasons across all of it through the lens of each restaurant's unique identity and positioning, and delivers proactive, specific, actionable intelligence to the restaurant owner.

The primary delivery channel is WhatsApp. The owner does not log in, does not check a dashboard, does not ask questions. The system comes to them, with the right intelligence, at the right time, already vetted for quality and actionability.

The secondary channel is a lightweight webapp — for depth, history, and onboarding.

### What We Are Not Building

- A dashboard the owner needs to remember to check
- An analytics tool that shows what happened
- A chatbot that answers questions on demand
- A generic SaaS product with the same insights for every restaurant
- A wrapper around AI with no proprietary intelligence layer

### The Single Test for Every Feature

> "Does this make the owner's next decision better, faster, or more confident — without requiring effort from them?"

If the answer is no, the feature does not belong in YTIP.

---

## 2. The Ten Design Principles

**1. Identity-first.**
Every insight is filtered through who this restaurant is, what the owner values, and what they will never compromise on. A margin improvement recommendation that conflicts with the owner's stated quality non-negotiables never reaches them. The same data point produces different recommendations for a premium café versus a QSR.

**2. Action over analysis.**
Every message to the owner contains one specific action, a deadline, and an estimated ₹ impact where calculable. The system never sends analysis without action. The format is always: here is what is happening, here is what you should do, here is when, here is why it matters in rupees.

**3. Quality gate is sacred.**
Nothing reaches the owner unless it passes all three vetting stages: significance check, cross-agent corroboration, and actionability + identity filter. The system sends nothing rather than sending something questionable. Owner trust is the product's most important asset.

**4. Proactive over reactive.**
The cultural calendar runs 14 days ahead. The competition monitor runs continuously. The margin guardian catches erosion before the P&L shows it. The system is never surprised by what just happened. It is always thinking about what is about to happen.

**5. Conversational learning.**
The system gets smarter through every owner interaction. Owner corrections update the menu graph. Owner responses to nudges calibrate what they care about. The onboarding conversation shapes every future insight. Ignored findings get reweighted. Acted-upon findings get amplified.

**6. Semantic understanding, not rules.**
PetPooja data is messy and restaurant-specific. The Menu Intelligence Layer understands data the way a smart employee would — inferring parent-variant relationships, identifying ghost items, learning modifier patterns — without hardcoded cleaning rules. This understanding is per-restaurant and compounds over time.

**7. Distributed intelligence, single voice.**
Seven specialist agents run independently with no hierarchy. Each owns a domain and reasons deeply within it. The Quality Council synthesises across domains. The owner hears one coherent voice that sounds like one deeply informed advisor, not a system report.

**8. Zero restaurant hardcoding.**
Every restaurant-specific fact lives in the restaurant profile. The intelligence engine is completely restaurant-agnostic. Adding a new restaurant requires adding a profile row and running onboarding — no code changes, no new configurations, no developer involvement.

**9. Outcome tracking.**
The system remembers every recommendation it made and whether the owner acted on it. It tracks whether acting on the recommendation produced the expected result. This feedback loop continuously improves confidence scoring and agent calibration.

**10. Worth ₹999/month from week one.**
Even before all external signals are wired in, the cultural intelligence layer combined with internal data analysis must deliver more value than the owner currently has from any tool. The MVP brief must be demonstrably better than anything else available to a small Indian restaurant at this price point.

---

## 3. The Restaurant Profile — Foundation of Everything

The restaurant profile is the most important data structure in the system. Every insight, every recommendation, every quality gate decision references it. It is built through the WhatsApp onboarding conversation and refined continuously.

### Hard Facts (structured data)
- Restaurant name, location (city, area, full address)
- Cuisine type and sub-type (e.g., "Café — specialty coffee, all-day brunch")
- Business model: dine-in / delivery / both
- Delivery platforms active: Swiggy, Zomato, other
- Seating capacity (dine-in)
- Average order value (approximate, owner-reported initially, calculated from data after)
- Peak slots: morning / lunch / evening / dinner (which matter most)
- Team size: kitchen, front-of-house
- PetPooja restaurant ID, API credentials
- Owner WhatsApp number, name

### Identity Data (qualitative — from onboarding conversation)
- Restaurant description in owner's own words ("what would you tell a friend about this place?")
- Target customer archetype (described, not categorised)
- Positioning: premium / mid-market / value — but in the owner's language
- What makes this restaurant different from others in the area
- Three-year vision: what does success look like
- Non-negotiables: what the owner will never compromise on (ingredient quality, specific dishes, ambience)
- Current biggest pain: what keeps the owner up at night about the business
- Aspiration: one thing that would change the business if solved

### Catchment Intelligence (system-inferred, owner-validated)
- Primary delivery radius (from Swiggy/Zomato data or owner input)
- Primary dine-in catchment radius
- Estimated community composition of catchment (from Census ward data + owner validation)
- Demographic profile: residential / corporate / transit / mixed
- Income stratification: approximate customer spending power

### Owner Preferences (learned over time)
- Communication frequency preference (learned from response patterns)
- Topics they engage with most (calibrated from WhatsApp response history)
- Topics they consistently ignore (downweighted over time)
- Preferred message timing (inferred from when they respond)
- Language preference: English / Hinglish / Hindi (detected from onboarding responses)

---

## 4. The Seven Agents

### 4.1 Ravi — Revenue & Orders

**Mandate:** Watch order flow continuously. Know what normal looks like for this restaurant. Fire when something deviates from normal in a way that matters.

**Data sources:**
- PetPooja orders (synced every 4 hours during trading hours)
- Day-part breakdown: breakfast, lunch, evening, dinner slots
- Platform split: dine-in, delivery, takeaway
- Payment mode patterns
- Discount and void patterns
- Salary cycle position (overlay from Priya — week 1 vs week 4)
- Weather forecast from IMD API (rain today = delivery spike expected)
- IPL/cricket match schedule (evening ordering pattern shift)

**What Ravi looks for:**
- Revenue anomalies vs. this restaurant's own 8-week baseline (not industry benchmarks)
- Day-part underperformance — a lunch slot running 25%+ below trend for 3+ consecutive days
- Sudden platform mix shift — dine-in dropping while delivery flat signals a floor problem
- Payment mode anomaly — cash suddenly dominating signals aggregator issue or new competitor
- Discount creep — total discount percentage trending up without a corresponding volume increase
- Void spike — cancelled/modified items above threshold signals kitchen or service issue
- Revenue vs. weather correlation — delivery not spiking on a rainy day when it historically should

**Ravi's finding format:**
- Minimum 3 data points before flagging (not 1 bad day)
- Always includes baseline comparison (this Tuesday vs last 4 Tuesdays)
- Always includes ₹ impact estimate
- Urgency: immediate if >20% deviation; this_week if 10-20%; strategic if trend over 3+ weeks

**What Ravi never does:**
- Fire on a single day's data
- Compare to industry benchmarks — only this restaurant's own history
- Send findings about normal seasonal variation that Priya has already flagged

---

### 4.2 Maya — Menu & Margin Guardian

**Mandate:** Own the menu's financial health. Know the contribution margin of every dish. Catch margin erosion before it shows in the P&L. Guide what to push, what to retire, what to price differently.

**Data sources:**
- PetPooja menu + order item data (via Menu Intelligence Layer — semantic, not raw)
- APMC daily wholesale prices — ghee, chicken, vegetables, dairy, spices
- Dish-level contribution margin (calculated daily: selling price - food cost)
- Review corpus — dish-specific sentiment from Zomato/Swiggy/Google (scraped weekly)
- BCG matrix position per dish — recalculated weekly
- Competitor pricing for comparable dishes within delivery radius

**What Maya looks for:**
- Margin erosion: a dish that was 65% CM dropping to 48% CM over 3 weeks due to ingredient cost increase
- Star dishes being under-promoted: high-margin, high-popularity dishes not being pushed on aggregator platforms
- Dead SKUs: items on menu with <3 orders in 30 days — occupying menu real estate and confusing customers
- Review-sales divergence: a dish with poor recent reviews still being sold at high volume — a rating crisis in the making
- Price-point gap: a category where the restaurant has no offering between ₹X and ₹Y while competitors do
- Cannibalisation: two dishes competing for the same customer, with the lower-margin one winning
- Modifier economics: add-ons that customers are choosing which cost more than the margin they add

**BCG Matrix Logic:**
- Stars: top 25% order volume AND top 25% margin — push hard
- Cash Cows: top 25% volume, bottom 50% margin — protect, slowly optimise price
- Question Marks: bottom 50% volume, top 25% margin — investigate why, fix or retire
- Dogs: bottom 25% volume AND bottom 25% margin — retire unless identity-critical

**What Maya never does:**
- Recommend retiring a dish that the owner flagged as identity-critical in onboarding
- Recommend price increases above what Kiran's competitive intelligence supports
- Send margin findings without also including the specific action (not just "your margin dropped" — "your butter CM dropped from 68% to 51% because ghee is up 22% — here are two actions")

---

### 4.3 Arjun — Stock & Waste Sentinel

**Mandate:** Watch the supply chain and kitchen prep. Connect ingredient cost signals to menu decisions before they become problems. Generate accurate prep recommendations that reduce waste.

**Data sources:**
- PetPooja inventory and purchase data
- APMC daily wholesale prices (same feed as Maya — Arjun focuses on procurement timing, Maya on margin impact)
- Prep vs. actual consumption per dish (calculated from orders vs. inventory movements)
- Cultural calendar input from Priya (Navratri in 9 days = adjust chicken purchase this week)
- Weather forecast (rain = delivery surge = prep more delivery-friendly items)
- Historical waste patterns by dish, day, and weather condition

**What Arjun produces:**
- Morning prep recommendation (daily): specific quantities per dish based on forecast demand. Format: "Today: prep 35 Dal Makhani portions (Thursday + light rain + your historical Thursday rain pattern). Reduce Fish Curry to 12 portions (last 3 Thursdays avg was 9)."
- Supplier price spike alerts: "Tomato wholesale up 34% at Vashi APMC this morning. Your Shakshuka and Tomato Soup are affected. Estimated weekly impact: ₹4,200. Consider switching to Roma tomatoes from Pune mandi at ₹8/kg less."
- Purchase timing recommendations: "Buy ghee now. MCX futures show 8% price rise expected in next 3 weeks. Your monthly ghee consumption is 45kg. Buy 90kg now to lock in current price."
- Waste pattern reports: "You prep 50 portions of Fish Curry every Saturday. Average sale: 14. 36 portions wasted weekly. ₹2,800/week in food waste from this dish alone."

**What Arjun never does:**
- Recommend ingredient cuts that compromise quality on items flagged as non-negotiable
- Send prep recommendations without grounding them in historical data

---

### 4.4 Priya — Cultural & Calendar Intelligence

**Mandate:** Be 14 days ahead of every cultural, seasonal, and behavioral event that affects this restaurant's customers. Filter every signal through the specific demographic composition of this restaurant's catchment. Never be reactive.

**Data sources:**
- Indian Cultural Food Behavior Model (see `CULTURAL_MODEL.md`) — 17+ triggers, 8 cities, 10 communities
- Drik Panchang API — exact tithi, fasting days, festival dates with regional variations
- Restaurant catchment demographic profile (from restaurant profile)
- Salary cycle position (current week of month, salary date for corporate catchments)
- IMD weather seasonal patterns — monsoon onset/retreat dates, seasonal eating behavior shifts
- Local event calendar — IPL schedule, major concerts, college exam seasons, public holidays
- Instagram food trend signals from city-specific accounts (weekly scrape)

**What Priya always outputs:**
A structured 14-day forward calendar for this restaurant, scored by behavioral impact. Each event entry contains:
- Event name and date
- Expected behavior change (specific: "-28% non-veg orders", "+40% delivery", etc.)
- Catchment relevance score (0-100, weighted by this restaurant's community composition)
- Specific dishes expected to surge / drop
- Recommended action with lead time ("Add Sabudana Khichdi to menu by Wednesday — 2 days before Navratri")
- Expected ₹ impact if action taken vs. not taken

**What Priya never does:**
- Apply generic national festival assumptions to a restaurant with a specific catchment demographic (Navratri affects a restaurant in Ahmedabad differently than one in Chennai with 30% South Indian customer base)
- Send cultural alerts for events with <20% catchment relevance without high confidence corroboration from other signals

**Priya's generational intelligence:**
For each cultural trigger, Priya maintains separate behavioral models for:
- 55+ (traditional observers — strict fasting, dine-in preference, spend on quality)
- 35-55 (moderate observers — partial fasting, mix of dine-in and delivery)
- 18-35 (loose observers — plant-based framing, Instagram-driven, delivery-first)
The restaurant profile includes owner's sense of their primary customer age band, which weights these models.

---

### 4.5 Kiran — Competition & Market Radar

**Mandate:** Watch everything happening outside the restaurant's four walls that affects its competitive position. No surprises. The owner should never discover a new competitor or a competitor's price change from a customer.

**Data sources:**
- Google Places API — new restaurant listings within delivery and dine-in radius, rating changes, popular times, new reviews
- Zomato and Swiggy discovery pages — trending restaurants in this area, new openings, featured placements
- Google Trends API — dish-level search volume by city (tracks when a cuisine trend enters a market)
- Instagram food content scrapers — what food creators in this city are posting (leading indicator for trends)
- SERPER API — web search for food news in this city, new restaurant press coverage
- Competitor review monitoring — weekly sentiment analysis on top 5 competitors

**What Kiran looks for:**
- New restaurant openings within delivery radius (immediate) or dine-in radius (within 48 hours of listing appearing on Google Maps)
- Rating trajectory of top competitors — a competitor going from 3.8 to 4.3 in 6 weeks is a threat
- Price moves — competitor dropping or raising prices on comparable items
- Trend emergence — when a dish type goes from niche to mainstream search volume (birria tacos, smash burgers, Korean fried chicken)
- Aggregator positioning changes — competitor getting featured placement on Swiggy/Zomato home feed
- Review theme emergence — multiple customers at competitors mentioning a specific positive (service, value, ambience) that this restaurant could act on

**Kiran's relevance filter:**
Not every competitive signal is relevant to every restaurant. Kiran filters through identity:
- A new biryani cloud kitchen is relevant to a biryani restaurant, not a specialty coffee café
- A premium new café is relevant to YoursTruly, not to a budget QSR
- A Korean fried chicken trend is relevant if the restaurant is positioned as experimental, not if they're a traditional South Indian

**Output format:**
"Threat / Opportunity / Watch" categorisation with specific recommended response.

---

### 4.6 Chef — Recipe & Innovation Catalyst

**Mandate:** Be the creative brain. Proactively suggest new dishes, seasonal specials, and format experiments that fit this restaurant's identity, are financially viable, and are timed to market opportunity.

**Data sources:**
- National food trend signals from Kiran (what's emerging nationally)
- Seasonal ingredient availability and pricing from Arjun (what's cheap and good right now)
- Cultural calendar from Priya (what food moments are coming)
- Restaurant identity profile (what fits this restaurant's positioning and cuisine)
- Current menu gap analysis from Maya (what occasions/day-parts/dietary needs are unserved)
- Review corpus — what customers are asking for in reviews that isn't on the menu
- Knowledge base — research papers, food anthropology, cuisine trends

**What Chef never does:**
- Suggest a dish that contradicts the restaurant's identity or cuisine (no sushi suggestions for a Maharashtrian thali restaurant)
- Suggest without financial modelling — every suggestion includes projected CM% based on current ingredient costs
- Suggest without timing rationale — every suggestion is connected to a specific upcoming cultural moment, season, or market opportunity

**Chef's output format:**
"Add [Dish Name] to your [menu position] by [date]. Suggested price: ₹[X]. Projected contribution margin: [Y]%. Rationale: [2 sentences on market timing]. Ingredients needed: [list with current market prices]. Prep complexity: [low/medium/high]."

---

### 4.7 Sara — Customer Intelligence

**Mandate:** Understand who is actually coming to this restaurant, what drives their loyalty, who is at risk of leaving, and what the highest-value customer looks like so the restaurant can find more of them.

**Data sources:**
- PetPooja customer data (via Customer Identity Resolution layer — deduplicated)
- Order history per customer — frequency, recency, average spend, preferred items
- RFM segmentation (recency / frequency / monetary) — recalculated weekly
- Cohort retention analysis — of customers who first came in month X, how many came back in month X+1, X+2, etc.
- For delivery restaurants: aggregator customer behavior, repeat rate by platform
- Review corpus — sentiment patterns that distinguish loyal customers from one-time visitors

**What Sara looks for:**
- Lapsed regulars: customers who visited 4+ times in the past 6 months and haven't been back in 45+ days
- New customer conversion: what % of first-time customers return for a second visit within 30 days (the most important retention metric)
- High-LTV customer profile: what do the top 20% of customers by spend have in common (time of visit, dishes ordered, order channel)
- Cohort deterioration: is a recent month's cohort retaining worse than previous cohorts — an early warning of product or service decline
- Platform loyalty: for delivery restaurants, which platform produces more loyal customers (not just more orders)

**Sara's limitation acknowledgement:**
For restaurants with significant cash/anonymous transactions, customer data will be incomplete. Sara adjusts confidence scores accordingly and is explicit about data coverage.

---

## 5. The Menu Intelligence Layer

This module sits between raw PetPooja data and all agents. It is the most important module in the system for data quality.

### The Problem It Solves
PetPooja data reflects operational reality, not logical structure. A restaurant might have:
- `Pour Over Coffee` at ₹280 (real item)
- `Pour Over Coffee` at ₹0 (ghost entry from a modifier created incorrectly)
- `Iced Pour Over` (variant — should be child of Pour Over)
- `Hot Pour Over` (variant — should be child of Pour Over)
- `Pour Over - Extra Shot` (modifier — not a standalone item)

A naive system treats these as 5 different revenue items. The Menu Intelligence Layer understands they are one product family.

### Graph Construction Algorithm
On first sync for a new restaurant, the system runs:

**Step 1 — Ghost detection:**
Items with ₹0 price are flagged as probable ghosts. Items with >90% co-occurrence with another item are flagged as probable modifiers. Confidence scored 0-100.

**Step 2 — Variant clustering:**
Items sharing root words (Levenshtein distance <3, or explicit temperature/size/style qualifiers like "Iced/Hot/Small/Large/Full/Half") are clustered into a parent concept with variant children.

**Step 3 — Modifier identification:**
Items that appear in >75% of orders alongside a specific parent item and are never ordered standalone are classified as modifiers of that parent.

**Step 4 — Category validation:**
PetPooja category assignments are cross-checked against item names. Miscategorised items (e.g., a dessert in the "Beverages" category) are flagged for owner validation.

### Owner Validation via WhatsApp
After graph construction, the system sends validation questions only for low-confidence inferences (score <70). Example:
- "Quick question about your menu — I see 'Extra Shot' appearing. Is this always added to a coffee order, or do customers sometimes order it standalone? (Reply: always with coffee / sometimes standalone)"
- "I see 'Pour Over Coffee' listed twice — one at ₹280 and one at ₹0. Should I ignore the ₹0 one? (Reply: yes ignore / no it's different)"

Maximum 8 validation questions per onboarding. Questions are binary or simple choice wherever possible.

### Continuous Learning
Every time the owner clarifies something in WhatsApp ("you got that wrong, the Fish Curry and the Fish Tacos are completely different dishes not the same thing"), the system:
1. Updates the menu graph immediately
2. Stores the correction as a permanent learned fact
3. Recalculates any findings that were based on the incorrect inference
4. Never makes that specific error again for this restaurant

---

## 6. The Knowledge Base

### Purpose
Agents reason not just on live operational data but in the context of a curated research corpus. This makes recommendations research-backed rather than purely pattern-based. It is a significant proprietary asset that compounds over time.

### What Goes In
- NRAI India Food Services Reports (annual)
- NSSO Household Consumption Surveys (food expenditure sections)
- FSSAI annual reports and food safety consumption data
- Academic research on Indian food consumer psychology and eating behavior
- RBI Consumer Confidence Survey reports (eating-out intent sections)
- ET Hospitality, Food & Beverage News curated articles
- Government Census data on community composition (ward-level)
- APMC historical price data (3+ years)
- The Indian Cultural Food Behavior Model (YTIP proprietary)
- Curated food anthropology research on Indian regional food cultures
- Restaurant industry benchmarks (from public sources)

### Storage Architecture
pgvector extension on existing PostgreSQL instance. Each document is:
- Chunked at ~500 tokens with 50-token overlap
- Embedded using a text embedding model
- Tagged with: source, publication_date, topic_tags[], agent_relevance[] (which agents care about this)
- Searchable by semantic similarity + topic tag filter

### How Agents Use It
When reasoning about a finding, agents can issue a knowledge base query: "Navratri eating behavior urban Maharashtra" or "millet food trends India 2025". The relevant chunks are included in the agent's reasoning context. This prevents agents from making generic recommendations and pushes them toward research-grounded specificity.

### Maintenance
Admin endpoint `POST /api/admin/knowledge-base/ingest` accepts a PDF upload or URL. The system chunks, embeds, and tags automatically. Takes under 60 seconds per document. No developer involvement required for ongoing maintenance.

---

## 7. The Quality Council — 3-Stage Vetting Gate

Nothing reaches the owner without passing all three stages. This is the most important function in the system for maintaining owner trust.

### Stage 1 — Significance Check (automated, mathematical)

**Questions asked:**
- Is the deviation statistically significant against this restaurant's own 8-week baseline?
- Is this finding based on at least 3 data points (not a single day/event)?
- Does the magnitude cross the minimum threshold? (Default: >15% deviation for revenue findings, >10% CM change for margin findings, >20% for volume findings)

**Outcome:** Pass / Hold (wait for next cycle, recheck) / Reject (noise)

Held findings are re-evaluated in the next cycle. If they strengthen, they move forward. If they weaken, they are rejected. A finding can be held for a maximum of 3 cycles before being rejected.

### Stage 2 — Cross-Agent Corroboration

**Questions asked:**
- Does at least one other agent's data point in the same direction as this finding?
- Are there any findings in the pool from the last 7 days that this finding connects to or amplifies?
- Does this finding contradict any finding from another agent? (If yes, hold both and flag for review — contradictions are signals of data quality issues)

**Examples of corroboration:**
- Ravi flags revenue drop → corroborated if Arjun also flagged waste increase (demand-supply mismatch)
- Maya flags margin erosion on a dish → corroborated if Arjun flagged the same ingredient price spike
- Kiran flags new competitor → corroborated if Ravi flags delivery revenue drop in the same week

**Outcome:** Pass (corroborated) / Hold (no corroboration yet — give one more cycle) / Escalate (contradiction detected — flag for manual review)

Solo findings that find no corroboration in one additional cycle are still passed if they are high-urgency (>30% revenue deviation, new competitor, food safety signal).

### Stage 3 — Actionability + Identity Filter

**Questions asked:**
- Does this finding contain a specific action (not vague guidance)?
- Does the action have a deadline?
- Does the action have an estimated ₹ impact?
- Does the recommended action conflict with any of the owner's stated non-negotiables?
- Has a similar finding already been sent to this owner in the last 7 days?
- Is the timing appropriate — is there enough lead time for the owner to act?
- Does the action fit this restaurant's operational capacity?

**Identity filter examples:**
- Owner stated: "I will never use lower quality ingredients" → Any finding recommending cheaper ingredient substitution is modified to explore price increase instead
- Owner stated: "We are a dine-in focused experience restaurant" → Delivery optimisation findings are deprioritised; dine-in experience findings are elevated
- Owner stated: "My focus is specialty coffee — food is secondary" → Food margin findings are sent at strategic urgency, never immediate

**Outcome:** Pass / Rework (finding is valid but action needs reformulation) / Reject (fails identity filter)

Rework findings are reformulated by the synthesis layer before sending. They are not sent in their original form.

---

## 8. Message Synthesis & WhatsApp Voice

### The Single Voice Principle
All findings that pass the Quality Council are synthesised into one coherent message by the synthesis layer. The owner never sees:
- Multiple separate findings in quick succession
- Agent names or system internals
- Technical language or data science terminology
- Hedging, caveats, or uncertainty (uncertainty is expressed as confidence, not hedging)

### Message Architecture
Every WhatsApp message from YTIP follows this structure:

**Opening:** One sentence stating the most important thing. No preamble. No "I've been analysing your data." Just: "Your butter coffee is quietly becoming your best business decision."

**Evidence:** 2-3 sentences with specific numbers. "It's now your #2 ordered item at ₹320 with a 74% contribution margin — your highest margin beverage. In the last 30 days it's generated ₹38,400 in contribution."

**Action:** One specific thing to do. "Move it to the top of your Swiggy menu listing this week — it's currently listed 7th in beverages."

**Impact:** The ₹ reason. "Based on your current Swiggy traffic, top-3 listing position typically adds 15-25% to item visibility. That's potentially ₹5,000-8,500 additional monthly contribution from one menu position change."

**Conversation hook (optional):** "Reply if you want me to look at your full beverage ranking."

### What the Message Is Never
- Longer than can be read in 90 seconds
- Multiple asks in one message
- Vague ("your performance seems lower than usual")
- Condescending ("as a restaurant owner, you should know...")
- Alarming without being actionable ("your business is at risk")
- Self-referential ("our AI system has detected...")

### Message Batching Logic
If multiple validated findings exist simultaneously, the system does not send them all at once. It:
1. Ranks findings by urgency + estimated ₹ impact
2. Sends the highest-ranked finding
3. Waits for owner response or 4 hours, whichever comes first
4. Sends the next finding if owner responded or if urgency is immediate
5. Holds lower-priority findings for the scheduled weekly brief

### The Weekly Brief
Every Monday morning, regardless of what was sent during the week, the owner receives a weekly synthesis brief. This is the most comprehensive message of the week. It includes:
- Last week's performance vs. the week before and the same week last year
- Top 3 wins of the week
- Top 3 things to improve
- What's coming this week (Priya's 7-day forward calendar)
- One Chef suggestion for the week
- Any unacted-on findings from the past week (summarised, not repeated verbatim)

---

## 9. WhatsApp Onboarding Flow

Full conversation design in `ONBOARDING_FLOW.md`. Summary of what onboarding must accomplish:

1. Capture all hard facts (restaurant name, location, cuisine, business model, platforms)
2. Elicit identity data through conversational questions — not forms
3. Establish non-negotiables explicitly
4. Run menu graph bootstrap (automated) and validate low-confidence inferences (5-8 questions)
5. Validate catchment demographic assumptions
6. Set owner communication preferences
7. Send the first intelligence brief within 24 hours of completed onboarding

Onboarding must feel like a conversation with a thoughtful person, not a form being filled. Voice notes must be accepted and transcribed. The owner can complete onboarding over multiple sessions — state is preserved.

---

## 10. The Webapp

The webapp is the depth layer. The owner goes there when they want to understand something the WhatsApp brief surfaced. It is not the primary experience.

### Webapp Pages (existing — keep)
- Home / Executive Summary
- Revenue Intelligence
- Menu Engineering
- Cost & Margin
- Leakage & Loss Detection
- Customer Intelligence
- Operational Efficiency
- AI Chat

### New Pages (build)
- Intelligence Feed — chronological log of all findings sent, with outcome tracking
- Onboarding — for initial setup if owner prefers web over WhatsApp
- Knowledge Base — admin view of ingested documents, upload interface
- Restaurant Profile — view and edit the captured profile

### Webapp Access
No complex auth. A unique link per restaurant, protected by a simple token in the URL. The owner bookmarks it. Login is via WhatsApp OTP if needed.

---

## 11. Multi-Restaurant Architecture

The system is designed for multiple restaurants from day one, even though the first deployment is single-restaurant.

### What makes it multi-tenant:
- `restaurant_id` on every database table
- Restaurant profile drives all intelligence (no restaurant-specific code)
- WhatsApp routing table: phone_number → restaurant_id → role
- Separate PetPooja credentials per restaurant in the profile
- Per-restaurant menu graph (completely separate)
- Per-restaurant findings pool (completely separate)
- Per-restaurant knowledge base contributions (each restaurant can have private documents)

### Adding a new restaurant:
1. Create restaurant profile row
2. Run WhatsApp onboarding conversation
3. Bootstrap menu graph
4. Schedule agents for that restaurant_id
5. Done — no code changes

### Multi-restaurant owner support:
When a single owner WhatsApp number is linked to multiple restaurants, incoming messages trigger a restaurant selector: "Which café are you asking about? Reply 1 for YoursTruly, 2 for Café Allora, 3 for The Good Bowl."

Once selected, that session stays on that restaurant for 30 minutes before reverting to the selector.

---

## 12. External Data Feeds

| Source | What it provides | Agent(s) | Update frequency |
|--------|-----------------|----------|-----------------|
| APMC API | Wholesale vegetable, meat, dairy prices | Arjun, Maya | Daily |
| IMD API | Weather forecast 3 days ahead | Arjun, Ravi, Priya | Daily |
| Drik Panchang API | Hindu/Jain festival calendar, fasting days | Priya | Weekly |
| Google Places API | Competitor listings, ratings, new openings | Kiran | Weekly full scan, continuous new listing monitoring |
| Google Trends | Dish/cuisine search volume by city | Kiran, Chef | Weekly |
| SERPER/Web search | Food news, restaurant press coverage | Kiran | Weekly |
| Instagram scraper | Food content trends in city | Kiran, Chef | Weekly |
| Swiggy/Zomato public | Trending restaurants, discovery signals | Kiran | Weekly |
| MCX futures | Commodity price signals (edible oils, spices) | Arjun | Weekly |
| Research corpus | Academic papers, NRAI reports, govt data | All agents (via KB) | On-demand ingestion |

---

## 13. MVP Definition

**MVP is complete when:**
1. WhatsApp onboarding conversation works end-to-end for YoursTruly
2. Menu graph is bootstrapped and validated for YoursTruly
3. Ravi, Maya, Arjun, Sara are running on live PetPooja data
4. Priya is running with the cultural calendar
5. Quality Council is vetting all findings
6. The owner receives a weekly Monday brief that is genuinely better than anything they have today
7. The owner can ask follow-up questions via WhatsApp and get intelligent responses

**MVP explicitly excludes:**
- Kiran (competition monitoring) — Phase 2
- Chef (recipe innovation) — Phase 2
- External data feeds beyond IMD weather — Phase 2
- Knowledge base ingestion UI — Phase 2
- Outcome tracking — Phase 2

**The MVP test:**
Show the first Monday brief to the YoursTruly owner. If they say "how did you know that?" or "I didn't realise that" or "I need to act on this" — MVP is a success. If they say "yeah I knew all this" — we have failed.
