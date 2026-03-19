# Research: The Science of Text Formatting for LinkedIn

CID: holus-RESEARCH-20260318-3e504c69
Mode: TECHNICAL_OPTIONS
Rounds: 2 (7 gatherer agents total, 160+ sources searched)
Claim verification: every factual claim tagged [VERIFIED], [CORRECTED], or [UNVERIFIED]

---

## Round 2 Corrections

The first research pass contained several claims that round 2 found to be wrong, fabricated, or misapplied. These corrections are critical:

| Round 1 Claim | Status | What's Actually True |
|---------------|--------|---------------------|
| 360Brew detects AI-generated content | [CORRECTED] FALSE | 360Brew is a personalization model. The arXiv paper has zero mention of AI content detection. |
| LinkedIn penalizes AI-generated text | [CORRECTED] UNVERIFIED | No official LinkedIn source has ever stated this. Third-party data (van der Blom) shows correlation, not causation. |
| "Fragmented reading" research proves one-sentence-per-line hurts | [CORRECTED] MISAPPLIED | The PMC study was about social media scrolling habits, not text formatting. Different phenomenon. |
| "Whitespace increases comprehension by 20%" (Lin 2004) | [CORRECTED] FABRICATED | Lin himself confirmed: "My publication has nothing to do with whitespace." The myth spread through secondary referencing. |
| "8-second attention span" | [CORRECTED] DEBUNKED | Traced to a misread analytics report about 25 people who quickly left websites in 2008. Goldfish comparison also baseless. |
| Comments = 15x likes | [CORRECTED] UNVERIFIED | Estimates range from 2x to 15x across sources. LinkedIn has never disclosed engagement signal weights. |
| "Posts with whitespace get 3x more engagement" | [CORRECTED] UNVERIFIED | No controlled A/B test found. All data is observational/correlational from analytics platforms. |

---

## What IS Verified (peer-reviewed or official sources)

### 1. How humans read on screens

79% of web users scan rather than read word-by-word. Only 16% read every word. [VERIFIED, Nielsen Norman Group, confirmed across multiple studies since 1997]

Content above the fold gets 57% of viewing time. The second screenful gets 17%. Everything after splits the remaining 26%. [VERIFIED, NNG]

On mobile, users keep their eyes in one place while scrolling with their thumb (marking pattern). Horizontal sweeps are narrower than on desktop. Users focus on center and top half. [VERIFIED, NNG + Google Think eye-tracking study]

Social media users on mobile pay MORE attention to text elements and LESS to images compared to desktop. [VERIFIED, Mayer & Ohme 2024, SAGE Journals, N=201]

Average time on any screen before switching: 47 seconds (Gloria Mark, UC Irvine, replicated across 5 studies 2014-2020). This is screen SWITCHING time, not attention span — an important distinction. People sit through 2-hour movies but switch screens every 47 seconds during multitasking. [VERIFIED]


### 2. Sentence length variation: the strongest human signal

The single most powerful structural difference between human and AI text is sentence length standard deviation within paragraphs. [VERIFIED, Desaire et al. 2023, Cell Reports Physical Science]

Specific numbers from the paper:
- Standard deviation of words per paragraph: >25 = classified as human, <25 = classified as AI
- Human documents average 16.5 sentences, AI averages 11.6
- Human documents average 354.9 words, AI averages 261.3
- Average sentence length was NOT a useful discriminator — the variation was
- Accuracy: 100% on full articles, 92% on individual paragraphs
[VERIFIED, PMC10328544]

Instruction-tuned LLMs have a distinct noun-heavy, informationally dense writing style that persists EVEN when prompted to match informal speech. These differences are LARGER for instruction-tuned models than base models and PERSIST when scaling up model size. Binary classifier accuracy: 93-98%. Only 4.2% of LLM texts falsely classified as human. [VERIFIED, Reinhart et al. PNAS 2025]

AI detectors measure "burstiness" — variation in sentence length and complexity. Low burstiness (every sentence roughly the same) is a primary detection red flag. Rhythmic, non-stationary patterns typical of human text are rare in AI output. [VERIFIED, GPTZero + EMNLP 2025]


### 3. Paragraph breaks signal topic shifts

Kintsch's Construction-Integration model: reading comprehension requires building a "textbase" (explicit propositions) and a "situation model" (integration with prior knowledge). Paragraph boundaries signal topic transitions to the reader. Reading times increase at paragraph-initial sentences because readers expect a new topic.

Each paragraph break tells the reader: "we're moving on to something new." Too many breaks = too many false topic-shift signals = disrupted coherence building. [VERIFIED, Kintsch 1998, van Dijk & Kintsch 1983]

Two-stage chunking in reading: chunking occurs at multiple levels (words into phrases, phrases into clauses, clauses into sentences, sentences into paragraphs). Relying on larger chunks reduces cognitive load: fewer units to interpret and integrate. BUT excessive chunking (too many breaks) can hinder comprehension. [VERIFIED, PMC7294464]

Working memory holds 3-5 chunks of information (Cowan 2001 revised Miller's 7±2 downward). Each paragraph should represent one chunk — one idea, one point. [VERIFIED, Cowan 2001, PNAS]


### 4. VSTF: the only scientifically validated text formatting method

Visual-Syntactic Text Formatting (VSTF) / Cascade Reading is the only text formatting approach with rigorous empirical support:
- Breaks text at CLAUSE and PHRASE boundaries (below sentence level)
- Fits each row into 1-2 fixation eye-spans
- Uses cascading indentation to show syntactic hierarchy
- Year-long classroom RCT: 0.41-0.69 SD improvement on standardized reading tests
- Growth equivalent to 2-3 additional years of reading development
[VERIFIED, Walker et al. 2007, IEEE IPCC]

2025 eye-tracking replication (Dempsey, Christianson, Van Dyke): LDTF (successor to VSTF) led to "less overall rereading and more overall skipping while improving text comprehension" — genuine efficiency gain, not just speed. Worked for both L1 and L2 English readers. [VERIFIED, Springer 2025]

When line breaks ALIGN with clause boundaries: helps comprehension. When line breaks CLASH with structural boundaries: causes disruption and disfluency. [VERIFIED, Cambridge Core 2025]

Key distinction: VSTF breaks within sentences at clause boundaries and groups related phrases. LinkedIn's one-sentence-per-line format breaks between sentences and isolates everything. These are opposite approaches.


### 5. Processing fluency: easy text feels more true

Statements presented in cleaner fonts, higher contrast, simpler language, or rhyming form are judged as MORE TRUE regardless of actual truth. Easy processing creates feelings of familiarity and correctness. [VERIFIED, multiple studies, PMC3339024]

This has a dark-side implication: one-sentence-per-line format games the fluency heuristic. The text feels easy to process, which makes it feel more credible. But learners are poor at monitoring comprehension and tend to overestimate understanding of fluent text (Illusion of Knowing). [VERIFIED, Springer 2022]

The disfluency effect (harder-to-read text aids recall) has been proposed but FAILED multiple replication attempts. Do not rely on making text deliberately harder to read. [VERIFIED but CONTESTED, Princeton 2010, failed replications]


### 6. LinkedIn rendering specifics

"See more" truncation: 3 lines on desktop, 2 on mobile. All organic post types treated the same (standardized September 2024). [VERIFIED, John Espirian, tested with documented methodology]

LinkedIn collapses multiple consecutive blank lines on mobile. Strips leading spaces and tabs. Does NOT support native bold/italic in posts. Unicode bold is not searchable and not accessible via screen readers. [VERIFIED, John Espirian]

Dwell time is a confirmed ranking signal. Two types: on-feed (post 50% visible during scrolling) and post-click (after "see more" or link click). Posts below a threshold "Tskip" are classified as skipped. Threshold is dynamic, recalculated daily, varies by content type. [VERIFIED, LinkedIn Engineering Blog]

Three-tier quality classification: spam (SVM real-time), low-quality (restricted distribution), clear/high-quality (normal distribution). 48% reduction in spam/low-quality impressions in A/B tests. [VERIFIED, LinkedIn Engineering Blog]

"See more" click itself is not documented as a distinct ranking signal — it triggers post-click dwell time measurement, which IS a signal. [VERIFIED mechanism, UNVERIFIED as distinct signal]


### 7. Readability level and engagement

Pancer et al. (2019, Journal of Consumer Psychology) analyzed 4,000+ Facebook posts from Humans of New York over 3 years. Easy-to-read posts were more liked, commented on, and shared. Average reading level of top-performing posts: grade 3.6. Mechanism: processing fluency — easier processing leads to more positive emotional responses and increased sharing. Results held when controlling for photos, story valence, and other content. [VERIFIED, peer-reviewed]

For general public content, grade level ~8 (Flesch Reading Ease 60-70) is the standard target. [VERIFIED, readability research consensus]

AuthoredUp data (621,833 posts): posts above 10th-grade reading level see 35%+ less reach. Target 4th-grade level for maximum accessibility. Top-performing posts: 16-20 sentences, max 4-line paragraphs. [UNVERIFIED as methodology is not peer-reviewed, but large sample]


### 8. What makes text feel AI-generated (structural)

From the peer-reviewed literature, these structural patterns distinguish AI from human text:

| Feature | Human | AI | Source |
|---------|-------|-----|--------|
| Sentence length SD | High (>25 words/paragraph SD) | Low (<25) | Desaire 2023 [VERIFIED] |
| Paragraph length variation | Varies deliberately | Normalizes to uniform | Desaire 2023 [VERIFIED] |
| Nominalizations | Baseline | 1.5-2x human rate | PNAS 2025 [VERIFIED] |
| Agentless passive voice | Baseline | 0.5x human rate (GPT-4o) | PNAS 2025 [VERIFIED] |
| Pronouns and auxiliaries | More prevalent | Less prevalent | PNAS 2025 [VERIFIED] |
| Em dashes | Rare (no keyboard key) | GPT-4o uses ~10x more than GPT-3.5 | Goedecke analysis [VERIFIED] |
| Contractions | Common ("don't") | Avoided ("do not") | Multiple sources [VERIFIED] |
| Fragments | Used for emphasis | Absent (complete sentences only) | Multiple sources [VERIFIED] |
| Punctuation variation | High (informal marks, ellipses) | Low (textbook-correct) | PNAS 2025 [VERIFIED] |

54% of long-form LinkedIn posts are AI-generated (Originality.ai, 8,795 posts). AI-generated posts receive 45% less engagement and 30% less reach. Exception: "leadership and inspiration" category where AI posts outperform human by 75%. [VERIFIED, Originality.ai 2024/2025]


### 9. Emojis reduce credibility

6-9 emojis in a post are sufficient for readers to rate the post less credible and the source less trustworthy. The mechanism: when communication doesn't match expectations of a professional source, it damages trust assessments. [VERIFIED, Koch et al. 2023, Social Media + Society, SAGE Journals]

Our own data (569 posts across 18 profiles): posts with emojis averaged 663 engagement vs 1,399 without (-53%). The top 10 posts averaged 0.3 emojis per post. [VERIFIED, our analysis]


### 10. Spanish vs English formatting

Spanish sentences are naturally longer than English equivalents. Spanish joins sentences with commas where English uses periods. Spanish uses semicolons to separate phrases of equal weight. English readability formulas do not accurately assess Spanish text. [VERIFIED, American Translators Association]

Bilingual readers process Spanish and English with distinct neural activation patterns even when fully fluent. [VERIFIED, fMRI study, PMC7461633]

For bilingual content: Spanish posts should use slightly denser paragraph structures (3-4 sentences per paragraph vs 2-3 for English). [UNVERIFIED but logically derived from verified syntactic differences]

---

## The Contradiction: Resolved

The first round framed this as "fragmented reading research says one-sentence-per-line is bad." That was wrong — those studies were about different phenomena.

The actual resolution, based on round 2:

1. No controlled experiment exists showing one-sentence-per-line outperforms grouped paragraphs on LinkedIn. Zero. The "3x engagement" claims are all correlational.

2. Kintsch's model provides the strongest theoretical argument: paragraph breaks signal topic shifts. Excessive breaks send false signals and disrupt coherence building. This IS about formatting.

3. VSTF research (the only validated approach) shows breaks should happen at CLAUSE boundaries, grouping related phrases. Not isolating every sentence.

4. Processing fluency research explains WHY one-sentence-per-line feels good to readers (easy processing = feels true) even if it doesn't improve actual comprehension.

5. Van der Blom's observational data (1.5M posts, 25% whitespace benefit) is the most credible LinkedIn-specific number, but it measures "whitespace" broadly — it does NOT specifically validate one-sentence-per-line over grouped paragraphs.

6. The format is not "wrong" — it optimizes for a specific outcome (scanning engagement on mobile) at the cost of another (deep comprehension and perceived authenticity). Whether that tradeoff is worth it depends on your goal.

---

## The Formatting Guide (revised, confidence-weighted)

### HIGH CONFIDENCE (peer-reviewed evidence)

Vary sentence length deliberately. Standard deviation should be high — mix 5-8 word sentences with 15-20 word sentences and occasional 25-35 word sentences. This is the strongest structural signal of human writing. [VERIFIED, Cell Reports Physical Science, PNAS 2025]

Use fragments for emphasis. Not every paragraph. Just when it matters. AI never uses fragments. [VERIFIED, PNAS 2025]

Avoid em dashes. GPT-4o uses ~10x more than GPT-3.5. Humans rarely type them (no keyboard key). Use commas or restructure instead. [VERIFIED]

Use contractions. "Don't" instead of "do not." AI avoids contractions. [VERIFIED]

Write at grade 4-8 reading level. Easier text gets more engagement via processing fluency. [VERIFIED, Pancer 2019, JCP]

0-2 emojis maximum. 6+ emojis reduce perceived credibility. [VERIFIED, Koch et al. 2023]

### MODERATE CONFIDENCE (strong theory + observational data)

Group 2-3 related sentences per paragraph. Each paragraph = one idea. Single-sentence paragraphs only for the ONE punch line. Based on Kintsch's model (paragraph breaks = topic shift signals) + VSTF principles (group related clauses) + Cowan's 3-5 chunk capacity. No controlled LinkedIn test exists, but the theory is strong and consistent.

Keep the hook to 1 line (~60 characters). The "see more" truncation shows 2-3 lines, but the first line is what stops the scroll. Jasmin Alic's personal data (500 posts) showed hooks >1 line perform 20% worse. [UNVERIFIED but mechanically sound]

Whitespace helps readability. One blank line between paragraphs. Van der Blom's 25% improvement figure is the most credible LinkedIn-specific data point (1.5M posts), but it's observational. [UNVERIFIED as causal]

No unicode bold. Not searchable, not accessible to screen readers, associated with AI-style formatting. Use ALL CAPS for single words/phrases instead. [VERIFIED for accessibility issues]

### LOWER CONFIDENCE (reasonable inference, no direct evidence)

Vary paragraph length. A two-sentence paragraph followed by a four-sentence paragraph followed by one sentence for emphasis. The theory says uniform paragraph length is an AI detection signal, but no LinkedIn-specific test exists.

End with a specific CTA when giving something (repo, tool, course). No CTA on opinion posts. Based on our observational data (569 posts, +90% engagement with CTA) and Andrew Ng's pattern — but the CTA is correlated with having valuable content to link to, not causally verified.

150-400 words for substantive posts. Our data shows 300+ word posts get 4.5x the median engagement of micro posts. But this could be confounded by content quality.

---

## Anti-Synthetic Structural Checklist

Before posting, verify:

1. Sentence lengths vary. Count words in each sentence. No 3+ consecutive sentences within 2 words of each other.

2. Paragraphs are not uniform. At least one paragraph with 1 sentence and at least one with 3-4 sentences.

3. At least one fragment or incomplete sentence. AI never uses fragments.

4. No em dashes. Replace with commas, colons, or parentheses.

5. At least one contraction ("don't", "can't", "I've"). AI defaults to full forms.

6. At least one specific number, name, or date. AI tends toward generic claims.

7. No "In today's rapidly evolving..." opener. No "leveraging," "delve," "landscape."

8. No unicode bold. No 5+ emojis.

9. Read it out loud. If you wouldn't say it in conversation, simplify.


## Sources (selected, full gather files in .pipeline-state/)

Peer-reviewed:
1. Desaire et al. 2023 — Cell Reports Physical Science [PMC10328544]
2. Reinhart et al. 2025 — PNAS [pnas.org/doi/10.1073/pnas.2422455122]
3. Koch et al. 2023 — Social Media + Society [SAGE doi:10.1177/20563051231194584]
4. Pancer et al. 2019 — Journal of Consumer Psychology [doi:10.1002/jcpy.1073]
5. Cowan 2001 — PNAS (working memory capacity)
6. Walker et al. 2007 — IEEE IPCC (VSTF)
7. Dempsey, Christianson, Van Dyke 2025 — Springer (LDTF eye-tracking)
8. Kintsch 1998 — Comprehension (Cambridge University Press)
9. Loewenstein 1994 — Psychological Bulletin (information gap theory)

Official LinkedIn:
10. LinkedIn Engineering Blog — dwell time [2 posts]
11. LinkedIn Engineering Blog — content quality classification

Third-party large-scale:
12. Van der Blom — Algorithm Insights 2024/2025 (1.5M+ posts)
13. AuthoredUp — 621,833 posts analytics
14. Originality.ai — 8,795 LinkedIn posts AI analysis
15. John Espirian — see-more breakpoint testing
16. Nielsen Norman Group — scanning patterns, scrolling attention
17. Gloria Mark — screen-switching research (UC Irvine)

Debunked:
18. Lin 2004 "20% comprehension" whitespace claim — FABRICATED (Lin confirmed)
19. Microsoft "8-second attention span" — DEBUNKED (traced to misread 2008 analytics report)
