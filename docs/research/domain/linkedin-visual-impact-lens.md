# LinkedIn Visual Impact Lens

Date: 2026-06-18

## Scope

This note captures lessons for Holus image generation from high-performing LinkedIn infographic/news-style visuals.

FACT: We do not currently have access to a verified corpus of the top 100 LinkedIn images by view count.

FACT: Public LinkedIn pages expose likes/comments for some posts, but not a reliable global "top viewed images" dataset.

FACT: A direct attempt to inspect `https://www.linkedin.com/feed/` through Chrome reached LinkedIn's login page, so this run did not access the user's authenticated LinkedIn feed or private analytics.

ASSUMPTION: The best available approach without private analytics is to combine public high-performing examples, creator analyses, platform specs, and our own run results.

## Reference Image Pattern

The provided AMD vs NVIDIA image works because it is not merely an image. It is a compact news artifact.

Structure:

- context eyebrow: "AI infrastructure just got a real competitor"
- huge claim: "same memory, same bandwidth"
- numeric hook: "$700 less"
- compared subjects: AMD vs NVIDIA
- proof grid: price, memory/bandwidth, raw compute, OS support
- verdict strip: "not faster on raw silicon, smarter on real-world AI"
- footnote/source caveat

Lessons:

- One claim dominates the entire asset.
- The strongest number is treated like the visual hero.
- Evidence is compressed into a table, not hidden in the caption.
- Red/green contrast maps to the comparison.
- The verdict is separate from the evidence.
- The post is mobile-first and readable inside a phone feed.

## Public Research Signals

Buffer's 2026 LinkedIn carousel guide says carousels perform strongly, lists industry news, data visualization, product showcases, zero-click content, and thought leadership as reusable formats, and highlights digestible formatting, consistent visual branding, synthesized sourcing, and narrative arc.

Pierre Herubel's analysis of top LinkedIn infographics says comparison posts and high-level frameworks dominate because readers get multiple insights and save reusable frameworks.

Sarah Hart's public LinkedIn carousel analysis used popular posts with 800+ likes and found dense but controlled pages with around 20-30 words per page and 5-7 words per line in common examples.

The provided AMD/NVIDIA news source from Tom's Hardware confirms the factual pattern behind the screenshot: AMD's Ryzen AI Halo Developer Platform is priced at $3,999, NVIDIA DGX Spark rose to $4,699, both target local AI workstation/developer use, and the key difference includes Windows support for AMD versus Linux-only NVIDIA.

LinkedIn's own ad specs recommend square images for broad delivery, while current carousel guidance generally favors 1080x1080 or 1080x1350 for feed-safe mobile layouts.

## Lens Rules Added To Holus

The system now applies a LinkedIn impact lens after proximity routing and before provider dispatch.

Core requirements:

- one scroll-stopping top claim
- one visible evidence structure below the claim
- one clear verdict or takeaway panel
- mobile-first hierarchy readable at thumbnail size

News battlecard pattern:

- headline claim
- one numeric delta
- two compared subjects
- compact evidence grid with 3-5 rows
- bottom verdict strip
- source/caveat line when claims are factual

Mode-specific patterns:

- chart: claim-led chart card with one metric contrast and verdict
- product scene: selected item -> reason/evidence -> decision
- workflow: operating map with input, output, and highlighted bottleneck
- person story: artifact causes the human decision; face is secondary
- typography: exact thesis plus one support line
- object metaphor: one object, one tension, one verdict line

## Generation Strategy Added To Holus

Holus now separates the visual concept route from the rendering path.

Deterministic template path:

- news battlecards
- comparison tables
- claim-led charts
- workflow/operating maps
- product decision surfaces
- typography thesis posters
- framework grids

AI image path:

- single physical metaphors

Hybrid path:

- person/story artifacts where the image model creates the vignette but the deterministic strategy constrains layout, palette, and required artifact/action

Design intelligence:

- the strategy chooses a named palette, typography style, icon style, chart style, layout density, and guardrails
- palettes vary by pattern and content signal, so deterministic outputs do not all look identical
- factual comparison posts use a red/green battlecard palette
- human/artifact stories use a warmer notebook palette
- typography cards use a mono/accent system
- charts and product surfaces use editorial or technical palettes depending on the content signal

## Public LinkedIn Example Eval

After adding the synthetic 100-case eval, we added a second eval using accessible public LinkedIn post snippets and the user-provided screenshot pattern.

This found real bugs that the synthetic eval missed:

- `same audience, same timing` incorrectly triggered the news battlecard path because `same` was too broad as a battlecard signal
- `ranking system` incorrectly triggered chart routing because `rank` matched inside `ranking`
- `creator points at one sentence` incorrectly missed person/story routing because only past-tense `pointed` was recognized

Fixes:

- battlecard signals now require stronger comparison/price/competitor signals
- chart `rank` detection now uses word boundaries
- person/story routing recognizes `points`, `marks`, `circles`, and `creator`

The public LinkedIn eval now covers:

- product/news battlecards
- AI model comparison tables
- B2B vs B2C comparison posts
- carousel vs infographic performance posts
- document-post metric comparisons
- carousel evolution posts
- LinkedIn algorithm update/system posts
- infographic design-rule posts
- template/system posts
- metaphor posts
- artifact/story posts
- thesis/caption-dependency posts

## Failure Modes To Avoid

- pretty scene without proof
- generic SaaS dashboard
- fake unreadable paragraphs
- invented prices, benchmarks, specs, or logos
- stock-photo person looking at laptop
- unstructured collage
- visual that only makes sense after reading the caption

## Next Work

The next real upgrade is not more prompt text. It is a multimodal visual judge that scores:

- claim readability
- evidence presence
- factual-source discipline
- verdict clarity
- mobile thumbnail legibility
- "generated slop" risk

The same `VisualJudgeDecision` contract can support this later.

## Sources

- Tom's Hardware, AMD Ryzen AI Halo vs NVIDIA DGX Spark news: https://www.tomshardware.com/desktops/mini-pcs/amd-challenges-nvidias-dgx-spark-with-usd3-999-ryzen-ai-halo-with-windows-11-support-strix-halo-desktop-undercuts-nvidia-by-usd700-packs-128gb-of-unified-memory
- Buffer, LinkedIn carousel examples and best practices: https://buffer.com/resources/linkedin-carousel-examples/
- Pierre Herubel, top LinkedIn infographic patterns: https://pierreherubel.substack.com/p/my-top-7-linkedin-infographics-this
- Sarah Hart, viral LinkedIn carousel design analysis: https://www.linkedin.com/posts/sarahhartcreative_lets-analyze-11-viral-linkedin-carousel-activity-7171119838545833984-ug8h
- LinkedIn single image ad specs: https://business.linkedin.com/advertise/ads/sponsored-content/single-image-ads-specs
