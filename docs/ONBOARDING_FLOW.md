# YTIP — WhatsApp Onboarding Flow

> Complete conversation design for restaurant onboarding.
> Read this before touching any onboarding or WhatsApp routing code.

---

## Design Principles

1. **It's a conversation, not a form.** The owner should feel they're talking to a thoughtful person who is genuinely curious about their restaurant.
2. **Voice notes accepted everywhere.** The owner can respond by typing or by voice note. Both are equally valid. Voice is transcribed by Whisper.
3. **Progressive and resumable.** Onboarding can be completed over multiple sessions. State is preserved. Returning owners pick up exactly where they left off.
4. **Only ask what matters.** Every question has a direct purpose. No question that doesn't feed the intelligence engine.
5. **Binary and easy-to-answer questions where possible.** Open-ended questions only for identity data that cannot be captured any other way.
6. **Acknowledge and reflect.** The system echoes back what it understood, giving the owner a chance to correct.
7. **Maximum 25 minutes to complete.** This is the design ceiling. Average should be 15 minutes.

---

## Conversation State Machine

States in order. Each state has: question(s) to ask, expected response type, what to store, next state.

```
INITIAL → IDENTITY_CAPTURE → BUSINESS_FACTS → VISION_AND_VALUES →
CATCHMENT → MENU_VALIDATION → PREFERENCES → COMPLETE
```

---

## State 0: INITIAL — First Contact

**Trigger:** A new phone number messages the YTIP WhatsApp number for the first time.

**System sends:**

> Namaste! 🙏 I'm the intelligence platform for your restaurant — think of me as a team working in the background 24/7 to help you understand your business better and take better decisions.
>
> Before I can be useful to you, I need to understand your restaurant really well. This will take about 15 minutes and I'll ask you some questions — you can type or just send me voice notes, whatever's easier.
>
> Ready to start? (Reply: Yes / Not now)

**If "Not now":**
> No problem. Message me whenever you're ready — just say "start" and we'll begin. 😊

**If "Yes" → move to State 1**

---

## State 1: IDENTITY_CAPTURE — Who Are You

**Purpose:** Get the restaurant's name, owner name, and the first identity signal — how they describe their own place.

**System sends:**

> Perfect. Let's start with the basics.
>
> What's your restaurant called, and what should I call you?

**Expected:** "I'm Rohan, the café is YoursTruly" or similar free-form.

**Store:** `restaurant_name`, `owner_name`

**System reflects:**

> Great to meet you, [owner_name]! [Restaurant name] — love it.
>
> Now tell me about it like you'd tell a close friend who's never been there. What makes this place yours?

**Expected:** 2-5 sentence free-form description. This is the most important identity signal.

**Store:** `owner_description` (verbatim, and a parsed summary)

**System responds warmly and moves on:**

> That's a beautiful way to put it. I can already tell this isn't just another café. 
>
> → State 2

---

## State 2: BUSINESS_FACTS — Hard Operational Data

**Purpose:** Capture structured facts about how the restaurant operates.

**Q2a — Cuisine and positioning:**
> What kind of food do you serve? (e.g., specialty coffee and all-day brunch, North Indian, South Indian thali, multi-cuisine, etc.)

**Store:** `cuisine_type`, `cuisine_subtype`

**Q2b — Business model:**
> Do you do dine-in, delivery, or both?
>
> Reply: 1 — Dine-in only / 2 — Delivery only / 3 — Both

**Store:** `has_dine_in`, `has_delivery`, `has_takeaway`

**Q2c — Platforms (only if has_delivery):**
> Which delivery platforms are you on?
>
> Reply: 1 — Swiggy only / 2 — Zomato only / 3 — Both / 4 — Other

**Store:** `delivery_platforms`

**Q2d — Location:**
> Which city and area are you in? (e.g., Mumbai, Bandra West)

**Store:** `city`, `area`

**Q2e — Scale:**
> Roughly how many covers (seats) do you have for dine-in? And on a typical day, how many orders do you handle?
>
> (No need to be exact — approximate is fine)

**Store:** `seating_capacity`, initial `avg_daily_orders` estimate

**System reflects:**
> Got it. [Restaurant name] — [cuisine_type] in [area], [city]. [Delivery/dine-in/both]. About [X] covers.
>
> Does that sound right? (Yes / Let me correct something)

**If correction needed:** Ask what to fix, update, re-reflect.

**→ State 3**

---

## State 3: VISION_AND_VALUES — The Heart of the Profile

**Purpose:** Capture identity data that shapes every future insight. These answers are the most important data in the entire profile. Take time here.

**Q3a — Target customer:**
> Who is your ideal customer? Not a demographic profile — describe them as a person. Who do you picture when you think "this place is perfect for them"?

**Store:** `target_customer` (verbatim)

**Q3b — What makes it different:**
> What does [restaurant name] do differently from other [cuisine type] places in [area]? What would a regular customer say if someone asked them why they keep coming back?

**Store:** `differentiator` (verbatim)

**Q3c — Non-negotiables (critical for quality gate):**
> Every great restaurant has things the owner will never compromise on, no matter what. What are yours? Could be ingredient quality, a specific dish, the atmosphere, the service style — anything.
>
> Take your time with this one.

**Store:** `non_negotiables` as array (parse from free-form response, reflect back as bullet list for validation)

**System reflects non-negotiables:**
> I heard these as your non-negotiables:
> • [non_negotiable_1]
> • [non_negotiable_2]
> • [non_negotiable_3]
>
> Anything to add or change? These will guide every recommendation I make — I'll never suggest something that goes against these.

**Store validated `non_negotiables`**

**Q3d — Vision:**
> If everything goes well over the next 3 years, what does [restaurant name] look like? What does success mean to you — not just in revenue, but as a place?

**Store:** `vision_3yr` (verbatim)

**Q3e — Current pain:**
> And honestly — what keeps you up at night about the business right now? The one thing you wish you understood better or could fix?

**Store:** `current_pain` (verbatim — this directly guides which agents prioritise what)

**Q3f — Aspiration:**
> Last one in this section: if there was one thing that could change the business overnight — one insight or one decision that would make a significant difference — what would that be?

**Store:** `current_aspiration` (verbatim)

**System acknowledges:**
> Thank you for sharing all of this. This is exactly what I needed to understand not just your restaurant's data, but what it means to you.
>
> I'll make sure every insight I give you is filtered through what you've told me — especially those non-negotiables.
>
> → State 4

---

## State 4: CATCHMENT — Who Lives Around You

**Purpose:** Build the demographic model of the restaurant's catchment. This powers Priya's cultural calendar personalisation.

**Q4a — Neighbourhood:**
> Tell me a bit about the area around [restaurant name]. Is it mostly residential? Office/corporate? A mix? Near colleges or schools?

**Store:** `catchment_type` (residential/corporate/transit/mixed)

**Q4b — Community composition (this is a sensitive question — frame carefully):**
> To make sure I give you culturally relevant insights — for example, knowing when festivals like Navratri or Ramzan will affect your customer flow — it helps to know roughly what communities are represented in your customer base.
>
> Is your customer base predominantly Hindu, with a mix of communities? Or is there a significant Muslim, Jain, Christian, or other community presence that affects your business noticeably?
>
> (Just a rough sense is fine — this helps me give you accurate cultural insights)

**Store:** `catchment_demographics` as JSON map — infer from response and validate

**System reflects:**
> Got it. I'll factor this into all cultural and festival intelligence I share with you.

**Q4c — Salary cycle relevance:**
> Is your customer base mostly salaried corporate workers, or more mixed (self-employed, students, families)?
>
> Reply: 1 — Mostly salaried / 2 — Mixed / 3 — Mostly non-salaried / 4 — Not sure

**Store:** Used to calibrate salary cycle overlay intensity

**→ State 5**

---

## State 5: MENU_VALIDATION — Teaching the System Your Menu

**Purpose:** Bootstrap the menu graph and validate low-confidence inferences.

**System sets context:**
> Almost done! I've already started analysing your menu from PetPooja to understand your dishes and how they're structured.
>
> I have a few quick questions to make sure I've understood your menu correctly — some items can look different in the system than how you actually think about them.

**[Run menu graph bootstrap algorithm here — see ARCHITECTURE.md]**

**For each low-confidence inference (max 8 questions), ask one of these patterns:**

**Pattern A — Ghost item:**
> I see "[item name]" listed at ₹0 in your menu. Should I ignore this completely, or is it actually something customers order? (Reply: 1 — Ignore it / 2 — It's real, [price])

**Pattern B — Variant relationship:**
> Are "Iced [Item]" and "Hot [Item]" really the same drink in two forms, or are they genuinely different recipes you'd want to track separately? (Reply: 1 — Same drink, different forms / 2 — Different, track separately)

**Pattern C — Modifier vs. standalone:**
> "[Item]" — is this something customers always add to another item, or do they sometimes order it on its own? (Reply: 1 — Always an add-on / 2 — Can be standalone)

**Pattern D — Duplicate detection:**
> I see "[Item A]" and "[Item B]" — these look very similar. Are they the same dish or different? (Reply: 1 — Same dish / 2 — Different dishes)

**Pattern E — Category correction:**
> I have "[Item]" filed under [Category]. Is that right, or does it belong elsewhere? (Reply: 1 — Yes that's right / 2 — It's actually [correct category])

**After all validation questions:**
> 
> Thanks — I now have a clear picture of your menu. I know which items are real sellers, which are add-ons, and which to ignore. Every insight about your menu will use this understanding.
>
> → State 6

---

## State 6: PREFERENCES — How You Like to Communicate

**Purpose:** Set communication preferences so nudges feel right, not intrusive.

**Q6a — Frequency:**
> How often would you like to hear from me?
>
> Reply: 1 — Only when something important needs attention / 2 — A few times a week / 3 — Daily updates are fine

**Store:** `communication_frequency`

**Q6b — Best time:**
> When's the best time for me to send you messages? Morning before service, during slow afternoon hours, or evening after close?
>
> Reply: 1 — Morning (7-9am) / 2 — Afternoon (2-4pm) / 3 — Evening (8-10pm) / 4 — Any time

**Store:** `preferred_send_time`

**Q6c — Language (detect from conversation, confirm if ambiguous):**
> I notice you've been writing in [English/Hindi/Hinglish]. Should I respond in the same way?
>
> Reply: 1 — Yes, [language] is fine / 2 — Actually I prefer [language]

**Store:** `preferred_language`

**→ State 7**

---

## State 7: COMPLETE — Onboarding Done

**System sends:**

> [Owner name], you're all set! 🎉
>
> Here's what I now know about [Restaurant name]:
> ✓ [Cuisine type] in [area], [city]
> ✓ [Business model — dine-in/delivery/both]
> ✓ Your non-negotiables are saved
> ✓ Your menu has been mapped ([X] items, [Y] categories)
> ✓ Cultural calendar calibrated for [city] and your catchment
>
> I'm now starting to analyse your last 30 days of data. You'll hear from me with your first proper intelligence brief by [tomorrow morning 8am].
>
> Until then — if you ever want to ask me anything about your business, just message here. I'm always on.

**[Trigger: register restaurant with agent scheduler, run initial agent cycle]**

---

## Resuming Interrupted Onboarding

When a returning phone number messages during onboarding:

**If gap < 24 hours:**
> Welcome back! We were on [current step description]. Ready to continue?

**If gap > 24 hours:**
> Good to have you back! Last time we covered [completed sections]. Ready to continue where we left off? (Yes / Start over)

**State is stored in `whatsapp_sessions.onboarding_state` as JSON. Never lost.**

---

## Post-Onboarding: Owner Asks a Question

After onboarding is complete, any WhatsApp message from the owner is routed to the intelligence conversation layer — not the raw SQL agent. The conversation layer:

1. Reads restaurant profile + recent findings pool
2. Understands the question in context
3. Routes to the relevant agent(s) for on-demand analysis if needed
4. Responds in the same single voice

**Example flows:**

Owner: "How did we do this weekend?"
→ System queries Ravi's latest findings + runs a quick weekend summary
→ Responds: "This weekend was [X] — here's what stood out..."

Owner: "Why is my butter chicken not selling?"
→ Routes to Maya — checks order volume trend, review sentiment, menu position, competitor pricing
→ Responds with specific diagnosis + action

Owner: "Navratri is coming — what should I do?"
→ Routes to Priya — checks catchment demographic, current menu, cultural model
→ Responds with specific menu suggestions with timing and ₹ projections

Owner: "Add that thing you mentioned about ghee prices to my shopping list"
→ Routes to Arjun — confirms the relevant finding, provides purchase recommendation
→ Responds: "Done. Arjun's recommendation: buy [X]kg of ghee by [date] at [supplier]..."

---

## Multi-Restaurant Selector Flow

When an owner has multiple restaurants linked to one number:

**Incoming message → check whatsapp_sessions → multi-restaurant owner**

**If no active restaurant selected in last 30 minutes:**
> Which café are you asking about?
> 1 — YoursTruly (Bandra)
> 2 — Café Allora (Powai)
> 3 — The Good Bowl (Andheri)

**Owner replies with number → session locked to that restaurant for 30 minutes**

**If active restaurant already selected:**
Direct routing to that restaurant's intelligence context.

**Owner can switch anytime:**
"Switch to Café Allora" → system recognises intent, switches session.

---

## Correction and Learning

**Owner corrects the system:**
"No that's wrong, the filter coffee and the pour over are completely different"

→ System: "Got it — I've updated this. Filter Coffee and Pour Over will be tracked separately from now on."
→ Updates menu graph, stores as learned fact, never repeats the error.

**Owner updates a non-negotiable:**
"Actually I've decided to start offering value combos"

→ System: "Understood. I'll factor this in — do you want me to update your profile to reflect that value combos are now part of your strategy?"
→ If yes: updates profile, removes conflicting filter from quality gate.

**Owner corrects a finding:**
"That's not accurate — the Tuesday drop was because we were closed for a private event"

→ System: "Thanks for the context. I've noted that [date] Tuesday was a private event closure. This will be excluded from trend analysis."
→ Stores exclusion in findings pool, adjusts baseline calculation.
