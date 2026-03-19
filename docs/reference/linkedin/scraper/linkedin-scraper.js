#!/usr/bin/env node
/**
 * LinkedIn Post Scraper — Playwright
 *
 * Scrapes a LinkedIn creator's recent posts: text, engagement metrics,
 * post type, hashtags, timestamps, and screenshots.
 *
 * Usage:
 *   node linkedin-scraper.js --handle alexwang2911 --max-posts 50
 *   node linkedin-scraper.js --handle svpino --max-posts 30 --login
 *
 * First run: use --login to authenticate (opens browser or uses .env credentials).
 * Subsequent runs reuse the saved session.
 */

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

// Load .env from holus root
const envPath = path.resolve(__dirname, "../../../../.env");
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, "utf-8").split("\n")) {
    const match = line.match(/^([A-Z_]+)=(.+)$/);
    if (match) process.env[match[1]] = match[2].trim();
  }
}

// ── Config ──────────────────────────────────────────────────────────────────

const BASE_DIR = path.join(__dirname, "..");
const SESSION_DIR = path.join(__dirname, ".session");
const SCROLL_DELAY_MIN = 2000;
const SCROLL_DELAY_MAX = 4500;
const POST_EXTRACT_DELAY_MIN = 800;
const POST_EXTRACT_DELAY_MAX = 1500;

// ── Arg parsing ─────────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { handle: null, maxPosts: 50, login: false, headless: false };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--handle" && args[i + 1]) config.handle = args[++i];
    if (args[i] === "--max-posts" && args[i + 1])
      config.maxPosts = parseInt(args[++i]);
    if (args[i] === "--login") config.login = true;
    if (args[i] === "--headless") config.headless = true;
  }

  if (!config.handle) {
    console.error("Usage: node linkedin-scraper.js --handle <linkedin_handle> [--max-posts 50] [--login] [--headless]");
    process.exit(1);
  }
  return config;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function sleep(min, max) {
  const ms = max ? Math.floor(Math.random() * (max - min) + min) : min;
  return new Promise((r) => setTimeout(r, ms));
}

function sanitize(text) {
  return text
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 5000);
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
}

// ── Login flow ──────────────────────────────────────────────────────────────

async function loginFlow(browser) {
  const email = process.env.LINKEDIN_EMAIL;
  const password = process.env.LINKEDIN_PASSWORD;

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
  });

  const page = await context.newPage();
  await page.goto("https://www.linkedin.com/login", { waitUntil: "domcontentloaded" });
  await sleep(2000, 3000);

  if (email && password) {
    console.log("→ Auto-login with .env credentials...");
    await page.fill("#username", email);
    await sleep(300, 600);
    await page.fill("#password", password);
    await sleep(500, 1000);
    await page.click('button[type="submit"]');
    await sleep(5000, 8000);

    const url = page.url();
    if (url.includes("/feed") || url.includes("/mynetwork")) {
      console.log("✓ Login successful.");
    } else if (url.includes("challenge") || url.includes("checkpoint")) {
      console.log("⚠ LinkedIn verification required — check your email/phone.");
      console.log("  Waiting 3 minutes for manual verification...");
      await page.waitForURL("**/feed/**", { timeout: 180000 });
    } else {
      console.log("⚠ Unexpected redirect:", url);
    }
  } else {
    console.log("\n╔══════════════════════════════════════════╗");
    console.log("║  LOG IN TO LINKEDIN IN THE BROWSER       ║");
    console.log("║  (or set LINKEDIN_EMAIL/PASSWORD in .env) ║");
    console.log("╚══════════════════════════════════════════╝\n");
    await page.waitForURL("**/feed/**", { timeout: 300000 });
  }

  console.log("→ Saving session...");
  const cookies = await context.cookies();
  fs.mkdirSync(SESSION_DIR, { recursive: true });
  fs.writeFileSync(
    path.join(SESSION_DIR, "cookies.json"),
    JSON.stringify(cookies, null, 2)
  );

  await context.close();
  console.log("✓ Session saved to .session/cookies.json\n");
}

// ── Post extraction ─────────────────────────────────────────────────────────

async function extractPosts(page, handle, maxPosts, outputDir) {
  const activityUrl = `https://www.linkedin.com/in/${handle}/recent-activity/all/`;
  console.log(`→ Navigating to ${activityUrl}`);
  await page.goto(activityUrl, { waitUntil: "domcontentloaded" });
  await sleep(3000, 5000);

  // Check if we're on the right page
  const pageTitle = await page.title();
  console.log(`  Page title: ${pageTitle}`);

  // Check for auth wall
  const authWall = await page.$('a[href*="login"], a[href*="signup"]');
  if (authWall && !pageTitle.includes("LinkedIn")) {
    console.error("✗ Not authenticated. Run with --login first.");
    return [];
  }

  const posts = [];
  const seenTexts = new Set(); // deduplicate by text content
  let scrollAttempts = 0;
  const maxScrollAttempts = maxPosts * 3; // generous scroll budget
  let lastPostCount = 0;
  let noNewPostStreak = 0;

  console.log(`→ Scrolling to load posts (target: ${maxPosts})...\n`);

  while (posts.length < maxPosts && scrollAttempts < maxScrollAttempts) {
    // Extract visible post containers
    const postElements = await page.$$('[data-urn*="activity"], .feed-shared-update-v2, div.occludable-update');

    for (const postEl of postElements) {
      if (posts.length >= maxPosts) break;

      try {
        // Get unique identifier
        const urn =
          (await postEl.getAttribute("data-urn")) ||
          (await postEl.getAttribute("data-id")) ||
          `post-${posts.length}`;

        if (posts.find((p) => p.urn === urn)) continue;

        // Extract post data
        const postData = await postEl.evaluate((el) => {
          const getText = (sel) => {
            const node = el.querySelector(sel);
            return node ? node.innerText.trim() : "";
          };

          const getAttr = (sel, attr) => {
            const node = el.querySelector(sel);
            return node ? node.getAttribute(attr) : "";
          };

          // Post text — try multiple selectors
          let text =
            getText(".feed-shared-update-v2__description") ||
            getText(".feed-shared-text") ||
            getText('[data-ad-preview="message"]') ||
            getText(".update-components-text") ||
            getText("span.break-words") ||
            "";

          // Timestamp — try datetime attribute first, fallback to relative
          let timestamp = "";
          let dateAbsolute = "";
          const timeEl = el.querySelector("time[datetime], [datetime]");
          if (timeEl) {
            const dt = timeEl.getAttribute("datetime");
            if (dt) {
              timestamp = dt;
              dateAbsolute = dt;
            } else {
              timestamp = timeEl.innerText.trim();
            }
          }
          if (!timestamp) {
            timestamp =
              getText(".feed-shared-actor__sub-description") ||
              getText(".update-components-actor__sub-description") ||
              "";
            timestamp = timestamp.split("•")[0].trim();
          }
          // Convert relative timestamps to approximate absolute dates
          if (!dateAbsolute && timestamp) {
            const now = new Date();
            const rel = timestamp.toLowerCase();
            let daysAgo = 0;
            const hourMatch = rel.match(/(\d+)\s*h/);
            const dayMatch = rel.match(/(\d+)\s*d/);
            const weekMatch = rel.match(/(\d+)\s*w/);
            const monthMatch = rel.match(/(\d+)\s*mo/);
            const yearMatch = rel.match(/(\d+)\s*y/);
            if (hourMatch) daysAgo = 0;
            else if (dayMatch) daysAgo = parseInt(dayMatch[1]);
            else if (weekMatch) daysAgo = parseInt(weekMatch[1]) * 7;
            else if (monthMatch) daysAgo = parseInt(monthMatch[1]) * 30;
            else if (yearMatch) daysAgo = parseInt(yearMatch[1]) * 365;
            if (daysAgo >= 0) {
              const d = new Date(now.getTime() - daysAgo * 86400000);
              dateAbsolute = d.toISOString().split("T")[0];
            }
          }

          // Reactions / likes
          let reactions =
            getText(".social-details-social-counts__reactions-count") ||
            getText('[data-test-id="social-actions__reaction-count"]') ||
            getText(".reactions-count") ||
            "0";

          // Comments count
          let comments = "";
          const commentBtns = el.querySelectorAll(
            'button[aria-label*="comment"], span.social-details-social-counts__comments'
          );
          for (const btn of commentBtns) {
            const t = btn.innerText || btn.getAttribute("aria-label") || "";
            const match = t.match(/(\d[\d,]*)\s*comment/i);
            if (match) {
              comments = match[1];
              break;
            }
          }

          // Reposts
          let reposts = "";
          const repostBtns = el.querySelectorAll(
            'button[aria-label*="repost"], span.social-details-social-counts__reposts'
          );
          for (const btn of repostBtns) {
            const t = btn.innerText || btn.getAttribute("aria-label") || "";
            const match = t.match(/(\d[\d,]*)\s*repost/i);
            if (match) {
              reposts = match[1];
              break;
            }
          }

          // Post type detection — order matters: check specific first, generic last
          let postType = "text";
          if (el.querySelector(".feed-shared-poll"))
            postType = "poll";
          else if (el.querySelector(".feed-shared-document, .document-s-container, .feed-shared-carousel, .carousel-container"))
            postType = "carousel/document";
          else if (el.querySelector(".feed-shared-linkedin-video") && el.querySelector("video[src], video source[src]"))
            postType = "video";
          else if (el.querySelector(".feed-shared-article, .update-components-article, .feed-shared-external-link"))
            postType = "article/link";
          else if (el.querySelector(".feed-shared-image, .update-components-image, img.feed-shared-image__image"))
            postType = "image+text";
          else if (el.querySelector("video"))
            postType = "video"; // actual video element with content

          // Images
          const images = [];
          const imgEls = el.querySelectorAll(
            ".feed-shared-image img, .update-components-image img, img.feed-shared-image__image"
          );
          for (const img of imgEls) {
            const src = img.getAttribute("src") || "";
            if (src && !src.includes("profile-displayphoto"))
              images.push(src);
          }

          // Hashtags — extract from both links and text content
          const hashtags = [];
          const hashtagEls = el.querySelectorAll('a[href*="hashtag"], a[href*="feed/hashtag"]');
          for (const h of hashtagEls) {
            const tag = h.innerText.trim().replace(/^#/, '');
            if (tag && !hashtags.includes(tag)) hashtags.push(tag);
          }
          // Also extract from post text using regex
          if (text) {
            const textHashtags = text.match(/#(\w+)/g) || [];
            for (const tag of textHashtags) {
              const clean = tag.replace(/^#/, '');
              if (clean && !hashtags.includes(clean)) hashtags.push(clean);
            }
          }

          return {
            text,
            timestamp,
            dateAbsolute,
            reactions,
            comments,
            reposts,
            postType,
            images,
            hashtags,
          };
        });

        if (!postData.text && !postData.images.length) continue; // skip empty

        postData.text = sanitize(postData.text);

        // Deduplicate by text content (first 150 chars)
        const textKey = postData.text.slice(0, 150);
        if (seenTexts.has(textKey)) continue;
        seenTexts.add(textKey);

        postData.urn = urn;
        postData.index = posts.length + 1;

        // Take screenshot of the post
        const screenshotName = `${String(posts.length + 1).padStart(3, "0")}-${slugify(postData.text.slice(0, 40) || "post")}.png`;
        const screenshotPath = path.join(outputDir, "screenshots", screenshotName);
        try {
          await postEl.screenshot({ path: screenshotPath });
          postData.screenshot = `screenshots/${screenshotName}`;
        } catch {
          postData.screenshot = null;
        }

        posts.push(postData);

        const rxn = postData.reactions || "0";
        const cmt = postData.comments || "0";
        const rp = postData.reposts || "0";
        console.log(
          `  [${posts.length}/${maxPosts}] ${postData.postType.padEnd(10)} | ${rxn} reactions, ${cmt} comments, ${rp} reposts | ${postData.text.slice(0, 60)}...`
        );

        await sleep(POST_EXTRACT_DELAY_MIN, POST_EXTRACT_DELAY_MAX);
      } catch (err) {
        // Skip problematic posts
        continue;
      }
    }

    // Check if we got new posts
    if (posts.length === lastPostCount) {
      noNewPostStreak++;
      if (noNewPostStreak >= 5) {
        console.log("\n→ No new posts loading after 5 scroll attempts. Stopping.");
        break;
      }
    } else {
      noNewPostStreak = 0;
      lastPostCount = posts.length;
    }

    // Scroll down
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 1.5));
    await sleep(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX);
    scrollAttempts++;

    // Click "Show more" or "See more" buttons if present
    try {
      const showMore = await page.$('button:has-text("Show more"), button:has-text("See more results")');
      if (showMore) {
        await showMore.click();
        await sleep(2000, 3000);
      }
    } catch {}
  }

  return posts;
}

// ── Content categorization ──────────────────────────────────────────────────

function categorizePost(text, postType) {
  const lower = text.toLowerCase();

  if (/cheat\s*sheet|cheatsheet|quick\s*reference|download/i.test(lower))
    return "Cheat Sheet / Resource List";
  if (/step[\s-]*by[\s-]*step|tutorial|how\s+to|walkthrough|let['']s\s+build/i.test(lower))
    return "Technical Tutorial";
  if (/architecture|system\s+design|pipeline|infrastructure|diagram/i.test(lower))
    return "System Design / Architecture";
  if (/\bvs\b|compared?|better|which\s+one|alternative/i.test(lower))
    return "Tool Review / Comparison";
  if (/career|salary|interview|hiring|resume|job\s+(search|market|hunt)|offer/i.test(lower))
    return "Career Advice";
  if (/announce|launch|release|just\s+shipped|new\s+feature|breaking/i.test(lower))
    return "Industry Commentary";
  if (/i\s+(learned|failed|struggled|built|quit|started)|my\s+journey|honest|truth/i.test(lower))
    return "Personal Story / Journey";
  if (/framework|principle|rule|mental\s+model|unpopular\s+opinion|hot\s+take/i.test(lower))
    return "Thought Leadership";
  if (/sponsor|partner|ad\s*:|#ad|promoted|discount|code\s*:/i.test(lower))
    return "Sponsored / Partnership";
  if (/diversity|inclusion|equity|representation|women\s+in|minority/i.test(lower))
    return "Diversity / Inclusion";
  if (postType === "poll") return "Entertainment / Memes";

  return "General / Uncategorized";
}

// ── Output generation ───────────────────────────────────────────────────────

function generateReport(handle, posts, outputDir) {
  // Categorize all posts
  for (const post of posts) {
    post.category = categorizePost(post.text, post.postType);
  }

  // Category distribution
  const catCounts = {};
  for (const post of posts) {
    catCounts[post.category] = (catCounts[post.category] || 0) + 1;
  }
  const catDist = Object.entries(catCounts)
    .map(([cat, count]) => ({
      category: cat,
      count,
      pct: ((count / posts.length) * 100).toFixed(1),
    }))
    .sort((a, b) => b.count - a.count);

  // Format distribution
  const fmtCounts = {};
  for (const post of posts) {
    fmtCounts[post.postType] = (fmtCounts[post.postType] || 0) + 1;
  }
  const fmtDist = Object.entries(fmtCounts)
    .map(([fmt, count]) => ({
      format: fmt,
      count,
      pct: ((count / posts.length) * 100).toFixed(1),
    }))
    .sort((a, b) => b.count - a.count);

  // Hashtag frequency
  const hashCounts = {};
  for (const post of posts) {
    for (const h of post.hashtags) {
      const tag = h.startsWith("#") ? h : `#${h}`;
      hashCounts[tag] = (hashCounts[tag] || 0) + 1;
    }
  }
  const topHashtags = Object.entries(hashCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  // Top posts by engagement (parse reactions/comments to numbers)
  const parseNum = (s) => parseInt(String(s).replace(/,/g, "") || "0", 10);
  const sortedByEngagement = [...posts]
    .map((p) => ({
      ...p,
      totalEngagement:
        parseNum(p.reactions) + parseNum(p.comments) + parseNum(p.reposts),
    }))
    .sort((a, b) => b.totalEngagement - a.totalEngagement);

  // Average post length
  const avgLength =
    posts.reduce((sum, p) => sum + p.text.split(/\s+/).length, 0) /
    (posts.length || 1);

  // ── Write raw JSON ──
  fs.writeFileSync(
    path.join(outputDir, "posts-raw.json"),
    JSON.stringify(posts, null, 2)
  );

  // ── Write markdown report ──
  let md = `# LinkedIn Scrape Report: @${handle}\n\n`;
  md += `**Scraped:** ${new Date().toISOString().split("T")[0]}\n`;
  md += `**Posts collected:** ${posts.length}\n`;
  md += `**Avg post length:** ${Math.round(avgLength)} words\n\n`;

  md += `## Content Type Distribution\n\n`;
  md += `| Category | Count | % |\n|----------|-------|---|\n`;
  for (const c of catDist) {
    md += `| ${c.category} | ${c.count} | ${c.pct}% |\n`;
  }

  md += `\n## Format Distribution\n\n`;
  md += `| Format | Count | % |\n|--------|-------|---|\n`;
  for (const f of fmtDist) {
    md += `| ${f.format} | ${f.count} | ${f.pct}% |\n`;
  }

  md += `\n## Top Hashtags\n\n`;
  md += `| Hashtag | Count |\n|---------|-------|\n`;
  for (const [tag, count] of topHashtags) {
    md += `| ${tag} | ${count} |\n`;
  }

  md += `\n## Top 10 Posts by Engagement\n\n`;
  md += `| # | Type | Category | Reactions | Comments | Reposts | Text Preview |\n`;
  md += `|---|------|----------|-----------|----------|---------|-------------|\n`;
  for (let i = 0; i < Math.min(10, sortedByEngagement.length); i++) {
    const p = sortedByEngagement[i];
    const preview = p.text.slice(0, 80).replace(/\|/g, "\\|").replace(/\n/g, " ");
    md += `| ${i + 1} | ${p.postType} | ${p.category} | ${p.reactions} | ${p.comments || "0"} | ${p.reposts || "0"} | ${preview}... |\n`;
  }

  md += `\n## All Posts (Chronological)\n\n`;
  for (const p of posts) {
    md += `### Post ${p.index} — ${p.postType} (${p.category})\n\n`;
    md += `- **Timestamp:** ${p.timestamp || "unknown"}\n`;
    md += `- **Reactions:** ${p.reactions || "0"} | **Comments:** ${p.comments || "0"} | **Reposts:** ${p.reposts || "0"}\n`;
    if (p.hashtags.length) md += `- **Hashtags:** ${p.hashtags.join(", ")}\n`;
    if (p.screenshot) md += `- **Screenshot:** [${p.screenshot}](${p.screenshot})\n`;
    md += `\n> ${p.text.slice(0, 500).replace(/\n/g, "\n> ")}\n\n`;
    md += `---\n\n`;
  }

  const reportPath = path.join(outputDir, "scrape-report.md");
  fs.writeFileSync(reportPath, md);

  console.log(`\n✓ Report saved: ${reportPath}`);
  console.log(`✓ Raw data: ${path.join(outputDir, "posts-raw.json")}`);
  console.log(`✓ Screenshots: ${path.join(outputDir, "screenshots/")}`);

  // Print summary
  console.log(`\n── Summary ──────────────────────────────────`);
  console.log(`Posts: ${posts.length}`);
  console.log(`Avg length: ${Math.round(avgLength)} words`);
  console.log(`\nContent types:`);
  for (const c of catDist) {
    console.log(`  ${c.pct}% ${c.category} (${c.count})`);
  }
  console.log(`\nFormats:`);
  for (const f of fmtDist) {
    console.log(`  ${f.pct}% ${f.format} (${f.count})`);
  }
  console.log(`\nTop 3 posts:`);
  for (let i = 0; i < Math.min(3, sortedByEngagement.length); i++) {
    const p = sortedByEngagement[i];
    console.log(
      `  ${i + 1}. [${p.reactions} reactions] ${p.text.slice(0, 60)}...`
    );
  }
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  const config = parseArgs();
  const { handle, maxPosts, login, headless } = config;

  // Prepare output directory — map handles to person folder names
  const HANDLE_TO_FOLDER = {
    "alexwang2911": "Alex Wang",
    "chiphuyen": "Chip Huyen",
    "andrej-karpathy-9a650716": "Andrej Karpathy",
    "alliekmiller": "Allie K Miller",
    "kozyrkov": "Cassie Kozyrkov",
    "andrewyng": "Andrew Ng",
    "svpino": "Santiago Valdarrama",
    "dalianaliu": "Daliana Liu",
    "sundaskhalid": "Sundas Khalid",
    "armand-ruiz": "Armand Ruiz",
    "shawnswyxwang": "Shawn Wang",
    "johnfreddyvega": "Freddy Vega",
    "ruben-hassid": "Ruben Hassid",
    "matiii": "Mati Staniszewski",
    "harrison-chase-961287118": "Harrison Chase",
    "ninadurann": "Nina Fernanda Duran",
    "carlossantanavega": "Carlos Santana Vega",
    "tiangolo": "Sebastian Ramirez",
    "emollick": "Ethan Mollick",
  };

  const folderName = HANDLE_TO_FOLDER[handle] || handle;
  const outputDir = path.join(BASE_DIR, folderName);

  fs.mkdirSync(path.join(outputDir, "screenshots"), { recursive: true });

  console.log(`\n╔══════════════════════════════════════════╗`);
  console.log(`║  LinkedIn Scraper — @${handle.padEnd(20)}║`);
  console.log(`║  Target: ${maxPosts} posts`.padEnd(43) + `║`);
  console.log(`║  Output: ${outputDir.split("/").pop().padEnd(32)}║`);
  console.log(`╚══════════════════════════════════════════╝\n`);

  // Launch browser
  const browser = await chromium.launch({
    headless: login ? false : headless,
    slowMo: 50,
  });

  try {
    // Login flow
    if (login) {
      await loginFlow(browser);
    }

    // Check for saved session
    const cookiePath = path.join(SESSION_DIR, "cookies.json");
    if (!fs.existsSync(cookiePath)) {
      console.error("✗ No session found. Run with --login first.");
      process.exit(1);
    }

    // Create context with saved cookies
    const cookies = JSON.parse(fs.readFileSync(cookiePath, "utf-8"));
    const context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      userAgent:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    });
    await context.addCookies(cookies);

    const page = await context.newPage();

    // Scrape posts
    const posts = await extractPosts(page, handle, maxPosts, outputDir);

    if (posts.length === 0) {
      console.error("\n✗ No posts extracted. Possible issues:");
      console.error("  - Session expired (re-run with --login)");
      console.error("  - Profile has no public activity");
      console.error("  - LinkedIn DOM changed (update selectors)");
      process.exit(1);
    }

    // Generate report
    generateReport(handle, posts, outputDir);

    await context.close();
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
