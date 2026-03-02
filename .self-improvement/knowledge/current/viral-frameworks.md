# Knowledge: Viral Framework Library

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 27 — authority engine niche research)
**Confidence:** medium (web research + pattern analysis; needs validation from own analytics)
**Affects:** marketing agent content generation, hook selection, structure decisions
**Research cadence:** bi-weekly (update with own performance data + fresh niche research)

---

## How to Use This File

The marketing agent reads this during the REASON stage to select proven structures
for authority-building content. Each framework is a **reverse-engineered pattern**
from high-performing LinkedIn posts in the AI consulting/builder niche.

This file complements `content-frameworks.md` (which defines Holus's own framework
library). This file documents **what's working in the wild** — real patterns from
real posts that drove real engagement.

**Selection logic:**
1. Pick a content pillar (from growth-engine-vision.md)
2. Pick a viral framework from this file that matches the pillar
3. Apply Camilo's voice (from voice-profile.md / brand.yaml)
4. Format for LinkedIn (from platforms.md)
5. Track performance → update confidence scores here

---

## Framework Index

| ID | Name | Type | Best Pillar | Engagement Signal | Source |
|----|------|------|-------------|-------------------|--------|
| `contrarian_reframe` | The Contrarian Reframe | Hot take | Contrarian takes, AI frameworks | Comments (debate) | Justin Welsh, AI consultants |
| `builder_reveal` | The Builder Reveal | Builder story | Builder stories, Results/proof | Shares + saves | Dev founders, AI builders |
| `transformation_arc` | The Transformation Arc | Personal narrative | Builder stories | Dwell time + comments | Alex Hormozi pattern |
| `framework_drop` | The Framework Drop | Educational | AI frameworks | Saves + shares | B2B consultants |
| `data_confession` | The Data Confession | Data + story hybrid | Results/proof, Industry analysis | 280% higher engagement | Hybrid pattern |
| `permission_giver` | The Permission Giver | Mindset shift | Contrarian takes | High likes + comments | Hormozi, Welsh |
| `insider_contrast` | The Insider Contrast | Hot take comparison | Industry analysis, AI frameworks | Comments (agreement) | Matt Barker pattern |
| `process_reveal` | The Process Reveal | Behind-the-scenes | Builder stories | Saves (replicable) | Richard Moore pattern |
| `bold_claim_proof` | Bold Claim + Proof | Authority assertion | Contrarian takes, Results/proof | Shares + debate | AI consultants |
| `question_inversion` | The Question Inversion | Thought experiment | AI frameworks, Contrarian takes | Comments (reflection) | Thought leaders |
| `carousel_framework` | The Carousel Framework | Visual framework | AI frameworks, Results/proof | 278% higher than video | B2B consultants |
| `cost_revelation` | The Cost Revelation | Transparency | Builder stories, Results/proof | Shares + saves | Founders, builders |

---

## Framework: `contrarian_reframe`

**Name:** The Contrarian Reframe
**Pattern:** Challenge an industry default. Offer a better mental model.
**Why it works:** Strong opinions act as filters — they repel indifference, attract the right audience, and trigger comments from people who agree AND disagree. The algorithm loves comment threads.
**Engagement:** 3K-30K likes on top performers. Comment-heavy.

### Structure

```
HOOK: [Challenge a default] — 1 sentence, bold, declarative.

THE DEFAULT (2 sentences):
Most [audience] believe [common approach].
It's the default. It's what every [authority] recommends.

THE REFRAME (1 sentence, standalone paragraph):
[Pivot statement — the contrarian position]

EVIDENCE (3-4 short points):
→ [Reason 1 with specific example]
→ [Reason 2 with data if possible]
→ [Reason 3 grounded in experience]

CLOSE:
[Question that invites debate — "Are you [doing the old way] or [the new way]?"]
```

### Real Examples

```yaml
examples:
  - hook: "I escaped the rat race 2.5 years ago. My secret sauce is less ambition."
    engagement: 30K likes
    creator: Justin Welsh
    why: Challenges the hustle narrative. Permission-giving + contrarian = engagement
    pillar_fit: contrarian_takes

  - hook: "Your AI strategy document is 40 pages too long. Here's why."
    engagement: high (AI consulting niche)
    creator: AI consultant pattern
    why: Specific claim + promised payoff. CTO reads this and thinks "that's us"
    pillar_fit: ai_frameworks, contrarian_takes

  - hook: "Most companies are still evaluating AI vendors. That's why they're 18 months behind."
    engagement: high (consulting niche)
    creator: growth-engine-vision.md hook library
    why: Urgency + insider knowledge. Prospect feels called out.
    pillar_fit: contrarian_takes, industry_analysis
```

### Consulting Angle

This framework is ideal for positioning Camilo as someone who sees what others don't.
The reframe should always point toward action the prospect could take — ideally action
that requires expertise (i.e., consulting).

---

## Framework: `builder_reveal`

**Name:** The Builder Reveal
**Pattern:** "I built X. Here's the architecture / what broke / what I learned."
**Why it works:** Demonstrates hands-on expertise. The specificity signals credibility
that no amount of abstract advice can match. CTOs respect builders.
**Engagement:** High shares + saves. Medium-high comments.

### Structure

```
HOOK: "I [built/automated/replaced] [specific thing]. Here's [what I learned / the architecture / what broke]."

THE CONTEXT (2-3 sentences):
[What existed before. What problem you solved. Why it matters.]

THE BUILD (3-5 specific details):
→ [Technical decision 1 — what and why]
→ [Technical decision 2 — what and why]
→ [Surprise or lesson — what you didn't expect]

THE RESULT:
[Concrete metric: time saved, cost reduced, throughput increased]

CLOSE:
[What would you build differently? / What's your biggest automation bottleneck?]
```

### Real Examples

```yaml
examples:
  - hook: "I replaced my $4,500/month SDR with an AI system that costs $47."
    engagement: viral (LinkedIn)
    creator: Eli Tanenbaum
    why: Specific dollar amounts + dramatic cost reduction. Every founder calculates their own savings.
    pillar_fit: builder_stories, results_proof

  - hook: "I built an AI Sales Agent that replaced my ENTIRE Sales team. While I was asleep, it followed up with 86 leads and closed 4 deals."
    engagement: viral (LinkedIn)
    creator: Julian Goldie
    why: "While I was asleep" — aspirational automation. Specific numbers (86 leads, 4 deals).
    pillar_fit: builder_stories, results_proof

  - hook: "I replaced 4 hours of video editing with one command. Here's the architecture."
    engagement: estimated high (builder niche)
    creator: Holus hook library
    why: Time savings + technical depth. Appeals to both builders and prospects.
    pillar_fit: builder_stories
```

### Consulting Angle

Every builder reveal should end with an insight that generalizes beyond the specific build.
"The real lesson: most AI implementations fail at data, not models."
This positions the build as evidence, and the insight as consulting value.

---

## Framework: `transformation_arc`

**Name:** The Transformation Arc
**Pattern:** Before state → turning point → after state. Personal narrative.
**Why it works:** Stories with transformation arcs trigger emotional engagement.
The reader projects themselves into the "before" state and wants the "after."
**Engagement:** Very high dwell time (storytelling). High comments (identification).

### Structure

```
HOOK: [Time marker + emotional state] — "2 years ago, I [was in pain state]."

THE BEFORE (3-4 sentences):
[Specific details of the old way. Make it relatable.]
[Use concrete numbers: hours, dollars, frustrations.]

THE TURNING POINT (1-2 sentences, standalone):
Then I [made a decision / discovered something / built something].

THE AFTER (3-4 sentences):
Now: [new reality with specific metrics].
[One detail that makes it vivid.]

THE META-LESSON (1 sentence):
[What this proves about the reader's situation.]

CLOSE:
[What's your turning point? / What would you change?]
```

### Real Examples

```yaml
examples:
  - hook: "2 years ago, I made the decision that changed my life."
    engagement: 192 likes (Lara Acosta)
    creator: Lara Acosta
    why: Universal template — everyone has a "before." Emotional identification.
    pillar_fit: builder_stories

  - hook: "I used to spend 3 hours editing every video. Now it takes 12 minutes."
    engagement: estimated high (builder pattern)
    creator: Holus hook library
    why: Specific numbers make the transformation concrete and believable.
    pillar_fit: builder_stories, results_proof

  - hook: "6 months ago I was manually posting to 5 platforms. It took 2 hours/day."
    engagement: estimated medium-high
    creator: builder niche pattern
    why: Relatable pain → automated solution. The reader calculates their own time waste.
    pillar_fit: builder_stories
```

### Consulting Angle

The transformation should mirror what a consulting prospect would experience.
"Before: 6 engineers, 9 months, no production system. After: 2 engineers, 6 weeks, deployed."
The implicit message: "I can create this transformation for your company."

---

## Framework: `framework_drop`

**Name:** The Framework Drop
**Pattern:** Teach a reusable mental model or decision-making framework.
**Why it works:** Frameworks are inherently shareable — they compress complex thinking
into actionable steps. High save rate = algorithm boost.
**Engagement:** Very high saves + shares. Medium comments.

### Structure

```
HOOK: [Problem everyone faces] + "Here's my framework."

THE FRAMEWORK (3-5 steps):
Step 1: [Name] — [explanation in 1-2 sentences]
Step 2: [Name] — [explanation in 1-2 sentences]
Step 3: [Name] — [explanation in 1-2 sentences]

THE INSIGHT:
[Why most people skip step N / get stuck at step N]

PROOF:
[Where you've applied this. Real outcomes.]

CLOSE:
[Which step are you stuck on? / Save this for later.]
```

### Real Examples

```yaml
examples:
  - hook: "Online business 101: 1) Gain attention. 2) Capture attention. 3) Monetize attention."
    engagement: 1K likes
    creator: Justin Welsh
    why: Brutally simple. The framework is complete in one read. Shareable.
    pillar_fit: ai_frameworks

  - hook: "My social media profit formula: [Audience x Niche x Offer = Revenue]"
    engagement: 234 likes
    creator: Matt Barker
    why: Formula format — easy to remember, easy to apply, easy to share.
    pillar_fit: ai_frameworks

  - hook: "How to actually deploy AI in your company: It's not about the model."
    engagement: estimated high (AI consulting niche)
    creator: AI consultant pattern
    why: Contrarian framing + promised framework. CTO reads and shares with team.
    pillar_fit: ai_frameworks
```

### Consulting Angle

The framework should be genuinely useful AND demonstrate that the full implementation
requires expertise. "Here are the 4 steps. Most companies nail steps 1-2 and fail
at 3-4. That's where it gets hard."

---

## Framework: `data_confession`

**Name:** The Data Confession
**Pattern:** Blend personal narrative with hard numbers. "I lost $X learning this."
**Why it works:** Posts combining personal story + concrete metrics achieve
**280% higher engagement** than story-only or data-only posts (PostPro AI analysis, 500+ posts).
**Engagement:** Very high across all signals.

### Structure

```
HOOK: "I [did something with a specific number]. Here's what [nobody tells you / I found]."

THE SETUP (2 sentences):
[What you set out to do. The hypothesis or goal.]

THE DATA (3-4 findings with numbers):
→ Finding 1: [metric + what it means]
→ Finding 2: [metric + what it means]
→ Finding 3: [the surprising one]

THE CONFESSION:
[What you got wrong. What the data forced you to accept.]

THE TAKEAWAY:
[Actionable insight the reader can apply.]

CLOSE:
[What does your data show? / What surprised you about [topic]?]
```

### Real Examples

```yaml
examples:
  - hook: "I tracked every AI implementation I've done. The #1 failure mode isn't the model."
    engagement: estimated high (AI consulting niche)
    creator: growth-engine-vision.md hook library
    why: Counter-intuitive finding + insider expertise. Prospect wants to know the answer.
    pillar_fit: results_proof, industry_analysis

  - hook: "I analyzed 500+ LinkedIn posts. One pattern predicted virality 73% of the time."
    engagement: high (LinkedIn meta content)
    creator: Sumanth Chary (Dev.to)
    why: Large sample size + specific accuracy claim. Practitioners want the pattern.
    pillar_fit: results_proof

  - hook: "I spent $12,000 on AI APIs in 6 months. Here's what I'd do differently."
    engagement: estimated high (builder pattern)
    creator: builder niche composite
    why: Specific dollar amount = credibility. "What I'd do differently" = hard-won wisdom.
    pillar_fit: builder_stories, results_proof
```

### Consulting Angle

This is the strongest consulting framework. Real data from real work proves expertise
more than any credential. The confession element shows intellectual honesty —
prospects trust people who admit mistakes more than people who claim perfection.

---

## Framework: `permission_giver`

**Name:** The Permission Giver
**Pattern:** Remove a mental barrier holding the audience back.
**Why it works:** Everyone has limiting beliefs about their career, business, or technical
ability. Posts that say "it's okay to [thing they feel guilty about]" trigger relief
and massive engagement through identification.
**Engagement:** Very high likes. High comments (people sharing their version).

### Structure

```
HOOK: [Bold permission statement] — 1 sentence.

THE BELIEF (2 sentences):
[The limiting belief most people carry.]
[Why it seems true / where it comes from.]

THE PERMISSION (1 sentence, standalone):
[Direct permission — "You don't need to [old expectation]."]

THE EVIDENCE (2-3 points):
→ [Why the old belief is wrong — evidence 1]
→ [Why the old belief is wrong — evidence 2]
→ [What to do instead]

CLOSE:
[Reinforcing statement. "Now go [do the thing]." / empowering question]
```

### Real Examples

```yaml
examples:
  - hook: "If you have no money, you should have no shame."
    engagement: 11K likes
    creator: Alex Hormozi
    why: Removes pride barrier. Permission to hustle. Practical steps follow.
    pillar_fit: contrarian_takes

  - hook: "You just have to be willing to look like an idiot while you figure it out."
    engagement: 8K likes
    creator: Alex Hormozi
    why: Universal fear (looking stupid) + permission to fail. One sentence = shareable.
    pillar_fit: contrarian_takes

  - hook: "You don't need a PhD to deploy AI in production. You need a good problem and messy data."
    engagement: estimated high (AI consulting niche)
    creator: AI consultant pattern
    why: Removes credential barrier. Prospects who've been waiting for "the right time" feel called to act.
    pillar_fit: ai_frameworks, contrarian_takes
```

### Consulting Angle

For AI consulting: remove the belief that "we're not ready for AI" or "we need to hire
a full ML team first." The permission post attracts prospects who've been hesitating.
Follow up with DM engagement.

---

## Framework: `insider_contrast`

**Name:** The Insider Contrast
**Pattern:** "What [authorities] say vs. what [insiders] know."
**Why it works:** Positions the author as an insider with superior knowledge.
The contrast format is visually scannable and triggers "I knew it!" reactions.
**Engagement:** High comments (agreement). High shares (people tagging peers).

### Structure

```
HOOK: "What [group A] says vs. What [group B] knows:"

LEFT COLUMN: [The common advice — 4-6 items]
→ "Post every day"
→ "Use engagement pods"
→ "Follow the trends"

RIGHT COLUMN: [The insider truth — 4-6 items]
→ "Post when you have something to say"
→ "Write things people actually want to share"
→ "Create your own trends"

THE INSIGHT (1-2 sentences):
[Why the gap exists between common advice and reality.]

CLOSE:
[Which column are you following? / What would you add?]
```

### Real Examples

```yaml
examples:
  - hook: "What LinkedIn coaches say vs. What the best creators know:"
    engagement: 3K likes
    creator: Justin Welsh
    why: Elevates the reader ("you're in on the secret"). Contrasts bad advice with good.
    pillar_fit: industry_analysis

  - hook: "What AI vendors promise vs. What AI actually delivers in production:"
    engagement: estimated high (AI consulting niche)
    creator: AI consultant pattern
    why: Every CTO has experienced the gap. Validates their frustration, positions you as honest.
    pillar_fit: industry_analysis, contrarian_takes
```

### Consulting Angle

This framework is gold for positioning against AI vendors. Prospects are getting
pitched by 10 vendors a week. A post that calls out vendor BS positions Camilo
as the honest advisor who knows what actually works.

---

## Framework: `process_reveal`

**Name:** The Process Reveal
**Pattern:** Show your actual working process. Transparency as trust.
**Why it works:** People save posts they can replicate. Process posts have the highest
save rate because they're reference material. Saves = strong algorithm signal.
**Engagement:** Very high saves. Medium-high shares.

### Structure

```
HOOK: "Here's how I [achieve result that audience wants]."

THE PROCESS (5-7 steps):
1. [Step with specific tool or method]
2. [Step with specific tool or method]
3. [Step — the non-obvious one]
4. [Step with time/effort detail]
5. [Step — the one most people skip]

THE SECRET:
[The insight that makes this process work — not just the steps, but the principle.]

CLOSE:
[What's your process? / What step would you add?]
```

### Real Examples

```yaml
examples:
  - hook: "Here's how I write over 50% of my content on LinkedIn."
    engagement: 339 likes
    creator: Richard Moore
    why: "50%" is specific enough to be credible. Everyone wants content shortcuts.
    pillar_fit: builder_stories

  - hook: "Here's exactly how I deploy AI for a client. No buzzwords."
    engagement: estimated high (AI consulting niche)
    creator: AI consultant pattern
    why: "No buzzwords" signals honesty. "Exactly how" promises specificity.
    pillar_fit: ai_frameworks, builder_stories
```

### Consulting Angle

The process reveal should be valuable but incomplete — the steps are real, but
executing them well requires experience. "Step 3 is where most companies get stuck.
It looks simple but the edge cases will eat you alive."

---

## Framework: `bold_claim_proof`

**Name:** Bold Claim + Proof
**Pattern:** Make a strong assertion. Immediately back it with evidence.
**Why it works:** The bold claim stops the scroll. The proof converts skepticism into
respect. Posts with specific numbers in the first line get 2.7x more engagement
than abstract openings (PostPro AI analysis).
**Engagement:** High shares (quotable). High comments (debate).

### Structure

```
HOOK: [Strong claim with specific number or assertion.]

THE PROOF (3-4 concrete points):
→ [Evidence 1 — specific, named, dated]
→ [Evidence 2 — metric or outcome]
→ [Evidence 3 — the one that clinches it]

THE IMPLICATION:
[What this means for the reader / their company / their career.]

CLOSE:
[Does this match your experience? / What's your data showing?]
```

### Real Examples

```yaml
examples:
  - hook: "Last month I crossed $500,000 in online course sales."
    engagement: 2K likes
    creator: Justin Welsh
    why: Specific milestone + timeline. Undeniable proof of expertise.
    pillar_fit: results_proof

  - hook: "I tested 47 different AI prompt frameworks. One outperformed all others by 312%."
    engagement: high (carousel format)
    creator: AI content pattern
    why: Large sample + specific percentage. Practitioner curiosity: "which one?"
    pillar_fit: results_proof, ai_frameworks
```

### Consulting Angle

For consulting: bold claims should be backed by work you've actually done.
"We reduced inference costs by 73% for a fintech client. Here's the architecture."
The specificity (fintech, 73%, architecture) positions you as someone who delivers.

---

## Framework: `question_inversion`

**Name:** The Question Inversion
**Pattern:** Take a common assumption, flip it into a question.
**Why it works:** Forces the reader to pause and reconsider. The best questions
create a "huh, I never thought of it that way" moment. High dwell time.
**Engagement:** High comments (people answering). High dwell time.

### Structure

```
HOOK: "[Common assumption]. But what if [contrarian reframe]?"

THE EXPLORATION (3-4 sentences):
[Unpack the inversion. Why might the contrarian view be right?]
[One concrete example that supports the inversion.]

THE TENSION:
[Acknowledge both sides. Don't resolve it — let the reader decide.]

CLOSE:
[The question again, more specific: "What if [specific version of the inversion]?"]
```

### Real Examples

```yaml
examples:
  - hook: "Everyone wants to hire AI engineers. But what if you already have them?"
    engagement: estimated high (AI consulting niche)
    creator: growth-engine-vision.md hook library
    why: Reframes hiring problem as training problem. CTOs love this.
    pillar_fit: ai_frameworks, contrarian_takes

  - hook: "What if everything you know about AI ROI is backwards?"
    engagement: estimated high
    creator: AI consultant pattern
    why: "Everything you know is wrong" is the ultimate scroll-stopper.
    pillar_fit: contrarian_takes
```

### Consulting Angle

The question inversion is a discovery call in post form. It surfaces the prospect's
hidden assumption, creates cognitive dissonance, and makes them want to talk to
someone who can resolve it. Perfect for DM-to-call conversion.

---

## Framework: `carousel_framework`

**Name:** The Carousel Framework
**Pattern:** Multi-slide PDF with one idea per slide. Visual learning.
**Why it works:** Document posts get **278% higher engagement than video** and
**596% higher than text** (LinkedIn data, 2026). Carousels naturally extend dwell
time (swipe = commitment) and are the most saved format on LinkedIn.
**Engagement:** Highest of any format. 6.60% engagement rate average.

### Structure

```
SLIDE 1: [Bold hook — the promise. Large text, clean design.]
SLIDE 2: [The problem — why this matters.]
SLIDES 3-8: [One point per slide. Short text + visual hierarchy.]
SLIDE 9: [Summary or key takeaway.]
SLIDE 10: [CTA — question to drive comments. "Which step do you struggle with?"]
```

### Real Examples

```yaml
examples:
  - hook: "The AI Implementation Playbook (7 slides)"
    engagement: very high (document format)
    creator: B2B consultant pattern
    why: Frameworks in carousel format get saved and shared to teams. "Send this to your CTO."
    pillar_fit: ai_frameworks

  - hook: "I built 3 AI products. Here's the architecture of each one."
    engagement: estimated very high
    creator: builder pattern
    why: Technical depth + visual format. Engineers and CTOs both engage.
    pillar_fit: builder_stories, results_proof
```

### Consulting Angle

Carousels are the most effective consulting lead magnet on LinkedIn. A framework
carousel that solves 80% of the problem positions Camilo as the person to call
for the remaining 20%.

**Note:** Requires image generation capability (Pilaster integration) to create
branded slide templates.

---

## Framework: `cost_revelation`

**Name:** The Cost Revelation
**Pattern:** Reveal the real cost (time, money, effort) behind something.
**Why it works:** Transparency builds trust. When you show what something actually
costs — especially if it's more than expected — people respect the honesty and share
it as a reality check for their networks.
**Engagement:** High shares + saves. Medium-high comments.

### Structure

```
HOOK: "I spent [specific amount] on [thing]. Here's what I'd do differently."

THE BREAKDOWN:
→ [Cost item 1: amount + what it was for]
→ [Cost item 2: amount + what it was for]
→ [Cost item 3: the one that surprised you]

THE LESSON:
[What was worth it. What wasn't. What you'd skip.]

THE FORMULA:
[If you're doing this, budget for X not Y. Here's the real math.]

CLOSE:
[What's your biggest hidden cost? / What would you skip?]
```

### Real Examples

```yaml
examples:
  - hook: "I spent $12,000 on AI APIs in 6 months. Here's what I'd do differently."
    engagement: estimated high
    creator: builder niche composite
    why: Specific dollar amount + "what I'd do differently" = hard-won wisdom.
    pillar_fit: builder_stories, results_proof

  - hook: "The real cost of building an AI product isn't the API calls. It's the 200 hours of data cleaning."
    engagement: estimated high
    creator: AI consultant pattern
    why: Reframes cost expectations. Prospects re-evaluate their budgets.
    pillar_fit: industry_analysis, builder_stories
```

### Consulting Angle

Cost revelations position Camilo as someone who's been through it and can save prospects
from expensive mistakes. "I already paid this tuition. Here's what I learned."

---

## Cross-Cutting Patterns (What the Data Shows)

### Hook Effectiveness (from 500+ post analysis)

| Pattern | Engagement Multiplier | Why |
|---------|----------------------|-----|
| Opening with specific numbers | 2.7x | Concreteness triggers curiosity |
| Contrarian first line | 2.3x | Stops the scroll, triggers debate |
| "I was wrong about..." | 2.1x | Vulnerability + pattern interrupt |
| Question in first line | 1.8x | Triggers reflexive thinking |
| Generic advice opening | 0.4x | Indistinguishable from AI slop |

### Formatting Rules

| Rule | Impact | Source |
|------|--------|--------|
| Line breaks every 1-2 sentences | 3.1x better than dense paragraphs | PostPro AI (500+ posts) |
| Arrow bullets (→) over dashes | Higher scan rate | LinkedIn native pattern |
| Bold key concepts | Guides the eye | B2B content data |
| Single idea per post | Higher completion rate | Content strategy consensus |
| 150-350 words (LinkedIn) | Optimal dwell time | 2026 algorithm data |

### Timing

| Window | Effect | Source |
|--------|--------|--------|
| 15+ engagements in first hour | Post survives; algorithm pushes it | PostPro AI analysis |
| Reply to comments within 60 min | 2.4x higher reach | PostEverywhere data |
| Post during morning commute (7-9am) or lunch (12-1pm) | Higher initial engagement | LinkedIn audience data |

### Format Performance (2026 LinkedIn data)

| Format | Engagement Rate | vs. Text-Only |
|--------|----------------|---------------|
| Document/Carousel (PDF) | 6.60% | +596% |
| Video (< 90s) | ~3.5% | +278% |
| Image + text | ~2.5% | +120% |
| Text-only (formatted) | ~1.5% | baseline |
| Text with external link | ~0.6% | -60% |

---

## Anti-Patterns (What NOT to Do)

```yaml
anti_patterns:
  engagement_bait:
    example: "Comment 'YES' if you agree"
    why_bad: LinkedIn NLP filters detect this. Immediate reach suppression (2025+ policy).
    alternative: End with a genuine question that invites perspective.

  generic_ai_take:
    example: "AI is transforming every industry. Here's why you should care."
    why_bad: Indistinguishable from 50% of LinkedIn posts (now AI-assisted). Zero differentiation.
    alternative: Specific claim + specific evidence. "I deployed AI for a logistics client. Routing costs dropped 31%."

  wall_of_text:
    example: Dense paragraph with no line breaks
    why_bad: 3.1x lower engagement than formatted posts. People scroll past.
    alternative: Short paragraphs. Line breaks. Arrow bullets. Whitespace.

  external_links_in_body:
    example: "Read my full article here: [link]"
    why_bad: 60% reach reduction. LinkedIn penalizes outbound links.
    alternative: Put link in first comment. Or deliver the value in the post itself.

  humble_brag:
    example: "I'm so grateful to announce my 3rd acquisition this year..."
    why_bad: People see through it. Low comment quality.
    alternative: Lead with the lesson, not the achievement. "Here's what I learned from building and selling 3 companies."

  sycophantic_opening:
    example: "Great question! I'd love to share my thoughts..."
    why_bad: Screams AI-generated. Zero trust.
    alternative: Jump straight to the insight. No preamble.
```

---

## What Changed vs Last Version

New file. Seeded from web research into LinkedIn AI consulting/builder niche (2025-2026).
12 frameworks reverse-engineered from high-performing posts. Cross-referenced with
growth-engine-vision.md hook library, content-frameworks.md structures, and brand.yaml voice.
Needs validation from own analytics data — confidence will increase as we track which
frameworks perform for Camilo's audience.
