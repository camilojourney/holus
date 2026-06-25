# Knowledge: Content Framework Library

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 13)
**Confidence:** high (derived from growth-engine-vision.md + voice-profile.md)
**Affects:** marketing agent content generation, prompt construction, content queue
**Research cadence:** monthly (update with performance data from analytics)

---

## How to Use This File

The marketing agent reads this file during the REASON stage to select a framework
for each content piece. Each framework has:
- **When to use** — triggers and product fit
- **Structure** — the skeleton with placeholders
- **Hook templates** — proven opening patterns (customize per product)
- **Platform rules** — how to adapt per channel
- **Voice notes** — integration with voice-profile.md

Placeholder syntax: `{variable}` — replaced by the agent at generation time.

---

## Framework Index

| ID | Name | Type | Best For | Engagement Level |
|----|------|------|----------|-----------------|
| `breakdown` | The Breakdown | Tutorial | Pilaster, genpeli | Very High |
| `contrarian` | The Contrarian | Hot Take | All products | High |
| `before_after` | The Before/After | Proof | Pilaster, genpeli | High |
| `thread` | The Thread | Value List | All products | Medium-High |
| `behind_scenes` | The Behind-the-Scenes | Founder Journey | Cross-product | Medium-High |
| `engagement_bait` | The Engagement Bait | CTA | Pilaster, genpeli | High (reach) |
| `data_drop` | The Data Drop | Authority | invoz, Pilaster | Medium |

---

## Framework: `breakdown`

**Name:** The Breakdown
**Tagline:** "Here's how X actually works"
**Content type:** Tutorial / explainer
**Goal:** Educate and build authority. Viewer learns something concrete.

### When to Use

- New feature shipped in any product
- Complex workflow that users struggle with
- Technical concept the audience misunderstands
- **Best products:** Pilaster (ComfyUI workflows), genpeli (video editing pipeline)
- **Best platforms:** LinkedIn (long-form), TikTok (video), YouTube Shorts (video)

### Structure

```
HOOK: {hook}

CONTEXT (2-3 sentences):
{product} does {thing}. But most people use it wrong.
Here's how it actually works under the hood.

BREAKDOWN (3-5 steps):
→ Step 1: {step_1_title}
  {step_1_detail}

→ Step 2: {step_2_title}
  {step_2_detail}

→ Step 3: {step_3_title}
  {step_3_detail}

INSIGHT:
{the_non_obvious_takeaway}

CLOSE:
{closing_question_or_forward_statement}
```

### Hook Templates

- "Most {audience} use {product} like {basic_way}. Here's what the top 1% do differently."
- "I spent {time} building {thing}. Here's the workflow nobody explains."
- "{product} has a feature most people ignore. It changes everything."
- "Here's how {technical_concept} actually works — not the marketing version."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Full text. Arrow bullets (→). 200-350 words. Closing question. |
| TikTok/Shorts | Screen recording + voiceover. Show each step. 30-60s. |
| Twitter/X | Thread format — one step per tweet. Hook tweet standalone. |
| Instagram | Carousel — one step per slide. Bold titles. |

### Voice Notes

- Use first-person: "I built this" / "Here's what I learned"
- Ground in real experience: "After processing 500 videos, here's what I found"
- One paradox or inversion in the insight section
- Close with a question, not a CTA

---

## Framework: `contrarian`

**Name:** The Contrarian
**Tagline:** "Everyone does X. Here's why Y is better"
**Content type:** Hot take / opinion
**Goal:** Stop the scroll with a strong opinion. Provoke engagement through disagreement.

### When to Use

- Industry best practice is actually suboptimal
- Common tool/approach has a better alternative (your product)
- Trending topic where the consensus is wrong
- **Best products:** All (position each against conventional approaches)
- **Best platforms:** LinkedIn (debate), Twitter/X (ratio potential), Threads

### Structure

```
HOOK: {hook}

THE COMMON BELIEF (2 sentences):
Most {audience} believe {common_approach}.
It's the default. It's what everyone recommends.

THE PIVOT:
{pivot_statement}

THE CONTRARIAN CASE (3-4 points):
1. {reason_1}
2. {reason_2}
3. {reason_3}

THE EVIDENCE:
{concrete_data_or_example}

CLOSE:
{question_that_invites_debate}
```

### Hook Templates

- "Stop {common_practice}. Do this instead."
- "R.I.P {old_way}. {new_thing} just broke it."
- "Everyone is talking about {trend}. Nobody is talking about {real_issue}."
- "{common_advice} is wrong. Here's why."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Full post. 150-250 words. End with debate question. |
| Twitter/X | Single tweet — the punchline only. Thread if evidence heavy. |
| Threads | Conversational tone. Shorter paragraphs. |
| TikTok | Talking head + bold text overlay with the contrarian claim. |

### Voice Notes

- Confident but not arrogant: "Here's what I've found" not "You're all wrong"
- Back claims with evidence (data, experience, research)
- The pivot line should be its own paragraph for emphasis
- Use em-dashes for the aside: "What I'm learning — painfully — is that..."

---

## Framework: `before_after`

**Name:** The Before/After
**Tagline:** "My workflow before vs after [product]"
**Content type:** Proof / social proof
**Goal:** Show transformation. Make the viewer want the same result.

### When to Use

- Product delivers a visible transformation
- User has a real before/after story
- New workflow dramatically improves existing process
- **Best products:** Pilaster (image quality), genpeli (raw vs edited video)
- **Best platforms:** LinkedIn (carousel), Instagram (side-by-side), TikTok (transformation)

### Structure

```
HOOK: {hook}

BEFORE (the pain):
{time_period} ago, {audience_pain}.
{specific_example_of_old_way}.
It took {old_time} and the results were {old_quality}.

THE CHANGE:
Then I {discovery_moment}.

AFTER (the result):
Now: {new_workflow}.
{specific_result} in {new_time}.
{concrete_metric_improvement}.

THE LESSON:
{what_this_proves_about_the_space}

CLOSE:
{forward_looking_or_question}
```

### Hook Templates

- "I used to spend {old_time} on {task}. Now it takes {new_time}."
- "My {thing} before vs after {product}. The difference is embarrassing."
- "{task} used to be my biggest bottleneck. Not anymore."
- "Same input. Completely different output. Here's what changed."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Text narrative + image comparison in comments or carousel. |
| Instagram | Split image or carousel (slide 1: before, slide 2: after). |
| TikTok | Video: show the before process → cut → show the after result. |
| Twitter/X | Two images in a single tweet. Short caption. |

### Voice Notes

- Be specific with numbers: "3 hours → 12 minutes" not "much faster"
- Show real artifacts (screenshots, videos, outputs)
- Humble framing: "I was doing it wrong" not "everyone else is wrong"
- The lesson should connect to a bigger truth

---

## Framework: `thread`

**Name:** The Thread
**Tagline:** "5 things I learned from X"
**Content type:** Value list / lessons
**Goal:** Deliver concentrated value. High save/bookmark rate.

### When to Use

- Accumulated lessons from building/using something
- Summarizing a complex topic into actionable takeaways
- Sharing hard-won knowledge the audience can apply immediately
- **Best products:** All (rotate through products for different angles)
- **Best platforms:** Twitter/X (native thread), LinkedIn (numbered list)

### Structure

```
HOOK: {hook}

ITEM 1: {lesson_title_1}
{lesson_detail_1}

ITEM 2: {lesson_title_2}
{lesson_detail_2}

ITEM 3: {lesson_title_3}
{lesson_detail_3}

ITEM 4: {lesson_title_4}
{lesson_detail_4}

ITEM 5: {lesson_title_5}
{lesson_detail_5}

CLOSE:
{meta_lesson_or_question}
```

### Hook Templates

- "I spent {time} building {thing}. Here's what nobody tells you."
- "{number} things I wish I knew before {activity}."
- "After {experience}, here are the {number} lessons that stuck."
- "The {audience} who {outcome} all do these {number} things."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| Twitter/X | One lesson per tweet. Hook tweet stands alone. 5-8 tweets total. |
| LinkedIn | Single post with numbered list. 200-350 words. |
| Instagram | Carousel — one lesson per slide with bold title. |
| Threads | Conversational numbering. Shorter per item. |

### Voice Notes

- Each item should be a standalone insight (not just a bullet point)
- Use Camilo's formula pattern: "Lesson = Experience + Reflection"
- End items with a short declarative: "That's the real lesson."
- Close with a question that invites the reader to share their version

---

## Framework: `behind_scenes`

**Name:** The Behind-the-Scenes
**Tagline:** "How I built X in Y days"
**Content type:** Founder journey / build log
**Goal:** Build personal connection. Humanize the brand. Attract builders.

### When to Use

- New feature or product just shipped
- Interesting technical challenge was solved
- Founder has a genuine "building in public" story
- **Best products:** Cross-product (the meta-story of building the portfolio)
- **Best platforms:** LinkedIn (primary — founder audience), Twitter/X

### Structure

```
HOOK: {hook}

THE CHALLENGE (2-3 sentences):
{what_we_set_out_to_build}.
{why_it_was_hard}.

THE JOURNEY (3-4 key moments):
Week 1: {early_decision_or_mistake}
Week 2: {pivot_or_breakthrough}
Week 3: {the_grind}
Launch: {what_actually_happened}

THE HONEST PART:
{what_went_wrong_or_was_surprising}

THE LESSON:
{what_this_taught_about_building}

CLOSE:
{forward_statement_or_question}
```

### Hook Templates

- "How I built {thing} in {time}. The real version, not the Twitter version."
- "We shipped {feature} last week. Here's what it took."
- "I used to believe {old_belief}. Building {thing} changed that."
- "The hardest part of building {thing} wasn't the code."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Full narrative. 250-400 words. Personal, reflective tone. |
| Twitter/X | Thread — one moment per tweet. Photos/screenshots inline. |
| Instagram | Photo of the workspace/product + story-style caption. |
| TikTok | Talking head or screen recording montage. Casual energy. |

### Voice Notes

- Maximum vulnerability: "I was wrong about X" / "This failed first"
- Use the callback device: open with a belief, close with how it changed
- Include real timelines and numbers
- The lesson should generalize beyond this specific build

---

## Framework: `engagement_bait`

**Name:** The Engagement Bait
**Tagline:** "Comment 'AI' and I'll send it"
**Content type:** Call-to-action / lead generation
**Goal:** Maximize reach through engagement signals. Capture leads.

### When to Use

- Have a valuable resource (template, workflow, cheat sheet) to share
- Platform algorithm rewards comment volume (LinkedIn, Instagram)
- Want to build email list or community
- **Best products:** Pilaster (ComfyUI workflows), genpeli (editing presets)
- **Best platforms:** LinkedIn (comment = signal), Instagram (DM automation)

### Structure

```
HOOK: {hook}

THE VALUE PREVIEW (2-3 sentences):
I {created/compiled} a {resource_type} for {audience}.
It includes {specific_value_1}, {specific_value_2}, and {specific_value_3}.

THE PROOF:
{evidence_this_works — numbers, testimonials, results}

THE CTA:
Comment "{keyword}" and I'll send it to you.
```

### Hook Templates

- "I made a {resource} that took me {time} to build. Giving it away free."
- "The {resource_type} I wish I had when I started {activity}."
- "Comment '{keyword}' and I'll DM you the {thing}."
- "This {resource} saved me {time/money}. Yours for free."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Comment trigger. Keep resource genuinely valuable. Follow up manually or via tool. |
| Instagram | "DM me {keyword}" or use ManyChat automation. Include preview image. |
| Twitter/X | "Like + RT for the link" pattern. Less effective — use sparingly. |
| TikTok | "Link in bio" or "Comment for the workflow." Video showing the resource. |

### Voice Notes

- The resource must be genuinely valuable — not bait-and-switch
- Keep the tone generous, not salesy: "I built this, you should have it"
- Include real proof (screenshot of results, number of downloads)
- Use sparingly: max 1x every 2 weeks per platform to avoid fatigue

### Frequency Cap

**Max usage:** 1x per 2 weeks per platform. Overuse kills trust and reach.

---

## Framework: `data_drop`

**Name:** The Data Drop
**Tagline:** "I analyzed 1000 posts. Here's what works"
**Content type:** Authority / research-backed insight
**Goal:** Establish credibility through data. Bookmark-worthy content.

### When to Use

- Have real data from analytics, experiments, or research
- Can share a non-obvious finding backed by numbers
- Want to position as authority in the space
- **Best products:** invoz (technical/data audience), Pilaster (experiment memory data)
- **Best platforms:** LinkedIn (B2B loves data), Twitter/X (quote-tweetable findings)

### Structure

```
HOOK: {hook}

THE METHODOLOGY (1-2 sentences):
I {analyzed/tracked/tested} {quantity} {things} over {time_period}.
Here's what the data shows.

FINDING 1: {finding_with_number}
{brief_explanation}

FINDING 2: {finding_with_number}
{brief_explanation}

FINDING 3: {finding_with_number}
{brief_explanation}

THE TAKEAWAY:
{what_this_means_for_the_audience}

CLOSE:
{question_about_their_experience_with_this_data}
```

### Hook Templates

- "I analyzed {number} {things}. Here's what nobody tells you."
- "The data says the opposite of what you'd expect about {topic}."
- "After {time_period} of tracking {metric}, here's what actually moves the needle."
- "We ran {number} experiments. {number}% of {common_approach} failed."

### Platform Adaptations

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Full post with inline numbers. Bold key stats. 200-300 words. |
| Twitter/X | Lead with the most surprising finding. Thread for full breakdown. |
| Instagram | Infographic carousel — one finding per slide with chart/number. |
| Threads | Conversational data storytelling. Focus on 1-2 key insights. |

### Voice Notes

- Always cite the source: "From our Pilaster experiment data" / "Based on 6 months of analytics"
- Use the formula device: "Performance = X * Y" for abstract patterns
- Be honest about sample size and limitations
- The takeaway should be actionable, not just interesting

---

## Hook Selection Guide

The marketing agent should select hooks based on product + framework + platform:

### By Product

| Product | Best Frameworks | Hook Angle |
|---------|----------------|------------|
| Pilaster | `breakdown`, `before_after`, `engagement_bait` | "ComfyUI workflow", "AI image generation", "character consistency" |
| genpeli | `breakdown`, `before_after`, `behind_scenes` | "video editing", "content creation", "raw to polished" |
| invoz | `data_drop`, `thread`, `contrarian` | "audio ML", "pronunciation", "developer tools" |

### By Platform

| Platform | Best Frameworks | Why |
|----------|----------------|-----|
| LinkedIn | `breakdown`, `behind_scenes`, `data_drop` | Professional audience values depth + data |
| Twitter/X | `contrarian`, `thread`, `data_drop` | Short, quotable, debate-friendly |
| TikTok | `breakdown`, `before_after` | Visual transformation + tutorial |
| Instagram | `before_after`, `engagement_bait`, `thread` | Visual proof + saves + DMs |
| Threads | `contrarian`, `thread` | Conversational, opinion-friendly |

---

## Framework Selection Logic (for the agent)

```
1. Check product: what product are we promoting this piece?
2. Check platform: where will this be posted?
3. Cross-reference: which frameworks fit BOTH product and platform?
4. Check recency: which framework haven't we used recently? (avoid repetition)
5. Check analytics: which framework has performed best for this product? (after data exists)
6. Select framework + pick hook template
7. Fill structure with product-specific content
8. Apply voice profile (see voice-profile.md)
9. Adapt for platform (length, format, media)
```

---

## What Changed vs Last Version

New file. Structured from growth-engine-vision.md frameworks + hook templates.
Cross-referenced with voice-profile.md for voice integration notes.
Cross-referenced with content-formats.md for platform adaptations.
Ready for marketing agent to consume during REASON stage.
