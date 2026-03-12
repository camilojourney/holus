# LinkedIn Platform Knowledge
# Last updated: 2026-03-08
# Source: operator experience + published LinkedIn algorithm research

---

## What Works

**Long-form text outperforms short.** Posts with 1,000–1,300 chars consistently
outreach short ones. LinkedIn rewards dwell time — longer posts mean readers
stay on the post longer, which signals quality to the algorithm.

**Personal stories get 3–5x more reach than company news.** "I built X and it
failed" outperforms "We're excited to announce Y". First-person practitioner
perspective is the signal LinkedIn's audience responds to.

**Carousels get high save rates but lower comments.** Saves = people coming back
to use the content. Comments = people reacting in the moment. Carousels perform
as reference material — strong for building authority, weaker for conversation.

**Posting time matters.** Peak windows: Tuesday–Thursday, 8am–10am local time.
Avoid Monday (people are catching up) and Friday afternoon (checked out).
Sunday evening also works for a segment of the audience (prepping for the week).

---

## Algorithm Patterns

**Dwell time > likes.** LinkedIn tracks how long someone pauses on a post.
A post with 200 people who read to the end beats a post with 500 likes from
people who scrolled past.

**Comments beat reactions.** A comment (even short) signals engagement depth.
Comments trigger the algorithm to push the post further. Ask a specific question
at the end of posts — not "what do you think?" but a question only practitioners
can answer.

**First 60 minutes set trajectory.** Early engagement (comments, reactions,
shares) in the first hour determines whether LinkedIn shows the post to your
second-degree network. Post when your core audience is online. Do not post
and go offline.

**Reshares have limited amplification.** LinkedIn's algorithm does not reward
reshares the same way as original engagement. Resharing to a personal network
helps reach but does not push to the algorithm's distribution pool the same way
original comments do.

---

## EN/ES Bilingual Strategy

**Post EN first. Schedule ES version 3 days later.**

Why this works:
- LinkedIn audience skews EN-dominant globally. EN version captures maximum
  first-wave reach.
- ES version catches a different scroll session and a different segment of
  Camilo's network (Latin American practitioners, Spanish-speaking founders).
- 3-day lag avoids the two posts competing with each other in the same feed cycle.
- Same content performs independently — different language = different post,
  not duplicate content in LinkedIn's view.

**LinkedIn API note:** The API supports a `localizedBody` field for native
multilingual posts (one post, multiple language versions). This is cleaner
but harder to A/B test separately. Current approach: 2 separate posts, 3-day lag.

**Flag for social-media-automatization:** The scheduler needs a `scheduled_at`
parameter to queue the ES version automatically after the EN version posts.
Without this, someone has to manually queue the second post.

---

## Content Format Guide

| Format | Max length | Algorithm boost | Save rate | Comment rate |
|--------|-----------|----------------|-----------|-------------|
| Text post | 1,300 chars before "see more" | High (dwell time) | Low | High |
| Carousel (PDF) | 10–15 slides recommended | Medium | Very high | Low |
| Single image | N/A | Medium | Low | Medium |
| Video (native) | Up to 10 min | High (watch time) | Low | Medium |
| External link post | N/A | Very low | N/A | Low |

**Carousels = PDF attachment, not native slides.** LinkedIn does not have a
native carousel format (unlike Instagram). To post a carousel on LinkedIn,
upload a PDF. Each page = one slide. Pilaster can generate these as image
sequences → merged PDF.

**No external links in post body.** Links in the post body suppress reach —
LinkedIn does not want to send people off-platform. Put the link in the
first comment instead. This is the standard workaround and widely known by
the algorithm.

**One image > carousel for raw reach.** A single strong image gets shown to
more people. Carousels get more saves from people who see them. Tradeoff:
reach vs. depth.

**Text posts: hook before "see more" cutoff.** The first 2–3 lines are shown
before LinkedIn collapses the post. Those lines must earn the click.

---

## Anti-Patterns

- **Links in post body** — kills reach. Always put in first comment.
- **Starting with "I"** — opening line starting with "I" performs measurably
  worse. Start with the insight, the number, the provocative statement.
- **Generic questions** — "What do you think about AI?" gets ignored.
  Ask something specific: "What's the one thing that broke your first AI pipeline?"
- **Emojis as bullet points** — signals low-effort content. Use → or numbered
  lists. One emoji maximum per post (optional).
- **"Excited to announce" language** — company-speak. LinkedIn users scroll
  past it. Reframe as what this means for the reader.
- **Posting too frequently** — more than once per day competes with yourself
  in the algorithm. Once per day maximum; 3–5x per week is the practical
  sweet spot for sustained growth.
- **No hook before the fold** — if the first line doesn't earn the "see more"
  click, the post's effective reach is cut by 60–80%.
