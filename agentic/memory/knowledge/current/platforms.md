# Knowledge: Platform Playbook

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 25 — authority engine rewrite)
**Confidence:** high (derived from brand.yaml, content-marketing-strategy.md, 2025-2026 platform data)
**Affects:** marketing agent posting decisions, content formatting, repurposing logic
**Research cadence:** monthly

---

## Platform Hierarchy

**Rule:** Create for LinkedIn. Repurpose for everything else.
Never create platform-specific content from scratch except for LinkedIn.

| Tier | Platform | Role | Cadence | Source |
|------|----------|------|---------|--------|
| PRIMARY | LinkedIn | Authority pipeline | 5x/week | Original content |
| Repurpose | Twitter | Amplification | 3x/week | Condensed from LinkedIn |
| Repurpose | Instagram | Brand building | 2x/week | Visual or condensed |
| Repurpose | Threads | Community | 2x/week | Conversational reframe |
| Repurpose | Facebook | Bilingual reach | 1x/week | Spanish translation |

**Not active:** TikTok, YouTube Shorts, Bluesky (revisit when LinkedIn pipeline is warm).

---

## LinkedIn Playbook

LinkedIn is where consulting prospects live. CTOs, VPs Eng, founders at 50-500
employee companies read LinkedIn during their morning commute and lunch break.
Every post is an audition: "Should I talk to this person about our AI strategy?"

### Algorithm Signals (2026)

| Signal | Weight | What It Means | How to Trigger |
|--------|--------|---------------|---------------|
| Dwell time | Very high | Reader stopped scrolling and read | Long-form (150+ words), storytelling, whitespace formatting |
| Comments | Very high | Reader engaged enough to respond | End with a question, contrarian framing, actionable frameworks |
| Shares | Highest | Reader wants their network to see this | Data-backed insights, frameworks worth bookmarking, "send this to your CTO" content |
| Saves | High | Reader wants to come back to this | Step-by-step guides, checklists, architecture diagrams |
| Profile clicks | Medium | Reader wants to know who wrote this | Strong hook + incomplete story (curiosity gap) |
| Likes | Low | Passive acknowledgment | Easy to get, low signal — don't optimize for this |
| External clicks | Penalized | Sends reader off-platform | Never put links in post body. First comment only |

**Ranking: shares > comments > dwell time > saves > profile clicks > likes**

### Post Formats

#### Text Post (50% of content)

**When:** Builder stories, contrarian takes, industry analysis.
**Why:** Highest reach potential. Algorithm favors native text. Zero production cost.
**Length:** 150-300 words (sweet spot for dwell time without losing attention).

Structure:
```
[Hook — 1 line, stop the scroll]

[Setup — 2-3 sentences, establish context]

[Body — the insight, framework, or story]
→ Use arrow bullets for lists
→ Short paragraphs (1-2 sentences)
→ Whitespace between every thought

[Closer — question, forward statement, or one-word punch]
```

Technical limits:
- 3,000 characters max
- No link preview if URL in body (put links in first comment)
- First 210 characters visible before "see more" — hook MUST be here

#### Carousel / Document Post (25% of content)

**When:** AI implementation frameworks, architecture walkthroughs, step-by-step guides.
**Why:** High save rate and dwell time. Each slide = more engagement signals.
**Format:** PDF upload (LinkedIn renders as slides). 7-12 slides optimal.

Structure:
```
Slide 1: Hook + title (bold, minimal text)
Slide 2: The problem / context
Slides 3-8: The framework / steps / insights (one idea per slide)
Slide 9: Summary / key takeaway
Slide 10: CTA (soft — "DM me" or "comment below")
```

Design rules:
- Clean, minimal design (not corporate). Dark background or white with accent color
- One idea per slide, large text (readable on mobile)
- Consistent branding (use Pilaster for template generation)
- No stock photos. Use diagrams, screenshots, architecture drawings

Technical limits:
- PDF format, max 300 pages (practical: 7-12 slides)
- 100 MB file size
- Counts as native content (no algorithm penalty)

#### Video Post (15% of content)

**When:** Builder stories with screen recordings, demo walkthroughs, talking head + code.
**Why:** Highest dwell time per post. Personal connection (face + voice = trust).
**Length:** 60-180 seconds (90s is sweet spot). Under 3 minutes always.

Structure:
```
0-3s: Hook (text overlay or verbal)
3-15s: Setup the problem/context
15-60s: The walkthrough / demo / insight
60-90s: Key takeaway
Last 5s: Soft CTA (verbal)
```

Production rules:
- Native upload only (never YouTube links)
- Captions always (70% watch without sound on mobile)
- Vertical (1080x1920) or square (1080x1080) — not landscape
- Use genpeli for editing: silence removal, caption burning, audio normalization
- Screen recording + voiceover > polished production (authenticity > polish)

Technical limits:
- Max 10 minutes (but never go past 3)
- Max 5 GB file size
- SRT caption upload supported

#### Image Post (10% of content)

**When:** Results/proof (architecture diagrams, before/after), data visualizations.
**Why:** Scroll-stopping visual. Good for technical content that benefits from a diagram.

Production rules:
- Use Pilaster for generation (branded templates, architecture diagrams)
- Single image > multi-image (carousel is better for multi)
- Include alt text for accessibility
- Pair with long caption (image + text = more algorithm signals)

Technical limits:
- Recommended: 1200x1200 or 1200x627
- Max 8 MB
- PNG or JPG

### Hook Patterns

These are proven scroll-stopping patterns for the consulting/AI builder niche.
The hook must be in the first line. It appears before "see more."

| Pattern | Template | Why It Works | Best For |
|---------|----------|-------------|----------|
| Contrarian | "Most companies fail at AI not because of [obvious]. They fail at [unexpected]." | Challenges assumptions, triggers curiosity | Industry analysis, contrarian takes |
| Confession | "I used to [common belief]. Then I [experience that changed it]." | Vulnerability + credibility | Builder stories |
| Bold claim | "[Specific number/result]. Here's exactly how." | Concrete proof, makes reader want the method | Results/proof |
| Observation | "I've worked with [N] companies on AI. The pattern I keep seeing:" | Authority through experience | AI frameworks |
| Question | "What happens when [relatable scenario]?" | Reader self-identifies, wants the answer | Any pillar |
| Myth-bust | "You don't need [thing everyone thinks you need] to [desired outcome]." | Relieves anxiety, creates curiosity | Contrarian takes, frameworks |
| Time-bound | "In [time period], I [impressive result]. Here's the breakdown." | Concrete, measurable, urgency | Builder stories, results |
| Pattern-break | "Stop [common practice]. Start [counterintuitive alternative]." | Directive, surprising | Contrarian takes |

Machine-readable format for the marketing agent:
```yaml
hooks:
  contrarian:
    template: "Most {audience} {common_action}. The ones who {win_action} do {unexpected_thing}."
    pillars: [industry_analysis, contrarian_takes]
    engagement_signal: comments  # Triggers disagreement = discussion
  confession:
    template: "I used to {belief}. Then {experience} changed everything."
    pillars: [builder_stories]
    engagement_signal: dwell_time  # Story pulls reader in
  bold_claim:
    template: "{specific_number}. Here's exactly how."
    pillars: [results_proof]
    engagement_signal: saves  # Reader bookmarks for reference
  observation:
    template: "I've {credential}. The pattern I keep seeing:"
    pillars: [ai_frameworks, industry_analysis]
    engagement_signal: shares  # "Send this to your CTO"
  question:
    template: "What happens when {relatable_scenario}?"
    pillars: [any]
    engagement_signal: comments  # Reader answers
  myth_bust:
    template: "You don't need {assumed_requirement} to {desired_outcome}."
    pillars: [contrarian_takes, ai_frameworks]
    engagement_signal: comments
  time_bound:
    template: "In {time_period}, I {result}. Here's the breakdown."
    pillars: [builder_stories, results_proof]
    engagement_signal: saves
  pattern_break:
    template: "Stop {common_practice}. Start {alternative}."
    pillars: [contrarian_takes]
    engagement_signal: shares
```

### Formatting Rules

| Rule | Why |
|------|-----|
| Hook in first line | Only 210 chars visible before "see more" |
| Line breaks between every 1-2 sentences | Whitespace = readability = dwell time |
| Arrow bullets for lists | Brand consistency (voice-profile.md) |
| No external links in body | Algorithm penalizes external clicks |
| Links in first comment only | Workaround for link penalty |
| No hashtags in body | Clutters the post, looks desperate |
| 3-5 hashtags in first comment (optional) | Discovery without visual clutter |
| Question or forward statement as closer | Triggers comments (high-weight signal) |
| Short paragraphs (1-3 sentences max) | Mobile-first reading experience |
| No exclamation marks | Confidence doesn't shout (brand.yaml anti-pattern) |

### Engagement Tactics

#### Comments Strategy

**Goal:** Every comment is a conversation starter with a potential consulting prospect.

| Tactic | How | Why |
|--------|-----|-----|
| Reply to every comment in first hour | Set a timer. Respond thoughtfully, not generically | First-hour engagement signals boost reach 3-5x |
| Ask follow-up questions | "What does that look like at your company?" | Deepens engagement, surfaces prospect pain points |
| Tag relevant people | Only when adding value, never spam-tagging | Extends reach to their network |
| Comment on prospect content | 3-5 thoughtful comments/day on ideal client profiles | Warm outreach without cold DMs |
| Never use generic responses | No "Great point!" or "Thanks for sharing!" | Kills credibility with technical audience |

#### DM Strategy

**Goal:** Convert high-signal engagement into discovery calls.

| Signal | Action | Timing |
|--------|--------|--------|
| Prospect comments on 3+ posts | Send value-add DM (not a pitch) | Within 24 hours of 3rd interaction |
| Someone shares your post | Thank + ask what resonated | Same day |
| Prospect asks a detailed question in comments | Move conversation to DM with deeper answer | Within 2 hours |
| Connection request from target profile | Accept + send welcome message (not a pitch) | Same day |

**DM templates (adapt, don't copy-paste):**
- Value-add: "Saw your comment about [topic]. We ran into the same thing at [product]. The fix was [brief insight]. Happy to go deeper if useful."
- After share: "Appreciate you sharing this. Curious — which part resonated most with your team's situation?"
- Welcome: "Thanks for connecting. Saw you're at [company] — I've been writing about [relevant topic]. Anything specific on your radar?"

**Never:** Open with a pitch, use automated DM sequences, mention pricing in first message.

#### Community Building

| Tactic | Frequency | Notes |
|--------|-----------|-------|
| Engage with 10-15 posts in target niche daily | Daily, 15 min | CTOs, VPs Eng, AI leaders — comment with substance |
| Share others' content with commentary | 1x/week | Builds goodwill, shows you read beyond your own feed |
| Participate in LinkedIn Audio Events | When relevant | Authority through live discussion |
| Create a newsletter on LinkedIn | When 1000+ followers | Deeper content, direct inbox access |

### Posting Schedule

| Day | Time (EST) | Why This Slot |
|-----|-----------|--------------|
| Monday | 8:00 AM | Morning commute readers. Start week strong |
| Tuesday | 8:30 AM | Highest engagement day (Tue-Thu) |
| Wednesday | 12:00 PM | Lunch break readers |
| Thursday | 8:00 AM | Second-highest engagement day |
| Friday | 9:00 AM | Pre-weekend wind-down. Lighter content works |

### Technical Reference

| Parameter | Value |
|-----------|-------|
| API | LinkedIn Share API v2, OAuth 2.0 |
| Rate limits | 100 posts/day (member), 150 (page) |
| Analytics API | Impressions, clicks, engagement, follower demographics |
| Character limit | 3,000 |
| Video max | 10 min / 5 GB |
| Document max | 300 pages / 100 MB |
| Image max | 8 MB (PNG/JPG) |
| Posting via | social-media-automatization MCP (`schedule_post`) |

---

## Repurposing Playbook

### Flow

```
LinkedIn post (original, algorithm-optimized)
  ├→ Twitter (condensed)
  ├→ Instagram (visual or condensed caption)
  ├→ Threads (conversational)
  └→ Facebook (bilingual ES)
```

**Timing:** Repurposed versions post 2-4 hours after LinkedIn.
This avoids duplicate-content signals and lets LinkedIn get first engagement.

### Twitter Adaptation

| Rule | Detail |
|------|--------|
| Format | Condense to 280 chars OR expand to 4-8 tweet thread |
| Hook | Keep the LinkedIn hook but tighten |
| Tone | More direct, less whitespace. Punchy |
| CTA | "Reply" or "RT if you agree" (not DM) |
| Links | OK in tweets (no penalty like LinkedIn) |
| Hashtags | 1-2 max, relevant only |
| Cadence | 3x/week |

Technical: Twitter API v2. Rate: Free tier 17 tweets/12hrs. 280 chars/tweet.

### Instagram Adaptation

| Rule | Detail |
|------|--------|
| Format | Carousel slides (from LinkedIn document) OR single image + caption |
| Hook | Visual hook on first slide/image — bold text, clean design |
| Caption | Condensed LinkedIn text, 150 words max, emoji-light |
| Reels | Only when LinkedIn video exists — re-edit for vertical 30-60s |
| Stories | Behind-the-scenes, polls, "new post" pointers |
| CTA | "Save this" or "Link in bio" |
| Cadence | 2x/week feed, daily stories |

Technical: Meta Graph API. Rate: 25 API calls/user/hour. 2,200 char caption.

### Threads Adaptation

| Rule | Detail |
|------|--------|
| Format | Text post, conversational reframe of LinkedIn content |
| Tone | More casual, like talking to a colleague. Can use "honestly," "here's the thing" |
| Length | 500 chars max. Get to the point faster |
| CTA | "What do you think?" (community-oriented) |
| Cadence | 2x/week |

Technical: Meta Threads API. Rate: 250 posts/24hrs, 50 replies/24hrs.

### Facebook Adaptation

| Rule | Detail |
|------|--------|
| Format | Bilingual post (ES translation via DeepL, reviewed) |
| Tone | Can be slightly warmer, more personal (Facebook audience) |
| Length | Full LinkedIn length is fine |
| When | Use for content with universal appeal (not too niche-technical) |
| CTA | Soft — "Comenta si te identificas" / "Comment if this resonates" |
| Cadence | 1x/week |

Technical: Meta Graph API. Rate: 200 posts/24hrs. Bilingual via social-media MCP `translate` tool.

---

## Platforms NOT Active

These platforms are paused until LinkedIn pipeline is producing results.
Revisit after 4 weeks of consistent LinkedIn posting.

| Platform | Why Paused | When to Activate |
|----------|-----------|-----------------|
| TikTok | Consulting prospects aren't there. Requires separate content (vertical video). | When brand-building for products becomes a priority |
| YouTube Shorts | Good for tutorial discovery but requires video production pipeline. | When genpeli pipeline is producing consistent video |
| Bluesky | Small audience, developer-focused. Low consulting prospect density. | When invoz needs developer marketing push |

---

## What Changed vs Last Version

**Complete rewrite.** Previous version (2026-02-26) was a platform catalog treating
all 8 platforms as equals with product-focused priorities and Late API distribution.

New version:
- Platform catalog → LinkedIn-first playbook with deep tactical detail
- Product-focused priorities → consulting authority building
- Equal-weight platforms → LinkedIn primary, 4 repurposed, 3 paused
- Late API → social-media-automatization MCP
- Added: hook patterns (8 types, machine-readable), engagement tactics (comments, DMs, community), formatting rules, repurposing playbook with per-platform adaptation rules
- Removed: TikTok, YouTube Shorts, Bluesky (paused, not deleted — documented why)
