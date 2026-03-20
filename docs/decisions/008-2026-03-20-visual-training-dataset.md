# Consultation 008: Visual Training Dataset Architecture

**Date:** 2026-03-20 | **Team:** Engineering | **CID:** CONSULT-ENG-20260320-0f9595ef

## Question

How to build a comprehensive visual training dataset for LinkedIn content generation:
1. Data schema per image
2. Organization at scale
3. Creator expansion strategy
4. End-state purpose

## Recommendation

### Data Schema

Each image gets a companion JSON sidecar with full metadata:

```json
{
  "id": "ruben-hassid-027-0",
  "creator": "Ruben Hassid",
  "creator_followers": 725000,
  "platform": "linkedin",
  "post_text": "full post text...",
  "post_type": "image+text",
  "image_file": "027-0-the-anatomy-of-a-claude-46-prompt.jpg",
  "image_format": "jpg",
  "image_bytes": 160095,
  "engagement": {
    "reactions": 5333,
    "comments": 412,
    "reposts": 89,
    "total": 5834
  },
  "classification": {
    "visual_type": "flowchart",
    "teaching_value": 9,
    "scroll_stop_power": 9,
    "content_complexity": "complex",
    "has_data_viz": false,
    "has_code": false,
    "key_visual_elements": ["boxes", "arrows", "labeled_sections"]
  },
  "scraped_at": "2026-03-18",
  "source_url": "https://media.licdn.com/dms/image/...",
  "urn": "urn:li:activity:..."
}
```

### Organization

```
/Volumes/SSD/holus/reference-library/
├── {Creator Name}/
│   ├── profile.md              # Creator analysis
│   ├── posts-raw.json          # All posts with metadata
│   ├── images/                 # Real images from CDN
│   │   ├── 001-0-title.jpg
│   │   └── 001-0-title.json    # Sidecar metadata
│   └── screenshots/            # Playwright captures (fallback)
├── _index/
│   ├── all-images.jsonl        # Master index of ALL images
│   ├── by-visual-type.json     # Grouped counts + paths
│   └── top-1000.json           # Ranked by engagement × quality
└── golden_examples/            # Already exists
```

### Creator Expansion Strategy

**Tier 1 — Fix existing (0 images due to scraper bug):**
Re-scrape Andrew Ng, Armand Ruiz, Allie K Miller, Santiago Valdarrama,
Cassie Kozyrkov, Sundas Khalid with image download enabled.
These creators have 40 posts each but 0 images — scraper tagged all as "video".

**Tier 2 — Add visual-first LinkedIn creators (AI/tech):**
- Zain Kahn (AI newsletter, 1M+ followers, heavy infographics)
- Lenny Rachitsky (product, carousels that get 5K+ reactions)
- Justin Welsh (solopreneur, clean text + image templates)
- Sahil Bloom (frameworks/checklists, 1M+ followers)
- Ben Tossell (AI tools, screenshots + tutorials)
- Irina Stanescu (Google, architecture diagrams)
- Yasin I. Özbey (AI visualizations, flowcharts)
- Matt Shumer (AI products, product screenshots)
- Linas Beliūnas (fintech, data visualizations)
- Aakash Gupta (product strategy, frameworks)

**Tier 3 — Beyond tech (visual excellence):**
- Chris Do (design, carousels with 10K+ reactions)
- Adam Grant (psychology, quote cards with massive reach)
- Gary Vaynerchuk (text-on-image format, massive scale data)

### Purpose / End-State

Three use cases, in priority order:

1. **Few-shot prompt grounding (immediate):**
   Top 3-5 images per visual type → injected into VISUAL_DESIGNER_SYSTEM
   as text descriptions. The LLM sees "Ruben Hassid's flowchart had:
   8 nodes, vertical layout, brand orange accent" and generates specs
   matching that quality level.

2. **Rubric calibration (week 2):**
   Use the engagement data to calibrate the visual quality rubric.
   "Teaching independence 9 + engagement 5000 = this is what a 9 looks like."
   The judge learns what scores correlate with real engagement.

3. **Style replication (week 4+):**
   Given enough examples per creator, the system can generate
   "in the style of Armand Ruiz" or "in the style of Ruben Hassid"
   by including their top 3 images as reference in the prompt.

## Action Items
- [ ] Build master scraper that downloads ALL media (images, GIFs, PDFs) with sidecar JSONs
- [ ] Re-scrape 6 existing creators with image download (Andrew Ng, Armand Ruiz, etc.)
- [ ] Add 10 new visual-first creators (Tier 2 list)
- [ ] Build _index/all-images.jsonl master index
- [ ] Build _index/top-1000.json ranked by engagement × teaching_value
