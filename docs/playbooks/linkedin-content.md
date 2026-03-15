# LinkedIn Content Playbook

## Core Rule

**No standalone text posts.** Every post published from Holus must have a visual
attached. Text captions exist to accompany a visual — not to stand alone.

## The 3 Post Types

### 1. Text + Carousel (PDF)

A written argument fully expressed as swipeable slides.

- **Caption:** Short hook, 150–255 visible characters. Teases the carousel, does not
  summarize it. Ends with "Swipe →" or similar.
- **PDF:** 8–10 slides. Square (1080×1080px) or portrait (1080×1350px). Max 3 MB.
- **Slide 1:** The hook — 8 words or fewer. High contrast. Stops the scroll.
- **Body slides:** One idea per slide. Max 30 words. 3-second readability.
- **Last slide:** CTA — a question or single action. Most-lingered-on slide.
- **No links inside the PDF** — LinkedIn penalizes outbound links. Links go in comments.

**Best for:** Frameworks, step-by-step breakdowns, contrarian takes with evidence,
comparisons (X vs Y), industry analysis.

**Engagement:** 6.6% avg — 596% higher than text-only.

---

### 2. Text + Image

A caption paired with a single graphic that reinforces or extends the message.

- **Caption:** Can be longer than carousel caption — the image supports but the text
  carries the argument. 500–900 characters.
- **Image:** Quote card, data callout, insight graphic, or diagram. 1080×1080px.
- **Image rule:** The image must add something the text does not say. Not decoration.

**Best for:** Single insights, quotes worth highlighting, stats, before/after moments.

---

### 3. Text + Video

Juan on camera. Caption sets context, video delivers the point.

- **Caption:** 150–300 characters. One sentence that makes the viewer want to watch.
- **Video:** Juan records. Genpeli edits — silence cuts, word-by-word captions,
  audio normalization. 60–90 seconds optimal for LinkedIn.
- **Script:** Holus writes the script. Juan reads and records. Genpeli edits.
- **Captions burned in** — autoplay is muted by default. Captions are not optional.

**Best for:** Personal stories, building-in-public moments, live demo walkthroughs,
opinion pieces where Juan's voice matters.

---

## Bilingual Publishing

Every piece is produced in English first, then Spanish — staggered.

- **Primary language:** English (posted first)
- **Secondary language:** Spanish (posted 3–4 days later, same account)
- **LinkedIn language tag:** Set per post so LinkedIn surfaces each to the right audience
- **Translation rule:** Localized, not translated. Spanish version adapts tone and phrasing
  for the Spanish-speaking audience — it is not a word-for-word translation.

This bilingual stagger is a **pipeline config** — not hardcoded to any person or language.
Any user of this system can configure their own language pair and stagger interval in
`config/localization.yaml`.

---

## What the Pipeline Produces Per Idea

For each raw idea, the planner (Opus) decides which post type fits best — or multiple
types if the idea has range. The output always includes:

1. The text caption (written for the specific post type)
2. The content artifact spec:
   - Carousel → slide-by-slide JSON outline (fed to PDF renderer)
   - Image → visual brief (fed to Pilaster)
   - Video → script (Juan records, Genpeli edits)
3. A localized (Spanish) version of both caption and artifact spec

**The planner does not default to text-only.** If an idea does not fit carousel,
image, or video, it is not posted — it is flagged for refinement.

---

## Production Stack

| Component | Tool |
|-----------|------|
| Caption + carousel outline | Holus (idea_runner.py) |
| PDF render | Python PDF renderer (reportlab/weasyprint) — to be built |
| Image generation | Pilaster MCP |
| Video script | Holus (idea_runner.py) |
| Video editing | Genpeli |
| Localization | bilingual-localizer agent |
| Publishing | social-media-automatization (targets: legacy mode) |
| Review + approve | Observatory (localhost:3000/content) |
