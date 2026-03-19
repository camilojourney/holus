# LinkedIn Content Analysis — Raw Findings

569 posts across 18 profiles. Analyzed 2026-03-18.


## 1. FORMAT: What type of post gets the most engagement?

| Format | Count | % of Posts | Avg Engagement | Median Engagement |
|--------|-------|-----------|----------------|-------------------|
| carousel/document | 6 | 1.1% | 794 | 951 |
| image+text | 174 | 30.6% | 924 | 455 |
| text-only | 50 | 8.8% | 630 | 415 |
| video | 291 | 51.1% | 1,406 | 361 |
| article/link | 48 | 8.4% | 240 | 157 |

Video has the highest average BUT the lowest median — a few mega-viral videos (Andrew Ng course announcements) pull the average up. Carousel/document has the highest median (951) — it's the most consistently high-performing format. Image+text is second most consistent. Article/link posts are dead — worst by every metric.

Ranking: carousels > image+text > text-only >> video (unless you're Andrew Ng) >> article/link.


## 2. HOOK TYPE: What opening line gets the most engagement?

| Hook Type | Count | Avg Engagement | Median |
|-----------|-------|----------------|--------|
| news/announcement | 31 | 5,427 | 4,681 |
| direct-address ("If you...", "Are you...") | 13 | 1,322 | 574 |
| how-to/explainer | 21 | 1,281 | 615 |
| question | 3 | 1,096 | 988 |
| contrarian/negative ("Stop...", "Don't...") | 7 | 825 | 333 |
| personal-story ("I...", "My...") | 32 | 789 | 446 |
| bold-statement ("The...", "Most...", "Every...") | 40 | 755 | 351 |
| emoji-hook (starts with emoji) | 35 | 332 | 324 |
| short-punchy (< 50 chars) | 14 | 200 | 143 |

"Announcing..." and "New course:..." destroy everything else (5,427 avg). But that only works if you HAVE something to announce. For regular content, direct-address and how-to hooks are the best (1,200-1,300 avg). Emoji hooks are the worst non-trivial format. Starting with emojis signals "marketing content" and people scroll past.

Open with "If you..." or "How to..." or "Why X..." — not with emojis or one-liners.


## 3. FORMATTING FEATURES: What helps, what hurts?

| Feature | Avg Eng WITH | Avg Eng WITHOUT | Verdict |
|---------|-------------|-----------------|---------|
| External link | 1,335 | 900 | HELPS (+48%) |
| Ends with CTA | 1,380 | 726 | HELPS (+90%) — but see note below |
| ALL CAPS words | 1,122 | 1,074 | Neutral (+4%) |
| Emoji | 663 | 1,399 | HURTS (-53%) |
| Unicode bold | 605 | 1,130 | HURTS (-46%) |

Note on CTAs: The +90% is partly because Andrew Ng's course announcements (the highest-engagement posts in the dataset) all end with "Please sign up here: [link]". The CTA isn't what makes those posts work — having something genuinely valuable to link to is. CTA works when you're giving something (a course, a repo, a tool). Don't force a CTA on a thought piece.

The top 10 posts in this dataset average 0.3 emojis per post. Andrew Ng uses zero. Ethan Mollick uses zero. The emoji-heavy creators (Carlos Santana, Sundas Khalid) have lower median engagement.


## 4. WORD COUNT: How long should posts be?

| Length | Count | Avg Engagement | Median |
|--------|-------|----------------|--------|
| 0-30 words (micro) | 90 | 322 | 152 |
| 31-75 words (short) | 126 | 703 | 346 |
| 76-150 words (medium) | 131 | 1,087 | 391 |
| 151-300 words (long) | 163 | 1,091 | 417 |
| 300+ words (essay) | 58 | 3,087 | 1,604 |

Longer posts get MORE engagement, not less. The "keep it short" LinkedIn advice is wrong based on this data. 300+ word posts get 4.5x the median engagement of micro posts. The sweet spot starts at 76+ words, but the real performers are 300+ word essays with substance.

Write longer. Don't write fluff — write substance. If you have enough to say, 300+ words wins.


## 5. LANGUAGE: English vs Spanish

| Language | Posts | Avg Engagement | Median |
|----------|-------|----------------|--------|
| English | 493 | 1,191 | 395 |
| Spanish | 74 | 396 | 334 |

English posts get 3x the average engagement, but the median gap is smaller (395 vs 334). Spanish posts are respectable — they're not dead content. The gap is partly because the highest-follower creators (Andrew Ng 1.8M, Allie Miller 2M) post in English. The Spanish creators in this dataset (Freddy Vega, Carlos Santana) have smaller but dedicated followings.

English reaches more people. Spanish is viable but starts from a smaller base. This supports running the bilingual experiment.


## 6. PER-PROFILE LEARNINGS

Tier 1 — Engagement machines (avg > 1,000)

| Creator | Posts | Avg | Median | Primary Format | Style |
|---------|-------|-----|--------|----------------|-------|
| Andrew Ng | 40 | 6,775 | 5,646 | video | Course announcements |
| Ruben Hassid | 40 | 1,823 | 1,256 | image+text | Claude/ChatGPT setups |
| Mati Staniszewski | 40 | 1,691 | 925 | image+text | ElevenLabs product wins |

Tier 2 — Strong performers (avg 500-1,000)

| Creator | Posts | Avg | Median | Primary Format | Style |
|---------|-------|-----|--------|----------------|-------|
| Ethan Mollick | 40 | 747 | 465 | image+text | Research-backed AI takes |
| Allie K Miller | 40 | 718 | 557 | video | AI business strategy |
| Nina Fernanda Duran | 40 | 622 | 290 | image+text | AI engineering diagrams |
| Freddy Vega | 40 | 567 | 378 | text | Spanish tech/culture |
| Sundas Khalid | 31 | 535 | 313 | video | Data career content |

Tier 3 — Moderate (avg 200-500)

| Creator | Posts | Avg | Median | Primary Format | Style |
|---------|-------|-----|--------|----------------|-------|
| Cassie Kozyrkov | 40 | 369 | 331 | video | Decision intelligence |
| Armand Ruiz | 40 | 364 | 142 | video | Architecture diagrams |
| Harrison Chase | 40 | 348 | 181 | image+text | LangChain product updates |
| Sebastian Ramirez | 40 | 298 | 145 | article/link | FastAPI releases |
| Carlos Santana Vega | 40 | 282 | 268 | article/link | Spanish AI explainers |


## 7. WHAT THE TOP 50 POSTS HAVE IN COMMON

Looking at the top 50 posts by total engagement:
- 32/50 (64%) are from Andrew Ng — his massive follower base (1.8M) dominates
- 6/50 (12%) are from Ruben Hassid — practical Claude/ChatGPT setup guides
- 4/50 (8%) are from Mati Staniszewski — ElevenLabs milestone announcements
- Zero Spanish-language posts in the top 50
- Average word count of top 50: 230 words — longer than average
- Average emoji count in top 50: 1.2 — very low emoji use
- Posts with links: 62% — majority include external links
- Posts ending with CTA: 74% — most have some call to action


## 8. SPACING ANALYSIS — PROBLEM DETECTED

The scraper captured all text as single-line (totalLines: 1 for every post). LinkedIn's line breaks are rendered via CSS but not captured in the raw text extraction. The spacing analysis is invalid — needs a scraper fix to capture actual line breaks. Spacing and breathing room is a key formatting variable we're missing.


## 9. CTA TYPES THAT WORK

Three CTA patterns from the top 30 posts:

| Type | Example | Who | Engagement |
|------|---------|-----|------------|
| "Sign up / Start here" + link | "Please sign up here: [link]" | Andrew Ng | 5,000-22,000 |
| "Repost to help others" | "Repost this to help others quit ChatGPT" | Ruben Hassid, Nina Duran | 4,000-6,000 |
| No CTA — just ends the story | "...which makes sharing this feel special" | Mati, Ethan Mollick | 5,000-16,000 |

Use a CTA when you're giving something (a repo, tool, template, course). Don't force a CTA on a thought piece — just end with the thought.


## 10. VISUAL PATTERNS — What makes images work

Three tiers from screenshot analysis:

Tier 1 — Custom-designed infographics (highest engagement for image+text)

Ruben Hassid "How to use Claude" flowchart (5,333 reactions):
- Purpose-built visual, not a screenshot
- White background, brand color accents (Anthropic orange)
- Clear hierarchy: headers, sections, details
- Flowchart/grid layout

Freddy Vega research data card (528 reactions, 47 comments):
- Dark background (stands out in LinkedIn's white feed)
- Research data with bar charts
- Color-coded callout boxes
- Source citations visible

Pattern: the image IS the content. It teaches something on its own, without the text.

Tier 2 — Data visualizations / charts

Ethan Mollick bar chart "Human birth lottery" (121 reactions):
- Horizontal bar chart from academic research
- Not designed by him — he shares existing data
- The image adds information, not decoration

Pattern: existing data visualized clearly. Curate, don't create from scratch.

Tier 3 — Screenshots of real products/code

Nina Fernanda Duran GitHub repo screenshot (1,944 reactions):
- Raw GitHub UI — README, file tree, badges
- Zero design effort — just a screenshot
- Works because it's authentic

Pattern: authenticity over polish. Screenshots feel real but don't stop the scroll.

What does NOT work visually:
- Stock photos (nobody in the top 50 uses them)
- Generic AI-generated art (decorative, not informational)
- Text-only images (just words on a colored background)
- Cluttered infographics with too many elements

Visual rules:
1. The image should teach independently — if someone only saw the image, would they learn something?
2. Dark backgrounds stand out in LinkedIn's white feed
3. Data + charts > designed graphics > screenshots > stock photos
4. One concept per image — don't cram everything in


## 11. ANTI-SYNTHETIC CHECKLIST

What makes content sound AI-generated (low engagement):

| Signal | Why it's bad | Do this instead |
|--------|-------------|-----------------|
| Unicode bold text | Screams ChatGPT | Regular text or ALL CAPS for emphasis |
| "In today's rapidly evolving..." | Generic AI opener | Start with a specific claim or experience |
| Heavy emoji (5+) | Looks like marketing copy | 0-2 emojis max, or zero |
| "Here are 10 ways to..." no personal angle | Listicle without soul | "I tried 10 approaches and 3 actually worked:" |
| Perfect grammar, no contractions | Too polished | Use contractions, incomplete sentences |
| "Let's dive in" | ChatGPT transition | Just present the content |
| "What do you think? Let me know!" | Generic CTA | Specific: "Have you tried this with Claude 4.6?" |
| Even paragraph lengths | AI patterns evenly | Vary — one sentence, then a long paragraph |
| "Leveraging", "delve", "landscape" | ChatGPT's favorite words | Use normal words |

What makes content feel human (high engagement):

| Signal | Why it works | Example |
|--------|-------------|---------|
| Specific numbers | Proves it's real | "$500M Series D at $11B valuation" (Mati) |
| Named people/companies | Shows relationships | "Nikhil Kamath" (Mati), "@Chris Achard" (Andrew Ng) |
| "I" + concrete past action | You did it, not just opining | "I've had ChatGPT-5.4 Pro working away at a project" (Ethan) |
| Imperfect sentences | Nobody writes perfectly | "how lucky are you to be alive right now?" (Ethan) |
| Contrarian take | AI plays it safe, humans don't | "LinkedIn should let us mute these phrases" (Ethan, 2,825 reactions) |
| Admitting not knowing | AI never says "I don't know" | "I always wondered about the answer to this" (Ethan) |
| Short opening + long body | Asymmetric structure | "You just quit ChatGPT for Claude. But you're lost." (Ruben) |
| Sharing failures | AI only shares successes | "Never expected to hear myself speaking Hindi" (Mati) |


## 12. BEFORE POSTING — 5 QUESTIONS

1. Could a ChatGPT prompt produce this exact post? If yes, rewrite.
2. Does it contain a specific experience only YOU had? If no, add one.
3. Would you say this out loud to a colleague? If no, simplify.
4. Does it take a position someone could disagree with? If no, sharpen.
5. Is there a number, name, or date grounding it in reality? If no, add one.
