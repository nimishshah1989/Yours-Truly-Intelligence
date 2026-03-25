# YTIP — Indian Cultural Food Behavior Model

> Proprietary asset. This model powers Priya's 14-day forward intelligence.
> All behavioral scores are on a scale of -3 (severe drop) to +3 (strong surge).
> City weights are 0.0 (no relevance) to 1.0 (maximum relevance).

---

## Model Overview

This model maps Indian cultural, religious, seasonal, and economic events to specific food consumption behavior changes. It is:

- **Community-weighted:** Impact is scaled by the actual community composition of each restaurant's catchment
- **City-weighted:** The same event has different relevance in different cities
- **Generationally-split:** Behavior differs between 55+, 35-55, and 18-35 age cohorts
- **Restaurant-filtered:** All outputs are filtered through the restaurant's identity profile

**Version:** 1.0 — March 2026
**Coverage:** 18 behavioral triggers, 8 cities, 10 communities

---

## Community Composition by City (estimated baselines)

> These are starting estimates. Each restaurant's actual catchment is validated during onboarding and overrides these defaults.

| Community | Mumbai | Delhi | Bangalore | Hyderabad | Pune | Ahmedabad | Chennai | Kolkata |
|-----------|--------|-------|-----------|-----------|------|-----------|---------|---------|
| Hindu North | 22% | 45% | 18% | 12% | 22% | 30% | 8% | — |
| Hindu South | 9% | 6% | 38% | 35% | — | — | 55% | — |
| Hindu Maharashtrian | 28% | — | — | — | 35% | — | — | — |
| Hindu Bengali | — | — | — | — | — | — | — | 52% |
| Jain | 8% | 4% | 3% | 2% | 7% | 25% | 2% | 2% |
| Muslim | 21% | 13% | 14% | 30% | 12% | 15% | 10% | 27% |
| Christian | 5% | 3% | 8% | 6% | 4% | — | 10% | 5% |
| Sikh | 2% | 8% | 2% | — | 3% | 2% | — | — |
| Parsi | 2% | — | — | — | — | — | — | — |
| Other | 3% | 21% | 17% | 15% | 17% | 28% | 15% | 14% |

---

## Event Catalog

---

### EVENT: Navratri — Sharada (October)

**Duration:** 9 days
**Primary communities:** Hindu North, Hindu Maharashtrian, Jain
**City weights:** Mumbai 0.90, Delhi 0.95, Bangalore 0.60, Hyderabad 0.50, Pune 0.85, Ahmedabad 1.00, Chennai 0.30, Kolkata 0.40

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | -2.8 | Severe drop for observing households |
| Onion/garlic demand | -2.2 | Many observe no onion/garlic |
| Satvik food demand | +2.8 | Strong surge |
| Delivery vs. dine-out | +0.5 | Slight delivery preference |
| Average spend | -0.3 | Slight drop overall |

**Surge dishes:** Sabudana Khichdi, Kuttu Puri, Singhare ke Atte ka Halwa, Sama Rice Khichdi, Aloo (Sendha Namak), Makhana Kheer, Makhana Curry, Fruit Chaat, Rajgira Roti, Lauki Halwa

**Drop dishes:** Chicken Biryani, Mutton, Fish Curry, Egg dishes, All onion/garlic based gravies

**Owner action template:**
Add a Navratri Thali (₹220-280) 3 days before start. Ingredients: Sabudana, Kuttu flour, Makhana, Sendha Namak, Rock salt, Rajgira — all available. CM target: 62-68%.

**Lead time required:** 7 days (menu update + ingredient procurement)

**Generational split:**
- 55+: Strict — no non-veg, no onion, no garlic for full 9 days. Will seek out specifically satvik menus.
- 35-55: Moderate — non-veg drop, may still use onion/garlic. Look for satvik options but don't demand them.
- 18-35: Loose — some observe first and last day only. Receptive to "plant-based" framing rather than "satvik."

---

### EVENT: Navratri — Chaitra (March/April)

**Duration:** 9 days
**Primary communities:** Hindu North, Hindu Maharashtrian, Jain
**City weights:** Mumbai 0.75, Delhi 0.90, Bangalore 0.50, Hyderabad 0.40, Pune 0.75, Ahmedabad 0.90, Chennai 0.25, Kolkata 0.35

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | -2.2 | Moderate drop — less strictly observed than Sharada |
| Onion/garlic demand | -1.8 | Moderate |
| Satvik demand | +2.3 | Good surge |

**Note:** Observed less strictly than Sharada Navratri in urban areas. 35+ demographic is the primary observer cohort.

---

### EVENT: Ramzan / Ramadan (30 days, date varies by Islamic calendar)

**Duration:** 30 days
**Primary communities:** Muslim
**City weights:** Mumbai 0.95, Delhi 0.85, Bangalore 0.70, Hyderabad 1.00, Pune 0.70, Ahmedabad 0.70, Chennai 0.65, Kolkata 0.85

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | +2.5 | Surge during Iftar window |
| Lunch slot orders | -2.8 | Severe drop — fasting during day |
| Iftar slot (6-8pm) | +3.0 | Maximum surge — 90-min revenue window |
| Sehri slot (3-4am) | +1.5 | Untapped for most restaurants |
| Delivery vs. dine-out | +1.2 | Delivery surge |
| Average spend | +1.8 | Higher per-order spend during Iftar |
| Halal demand | +3.0 | Non-halal options lose Muslim customers entirely |

**Surge dishes:** Haleem, Nihari, Biryani, Sewaiyan, Sheer Khurma, Kebabs, Rooh Afza, Dates, Shorba, Paya, Fruit Chaat (sehri)

**Critical insight:** The 30-day period creates a completely different eating clock. Lunch revenue collapses for restaurants in Muslim-heavy catchments. Iftar window is a 90-minute surge unlike any other time of year. Restaurants near mosques see 3-4x normal dinner traffic during Iftar.

**Owner action template:**
For restaurants with >15% Muslim catchment: Create Iftar combo box (min 4-person) at ₹450-600. Pre-order via WhatsApp by 4pm daily. Consider Sehri delivery 3-4am if operational capacity allows.

---

### EVENT: Eid ul-Fitr (3 days, post-Ramzan)

**Duration:** 3 days
**Primary communities:** Muslim
**City weights:** Mumbai 0.95, Delhi 0.85, Bangalore 0.70, Hyderabad 1.00, Pune 0.70, Ahmedabad 0.70, Chennai 0.65, Kolkata 0.85

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Family dining | +3.0 | Maximum family dining day |
| Average spend | +2.5 | Celebration mode — spend freely |
| Non-veg demand | +3.0 | Maximum |
| Sweets demand | +2.8 | Sheer Khurma, Sewaiyan |
| Delivery vs. dine-out | -1.0 | Preference for dine-in on Eid day |

**Surge dishes:** Biryani, Mutton Korma, Sheer Khurma, Sewaiyan, Haleem, Kebabs, Phirni, Malpua

**Generational note:** Young urban Muslims increasingly celebrate Eid by taking family to restaurants. Restaurant Eid experiences are growing as a trend in metros.

---

### EVENT: Shravan Month (August, 30 days)

**Duration:** 30 days
**Primary communities:** Hindu North, Hindu Maharashtrian
**City weights:** Mumbai 0.90, Delhi 0.70, Bangalore 0.40, Hyderabad 0.35, Pune 0.85, Ahmedabad 0.80, Chennai 0.20, Kolkata 0.30

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | -2.5 | Sustained month-long drop |
| Monday non-veg specifically | -3.0 | Maximum drop — Shravan Somwar |
| Veg demand | +2.0 | Steady veg surge |
| Average spend | -0.5 | Slight drop |
| Delivery | +0.8 | Monsoon coincidence boosts delivery |

**Critical insight:** Monday is the highest-impact day. Many urban professionals observe only Monday Shravan (Shravan Somwar) even if they don't observe the full month.

**Surge dishes:** Dal Bati, Puri Sabzi, Sabudana dishes, Paneer dishes, Varan Bhaat, Modak (during Ganesh Chaturthi overlap), Khichdi

**Owner action template:**
Prominently feature veg menu throughout Shravan. Create "Shravan Monday Special" combo. Non-veg restaurants should not push non-veg on Mondays during Shravan.

---

### EVENT: Diwali (October/November, 5 days)

**Duration:** 5 days
**Primary communities:** Hindu North, Hindu Maharashtrian, Hindu South, Jain, Sikh
**City weights:** Mumbai 1.00, Delhi 1.00, Bangalore 0.85, Hyderabad 0.80, Pune 0.95, Ahmedabad 1.00, Chennai 0.70, Kolkata 0.60

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Sweets/mithai demand | +3.0 | Maximum |
| Pre-Diwali dining out | +2.0 | 10-day pre-Diwali window is peak |
| Diwali day itself — dining out | -1.0 | Families eat home on Diwali day |
| Post-Diwali 3 days | +1.5 | Families go out to celebrate |
| Gift hampers | +3.0 | Sweets boxes, dry fruit hampers |
| Average spend | +2.0 | Celebration premium |

**Critical insight:** Diwali DAY itself is a home day — restaurant footfall drops. The 10-day PRE-Diwali window (Dhanteras especially) is the dining-out peak. Plan menu and marketing for the pre-Diwali period, not the day itself.

**Surge dishes:** Mithai boxes, Kaju Katli, Gulab Jamun, Special Thali, Chakli, Chivda, Dry fruit sweets
**Unique opportunity:** Gift hampers — restaurants can sell festive sweet/snack hampers at 70%+ margin

---

### EVENT: Ganesh Chaturthi (August/September, 10 days)

**Duration:** 10 days
**Primary communities:** Hindu Maharashtrian
**City weights:** Mumbai 1.00, Delhi 0.20, Bangalore 0.40, Hyderabad 0.60, Pune 1.00, Ahmedabad 0.30, Chennai 0.25, Kolkata 0.20

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Modak demand | +3.0 | Maximum — Ganesh's favourite |
| Veg demand | +1.5 | First and last day especially |
| Non-veg demand | -1.0 | Moderate drop |
| Street food demand | +2.0 | Pandal-hopping culture |

**Surge dishes:** Modak (steamed and fried), Ukadiche Modak, Puran Poli, Karanji, Shrikhand, Thalipeeth

**Critical insight:** THIS IS HYPER-LOCAL. Massive in Mumbai and Pune, moderate in Hyderabad and Bangalore. Neighborhood restaurants near major Ganesh pandals see extraordinary walk-in traffic on Ganesh eve and visarjan day (Day 10).

**Timing note:** Day 1 and Day 10 (visarjan) are peak footfall days. Post-visarjan late night (11pm-1am) is a significant dining surge as processions return.

---

### EVENT: Durga Puja (September/October, 5 days)

**Duration:** 5 days
**Primary communities:** Hindu Bengali
**City weights:** Kolkata 1.00, Mumbai 0.50, Delhi 0.50, Bangalore 0.45, Hyderabad 0.30, Pune 0.30, Ahmedabad 0.10, Chennai 0.25

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | +2.5 | Bengalis eat fish and meat during Puja |
| Dining out | +3.0 | Every day of Puja, families eat out |
| Average spend | +2.5 | Celebration mode |
| Street food | +3.0 | Pandal-hopping street food culture |
| Delivery vs. dine-out | -2.0 | Strong preference for dine-in/street |

**Surge dishes:** Kosha Mangsho, Hilsa preparations, Chingri Malaikari, Luchi, Biryani, Mishti Doi, Sandesh, Phuchka, Telebhaja

**Critical insight for non-Kolkata cities:** Bengali diaspora is deeply nostalgic during Puja season. They will seek out authentic Bengali food and pay premium for it. A well-executed Puja special menu at a non-Bengali restaurant in Mumbai/Bangalore can attract this entire community.

---

### EVENT: Onam (August/September, 10 days)

**Duration:** 10 days
**Primary communities:** Christian (Kerala), Hindu South (Kerala)
**City weights:** Mumbai 0.60, Delhi 0.30, Bangalore 0.70, Hyderabad 0.40, Pune 0.40, Ahmedabad 0.10, Chennai 0.50, Kolkata 0.20

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Sadya demand | +3.0 | The one meal Malayalis will travel for |
| Veg demand | +2.0 | Sadya is a veg feast |
| Family dining | +2.5 | Multi-generation family occasion |
| Average spend | +1.5 | Premium for authentic Sadya |
| Delivery vs. dine-out | -1.5 | Strong dine-in preference |

**The Sadya imperative:** For Kerala restaurants, Onam Sadya served on banana leaf is non-negotiable. Price it at ₹600-1200 per head. Advance booking only. Sell-out = social signal (creates scarcity demand).

**Generational note:** Deep emotional connection across ALL age groups for Malayalis. Young Malayalis use Onam as a cultural identity moment — photographs of Sadya spread organically on Instagram.

---

### EVENT: Holi (February/March, 2 days)

**Duration:** 2 days (Holika Dahan + Holi)
**Primary communities:** Hindu North, Hindu Maharashtrian
**City weights:** Mumbai 0.85, Delhi 1.00, Bangalore 0.60, Hyderabad 0.50, Pune 0.80, Ahmedabad 0.90, Chennai 0.30, Kolkata 0.70

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Post-Holi afternoon dining | +2.5 | Groups come out after playing |
| Thandai demand | +3.0 | Maximum |
| Sweets demand | +2.0 | Gujiya, Malpua |
| Group dining | +2.5 | Friend groups |
| Delivery vs. dine-out | -1.0 | Preference for going out |
| Average spend | +1.5 | Celebratory |

**Timing insight:** Holi morning = people play, are home. Post-noon (2-7pm) = groups emerge. Peak dining window is 2-8pm. Not an evening event.

**Millennial/Gen Z pattern:** "Holi party" culture is significant in metros — rooftop events, brunch packages, poolside gatherings. Restaurants hosting Holi experiences or selling Holi-themed brunch packages do very well.

**Surge dishes:** Thandai, Gujiya, Malpua, Dahi Bhalle, Chaat, Puran Poli, Kanji Vada, Bhang (clearly marked, only where legal)

---

### EVENT: Christmas & New Year's Eve (December 24-31)

**Duration:** 10 days (peak: Dec 24, 25, 31)
**Primary communities:** Christian, all urban communities (pan-community celebration)
**City weights:** Mumbai 1.00, Delhi 0.95, Bangalore 0.95, Hyderabad 0.80, Pune 0.90, Ahmedabad 0.60, Chennai 0.85, Kolkata 0.90

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Dining out | +3.0 | Biggest dining-out period of year |
| Average spend | +2.8 | Maximum premium willingness |
| Group dining | +3.0 | Friend groups, office parties |
| Advance bookings | +3.0 | Customers expect to pre-book |
| Delivery vs. dine-out | -2.5 | Strong dine-in preference |
| Premium dining | +2.5 | Experience over value |

**Critical insight:** NYE (December 31) is the single biggest dining-out night of the year across ALL communities in urban India. Start taking advance bookings 3 weeks out. Minimum cover charge is standard and accepted. Prix fixe with alcohol pairing maximizes revenue per cover.

**This is NOT just a Christian festival:** Christmas-NYE has become a fully pan-community urban celebration. Every restaurant should treat this 10-day window as their most important revenue period of the year.

---

### EVENT: Lohri & Baisakhi (January 13-14)

**Duration:** 2 days
**Primary communities:** Sikh, Hindu North
**City weights:** Mumbai 0.50, Delhi 0.95, Bangalore 0.35, Hyderabad 0.25, Pune 0.40, Ahmedabad 0.35, Chennai 0.20, Kolkata 0.30

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Punjabi food demand | +2.5 | Peak traditional Punjabi food demand |
| Group dining | +2.0 | Community celebration |
| Average spend | +1.5 | Celebratory |

**Surge dishes:** Makki di Roti + Sarson Saag, Pinni, Gajak, Chikki, Lassi, Butter Chicken, Dal Makhani, Tandoori items

**Note:** Concentrated impact in cities with significant Punjabi population. Very high relevance for North Indian/Punjabi restaurants.

---

### EVENT: Ekadashi (bi-monthly, 2x per month)

**Duration:** 1 day, occurs twice monthly
**Primary communities:** Hindu North, Hindu Maharashtrian, Jain
**City weights:** Mumbai 0.80, Delhi 0.75, Bangalore 0.55, Hyderabad 0.50, Pune 0.80, Ahmedabad 0.85, Chennai 0.40, Kolkata 0.45

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | -1.8 | Moderate drop |
| Grain-free demand | +1.5 | No wheat, no rice |
| Satvik demand | +2.0 | |

**Surge dishes:** Sabudana Khichdi, Rajgira Roti, Sama Rice, Makhana dishes, Fruit-based dishes, Dry fruit sweets

**The compounding insight:** Ekadashi occurs 24 times per year. For restaurants in Gujarati or Maharashtrian-heavy catchments, this is a recurring, predictable behavior pattern that affects 2 days per month. A small Ekadashi menu (3-4 items) signals awareness to Vaishnav customers — they notice and they're loyal.

**Generational note:** Primarily observed by 40+ age group. Younger urban generation largely skips.

---

### EVENT: Jain Paryushana (August, 8 days)

**Duration:** 8 days (Shvetambara) / 10 days (Digambara)
**Primary communities:** Jain
**City weights:** Mumbai 0.90, Delhi 0.70, Bangalore 0.50, Hyderabad 0.30, Pune 0.75, Ahmedabad 1.00, Chennai 0.25, Kolkata 0.20

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Non-veg demand | -3.0 | Complete elimination |
| Root vegetable demand | -2.5 | No potato, onion, garlic, carrot, beet |
| Restaurant visits | -2.0 | Many strict Jains don't eat out at all during Paryushana |
| Average spend | -1.5 | |

**Critical insight:** This is the STRICTEST dietary period in the Indian calendar. Ahmedabad restaurants see noticeable revenue drops. Jains with high purchasing power go completely offline during Paryushana. Post-Paryushana (Paryushan ends with Samvatsari — forgiveness day) sees a surge as the community celebrates.

**For Jain-heavy catchments:** Don't fight Paryushana. Focus marketing energy on the post-Paryushana celebration window and pre-Paryushana period.

**Jain certification:** Restaurants with >8% Jain catchment should consider getting Jain certification for their menu. It unlocks a high-spending, loyal customer segment.

---

### RECURRING: Monthly Salary Cycle

**Type:** Recurring economic pattern, every month
**Communities:** All salaried urban workers
**City weights:** All cities 0.85-1.00

**Behavior impacts by week:**
| Week | Score | Pattern |
|------|-------|---------|
| Week 1 (1st-7th) | +2.5 | Post-salary spending — premium dishes, new items, dining out freely |
| Week 2 (8th-15th) | +0.5 | Slight above normal |
| Week 3 (16th-23rd) | -0.3 | Slight below normal |
| Week 4 (24th-31st) | -1.5 | Pre-salary tightening — value seeking, smaller orders |

**Action template:**
- Launch premium dishes and new items in Week 1
- Feature value combos, lunch specials, and bundle deals in Week 4
- The same customer has different willingness-to-pay across the month — price accordingly

---

### SEASONAL: Monsoon (June-September)

**Duration:** ~120 days
**Communities:** All
**City weights:** Mumbai 1.00, Delhi 0.85, Bangalore 0.80, Hyderabad 0.80, Pune 0.90, Ahmedabad 0.75, Chennai 0.70, Kolkata 0.85

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Delivery surge | +2.8 | Heavy rain = delivery spike 40-70% in Mumbai/Pune |
| Dine-out drop | -1.8 | People avoid going out in heavy rain |
| Chai/snack demand | +3.0 | India's most reliable food behavior pattern |
| Comfort food demand | +2.5 | Khichdi, hot soups, pakoda |
| Order frequency | +1.5 | Order more often, not necessarily more per order |

**Surge dishes:** Chai (mandatory), Pakoda/Bhajiya, Khichdi, Hot soups, Sandwiches, Corn dishes (monsoon classic), Vada Pav (Mumbai), Samosa

**Rain-day playbook:**
When IMD rain forecast is >70% probability for today:
- Prepare 40% more delivery-friendly packaging
- Reduce dine-in setup time allocation
- Push delivery promotions by 9am
- Send opt-in customer WhatsApp at 10am: "It's raining outside ☔ order in?"

**Generational note:** Millennials have romanticised monsoon food culture. "Chai and pakoda" content drives massive Instagram engagement every monsoon. This is free marketing — create content, not just menus.

---

### SEASONAL: Summer (March-June)

**Duration:** ~90 days
**Communities:** All
**City weights:** Mumbai 0.80, Delhi 1.00, Bangalore 0.50, Hyderabad 0.90, Pune 0.80, Ahmedabad 1.00, Chennai 1.00, Kolkata 0.90

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Cold beverage demand | +3.0 | Maximum |
| Mango demand | +3.0 | April-June mango season — India's most predictable food surge |
| Heavy food demand | -1.5 | Avoid heavy gravies in peak heat |
| Late evening dining | +1.5 | People emerge after sunset |
| Lunch slot | -1.2 | Drop in cities with extreme heat |

**Mango season (April-June) is the single most predictable food demand event in India.** Every cuisine, every community, every age group. A restaurant without a mango special in April-June is missing free revenue.

**Summer menu engineering:**
- 4-5 mango-based items (mandatory)
- Cold beverages: Aam Panna, Thandai, Nimbu Pani, Chaas — high margin
- Shift heavy items to dinner-only
- Smaller portions at lunch (heat suppresses appetite)

---

### SPORTING: IPL Season (March-May, ~60 days)

**Duration:** ~60 days
**Communities:** All urban
**City weights:** All cities 0.85-1.00 (highest for home city of playing team)

**Behavior impacts:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Match night delivery | +2.5 | Surge peaks at 7pm and 9:30pm (halftime) |
| Sports bar/match screening dine-in | +2.0 | Massive for venues showing match |
| Finger food demand | +2.5 | Sharing platters, wings, nachos |
| Post-7pm ordering | +2.0 | Ordering time shifts later on match nights |

**Match night playbook:**
- Match starts 7:30pm → delivery spike at 7pm (pre-match orders) and 9:30pm (halftime)
- "Match Night Special" combo — finger food for 2-4 people at ₹X
- If restaurant can show the match: covers double, dwell time doubles
- TV investment during IPL pays back in 2-3 weeks for sports-adjacent restaurants

**Generational note:** IPL watching is intensely social for 18-35 age group. Group ordering (4-8 people sharing) is the dominant pattern. Design large sharing portions.

---

## How Priya Uses This Model

### Catchment Relevance Calculation
```
relevance = sum(catchment_pct[community] for community in event.primary_communities) 
            / 100 
            × city_weight[restaurant.city]

Minimum relevance to act: 0.20 (20%)
High relevance: > 0.60
Maximum relevance: 1.00
```

### Impact Calculation for Specific Restaurant
```
For each behavior dimension:
  base_impact = event.behavior_impacts[dimension]
  
  # Scale by catchment relevance
  scaled_impact = base_impact × relevance
  
  # Adjust for restaurant business model
  if dimension == "delivery_surge" and not restaurant.has_delivery:
      scaled_impact = 0  # irrelevant for dine-in only
  
  if dimension == "non_veg_drop" and restaurant.cuisine_type == "pure_veg":
      scaled_impact = 0  # already a veg restaurant
```

### Lead Time Requirements by Action Type
| Action required | Lead time needed |
|----------------|-----------------|
| Add new dishes (requires procurement) | 7-10 days |
| Add new dishes (existing ingredients) | 2-3 days |
| Menu positioning change (aggregator) | 1 day |
| WhatsApp broadcast to customers | 1 day |
| Pricing change | 1 day |
| Staff planning (extra hands) | 5 days |
| Special event setup | 7 days |
| Inventory buildup | 3-5 days |

---

## Validation and Updates

This model was built from:
- NRAI India Food Services Reports
- NSSO Household Consumption Survey data
- Primary domain expert interviews (to be conducted — target: 3 food anthropologists, 5 experienced F&B operators)
- Validation against YoursTruly historical PetPooja data

**Version 1.1 updates will include:**
- Validated scores from YoursTruly's actual data vs. predictions
- Additional triggers: Gudi Padwa, Ugadi, Pongal, Bihu
- Corporate calendar overlay (appraisal season, quarter-end)
- Exam season impact (near college/coaching catchments)
- Regional food moment triggers (mango season regional variations, mustard season Bengal)
