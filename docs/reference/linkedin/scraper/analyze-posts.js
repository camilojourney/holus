#!/usr/bin/env node
/**
 * Post Anatomy Analyzer — quantitative analysis across all scraped profiles
 *
 * Reads every posts-raw.json, aggregates engagement, formats, hooks,
 * length distributions, hashtag frequency, and outputs a structured report.
 */

const fs = require("fs");
const path = require("path");

const BASE = path.resolve(__dirname, "..");

// ── Collect all posts from all profiles ─────────────────────────────────────

function loadAllPosts() {
  const profiles = fs.readdirSync(BASE).filter((d) => {
    const raw = path.join(BASE, d, "posts-raw.json");
    return fs.existsSync(raw) && fs.statSync(path.join(BASE, d)).isDirectory();
  });

  const allPosts = [];
  for (const profile of profiles) {
    const posts = JSON.parse(
      fs.readFileSync(path.join(BASE, profile, "posts-raw.json"), "utf-8")
    );
    for (const p of posts) {
      allPosts.push({ ...p, profile });
    }
  }
  return allPosts;
}

// ── Parse engagement numbers ────────────────────────────────────────────────

function parseNum(s) {
  if (!s) return 0;
  return parseInt(String(s).replace(/,/g, ""), 10) || 0;
}

function totalEngagement(p) {
  return parseNum(p.reactions) + parseNum(p.comments) + parseNum(p.reposts);
}

// ── Hook analysis ───────────────────────────────────────────────────────────

function classifyHook(text) {
  if (!text) return "none";
  const firstLine = text.split("\n")[0].trim();

  if (firstLine.endsWith("?")) return "question";
  if (/^\d+[\.\)]/.test(firstLine)) return "numbered-list";
  if (/^(I |My |We |Our )/.test(firstLine)) return "personal-story";
  if (/^(Stop|Don't|Never|Forget|Quit|Warning)/i.test(firstLine))
    return "contrarian/negative";
  if (/^(The |Most |Every |All |No one)/i.test(firstLine))
    return "bold-statement";
  if (/^(How|Why|What|Where|When|Who)/i.test(firstLine))
    return "how-to/explainer";
  if (/^(🔴|🔥|⭕|🚨|📣|✨|💡|⚡)/.test(firstLine)) return "emoji-hook";
  if (/^(Breaking|Just|NEW|JUST|Today|Announcing)/i.test(firstLine))
    return "news/announcement";
  if (
    /^(If you|If your|Are you|Do you|Have you)/i.test(firstLine)
  )
    return "direct-address";
  if (firstLine.length < 50) return "short-punchy";
  return "descriptive-lead";
}

// ── Formatting analysis ─────────────────────────────────────────────────────

function analyzeFormatting(text) {
  if (!text) return {};

  const lines = text.split("\n");
  const nonEmpty = lines.filter((l) => l.trim().length > 0);

  return {
    totalLines: lines.length,
    contentLines: nonEmpty.length,
    blankLineRatio: (lines.length - nonEmpty.length) / Math.max(lines.length, 1),
    avgLineLength:
      nonEmpty.reduce((s, l) => s + l.length, 0) / Math.max(nonEmpty.length, 1),
    wordCount: text.split(/\s+/).length,
    charCount: text.length,
    hasEmoji: /[\u{1F600}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}]/u.test(text),
    emojiCount: (text.match(/[\u{1F600}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}]/gu) || []).length,
    hasNumberedList: /^\s*\d+[\.\)]/m.test(text),
    hasBullets: /^\s*[•\-\*→▸▶]/m.test(text),
    hasHashtags: /#\w+/.test(text),
    hashtagCount: (text.match(/#\w+/g) || []).length,
    hasLink: /https?:\/\/\S+|lnkd\.in/.test(text),
    hasMention: /@\w+/.test(text),
    hasUnicodeBold: /[\u{1D400}-\u{1D7FF}]/u.test(text),
    usesAllCaps: /\b[A-Z]{4,}\b/.test(text),
    lineBreakDensity: lines.length / Math.max(text.split(/\s+/).length, 1),
    endsWithQuestion: text.trim().endsWith("?"),
    endsWithCTA:
      /follow|comment|share|like|subscribe|check|grab|join|sign up|dm|link/i.test(
        text.split("\n").pop() || ""
      ),
  };
}

// ── Language detection (basic) ──────────────────────────────────────────────

function detectLanguage(text) {
  if (!text) return "unknown";
  const spanishWords =
    /\b(el|la|los|las|de|del|en|por|para|con|que|es|son|una|este|esta|como|más|pero|también|nuevo|nuevo|aquí|puede|tienen|sobre|ahora|bien|cada|donde|hace|hay|hoy|muy|otro|sin|solo|todos|vamos|ver|ya|año|así|ser)\b/gi;
  const englishWords =
    /\b(the|is|are|was|were|been|have|has|had|will|would|could|should|can|this|that|these|those|from|with|about|into|through|during|before|after|above|below|between|same|each|every|both|few|more|most|other|some|such|than|too|very|just|also|now|here|there|then|when|where|how|what|which|who|why|all|any|each|every|few|more|most|no|not|only|own|same)\b/gi;

  const spCount = (text.match(spanishWords) || []).length;
  const enCount = (text.match(englishWords) || []).length;

  if (spCount > enCount * 1.5) return "spanish";
  if (enCount > spCount * 1.5) return "english";
  if (spCount > 0 && enCount > 0) return "mixed";
  return "english"; // default
}

// ── Main analysis ───────────────────────────────────────────────────────────

function analyze() {
  const posts = loadAllPosts();
  console.log(`\nLoaded ${posts.length} posts from ${new Set(posts.map((p) => p.profile)).size} profiles\n`);

  // Enrich each post
  for (const p of posts) {
    p.eng = totalEngagement(p);
    p.hookType = classifyHook(p.text);
    p.fmt = analyzeFormatting(p.text);
    p.lang = detectLanguage(p.text);
    p.reactionsNum = parseNum(p.reactions);
    p.commentsNum = parseNum(p.comments);
    p.repostsNum = parseNum(p.reposts);
  }

  // ── 1. FORMAT BREAKDOWN ─────────────────────────────────────────────────
  console.log("═══════════════════════════════════════════════════════");
  console.log("1. FORMAT BREAKDOWN");
  console.log("═══════════════════════════════════════════════════════");

  const byFormat = {};
  for (const p of posts) {
    const fmt = p.postType || "unknown";
    if (!byFormat[fmt]) byFormat[fmt] = { count: 0, totalEng: 0, posts: [] };
    byFormat[fmt].count++;
    byFormat[fmt].totalEng += p.eng;
    byFormat[fmt].posts.push(p);
  }

  const formatRows = Object.entries(byFormat)
    .map(([fmt, d]) => ({
      format: fmt,
      count: d.count,
      pct: ((d.count / posts.length) * 100).toFixed(1),
      avgEng: Math.round(d.totalEng / d.count),
      medianEng: median(d.posts.map((p) => p.eng)),
    }))
    .sort((a, b) => b.avgEng - a.avgEng);

  console.table(formatRows);

  // ── 2. HOOK TYPE ANALYSIS ───────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("2. HOOK TYPE vs ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const byHook = {};
  for (const p of posts) {
    if (!byHook[p.hookType]) byHook[p.hookType] = { count: 0, totalEng: 0, posts: [] };
    byHook[p.hookType].count++;
    byHook[p.hookType].totalEng += p.eng;
    byHook[p.hookType].posts.push(p);
  }

  const hookRows = Object.entries(byHook)
    .map(([hook, d]) => ({
      hook,
      count: d.count,
      avgEng: Math.round(d.totalEng / d.count),
      medianEng: median(d.posts.map((p) => p.eng)),
      topPost: d.posts.sort((a, b) => b.eng - a.eng)[0]?.text?.slice(0, 60),
    }))
    .sort((a, b) => b.avgEng - a.avgEng);

  console.table(hookRows);

  // ── 3. TOP 50 POSTS ────────────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("3. TOP 50 POSTS BY TOTAL ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const top50 = [...posts].sort((a, b) => b.eng - a.eng).slice(0, 50);
  for (let i = 0; i < top50.length; i++) {
    const p = top50[i];
    console.log(
      `\n#${i + 1} | ${p.profile} | ${p.postType} | ${p.eng.toLocaleString()} eng (${p.reactionsNum} ❤️ ${p.commentsNum} 💬 ${p.repostsNum} 🔄)`
    );
    console.log(`   Hook: [${p.hookType}] ${(p.text || "").slice(0, 100)}`);
    console.log(
      `   Words: ${p.fmt.wordCount} | Lines: ${p.fmt.totalLines} | Emoji: ${p.fmt.emojiCount} | Links: ${p.fmt.hasLink ? "Y" : "N"} | Lang: ${p.lang}`
    );
  }

  // ── 4. FORMATTING vs ENGAGEMENT CORRELATION ────────────────────────────
  console.log("\n\n═══════════════════════════════════════════════════════");
  console.log("4. FORMATTING PATTERNS vs ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const withEmoji = posts.filter((p) => p.fmt.hasEmoji);
  const withoutEmoji = posts.filter((p) => !p.fmt.hasEmoji);
  const withList = posts.filter((p) => p.fmt.hasNumberedList || p.fmt.hasBullets);
  const withoutList = posts.filter((p) => !p.fmt.hasNumberedList && !p.fmt.hasBullets);
  const withLink = posts.filter((p) => p.fmt.hasLink);
  const withoutLink = posts.filter((p) => !p.fmt.hasLink);
  const withBold = posts.filter((p) => p.fmt.hasUnicodeBold);
  const withoutBold = posts.filter((p) => !p.fmt.hasUnicodeBold);
  const withCTA = posts.filter((p) => p.fmt.endsWithCTA);
  const withoutCTA = posts.filter((p) => !p.fmt.endsWithCTA);
  const withCaps = posts.filter((p) => p.fmt.usesAllCaps);
  const withoutCaps = posts.filter((p) => !p.fmt.usesAllCaps);

  const fmtComparison = [
    { feature: "Emoji", with: avgEng(withEmoji), without: avgEng(withoutEmoji), withN: withEmoji.length, withoutN: withoutEmoji.length },
    { feature: "Numbered/Bullet list", with: avgEng(withList), without: avgEng(withoutList), withN: withList.length, withoutN: withoutList.length },
    { feature: "External link", with: avgEng(withLink), without: avgEng(withoutLink), withN: withLink.length, withoutN: withoutLink.length },
    { feature: "Unicode bold", with: avgEng(withBold), without: avgEng(withoutBold), withN: withBold.length, withoutN: withoutBold.length },
    { feature: "Ends with CTA", with: avgEng(withCTA), without: avgEng(withoutCTA), withN: withCTA.length, withoutN: withoutCTA.length },
    { feature: "ALL CAPS words", with: avgEng(withCaps), without: avgEng(withoutCaps), withN: withCaps.length, withoutN: withoutCaps.length },
  ];

  console.table(fmtComparison);

  // ── 5. WORD COUNT BUCKETS ──────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("5. WORD COUNT vs ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const wordBuckets = [
    { label: "0-30 (micro)", min: 0, max: 30 },
    { label: "31-75 (short)", min: 31, max: 75 },
    { label: "76-150 (medium)", min: 76, max: 150 },
    { label: "151-300 (long)", min: 151, max: 300 },
    { label: "300+ (essay)", min: 301, max: Infinity },
  ];

  const wordRows = wordBuckets.map((b) => {
    const bucket = posts.filter(
      (p) => p.fmt.wordCount >= b.min && p.fmt.wordCount <= b.max
    );
    return {
      range: b.label,
      count: bucket.length,
      avgEng: avgEng(bucket),
      medianEng: median(bucket.map((p) => p.eng)),
    };
  });

  console.table(wordRows);

  // ── 6. LANGUAGE BREAKDOWN ──────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("6. LANGUAGE vs ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const byLang = {};
  for (const p of posts) {
    if (!byLang[p.lang]) byLang[p.lang] = { count: 0, totalEng: 0, posts: [] };
    byLang[p.lang].count++;
    byLang[p.lang].totalEng += p.eng;
    byLang[p.lang].posts.push(p);
  }

  const langRows = Object.entries(byLang)
    .map(([lang, d]) => ({
      language: lang,
      count: d.count,
      avgEng: Math.round(d.totalEng / d.count),
      medianEng: median(d.posts.map((p) => p.eng)),
    }))
    .sort((a, b) => b.avgEng - a.avgEng);

  console.table(langRows);

  // ── 7. LINE BREAK / SPACING PATTERNS ──────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("7. SPACING DENSITY vs ENGAGEMENT");
  console.log("═══════════════════════════════════════════════════════");

  const spacingBuckets = [
    { label: "Dense (0-10%)", min: 0, max: 0.1 },
    { label: "Normal (10-30%)", min: 0.1, max: 0.3 },
    { label: "Airy (30-50%)", min: 0.3, max: 0.5 },
    { label: "Very airy (50%+)", min: 0.5, max: 1.0 },
  ];

  const spacingRows = spacingBuckets.map((b) => {
    const bucket = posts.filter(
      (p) => p.fmt.blankLineRatio >= b.min && p.fmt.blankLineRatio < b.max
    );
    return {
      spacing: b.label,
      count: bucket.length,
      avgEng: avgEng(bucket),
      medianEng: median(bucket.map((p) => p.eng)),
    };
  });

  console.table(spacingRows);

  // ── 8. PER-PROFILE STATS ──────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════════════════");
  console.log("8. PER-PROFILE PERFORMANCE");
  console.log("═══════════════════════════════════════════════════════");

  const byProfile = {};
  for (const p of posts) {
    if (!byProfile[p.profile])
      byProfile[p.profile] = { count: 0, totalEng: 0, posts: [] };
    byProfile[p.profile].count++;
    byProfile[p.profile].totalEng += p.eng;
    byProfile[p.profile].posts.push(p);
  }

  const profileRows = Object.entries(byProfile)
    .map(([name, d]) => {
      const sorted = d.posts.sort((a, b) => b.eng - a.eng);
      const formats = {};
      for (const p of d.posts) formats[p.postType] = (formats[p.postType] || 0) + 1;
      const topFormat = Object.entries(formats).sort((a, b) => b[1] - a[1])[0];
      return {
        profile: name,
        posts: d.count,
        avgEng: Math.round(d.totalEng / d.count),
        medianEng: median(d.posts.map((p) => p.eng)),
        topPost: sorted[0]?.eng?.toLocaleString(),
        primaryFormat: topFormat ? `${topFormat[0]} (${topFormat[1]})` : "?",
        primaryLang: d.posts.filter((p) => p.lang === "spanish").length > d.count / 2 ? "ES" : "EN",
      };
    })
    .sort((a, b) => b.avgEng - a.avgEng);

  console.table(profileRows);

  // ── Save enriched data ────────────────────────────────────────────────
  const report = {
    meta: {
      totalPosts: posts.length,
      totalProfiles: Object.keys(byProfile).length,
      analyzedAt: new Date().toISOString(),
    },
    formatBreakdown: formatRows,
    hookAnalysis: hookRows,
    formattingVsEngagement: fmtComparison,
    wordCountBuckets: wordRows,
    languageBreakdown: langRows,
    spacingDensity: spacingRows,
    profilePerformance: profileRows,
    top50: top50.map((p) => ({
      rank: top50.indexOf(p) + 1,
      profile: p.profile,
      format: p.postType,
      hook: p.hookType,
      lang: p.lang,
      engagement: p.eng,
      reactions: p.reactionsNum,
      comments: p.commentsNum,
      reposts: p.repostsNum,
      wordCount: p.fmt.wordCount,
      hasEmoji: p.fmt.hasEmoji,
      hasLink: p.fmt.hasLink,
      hasList: p.fmt.hasNumberedList || p.fmt.hasBullets,
      spacing: p.fmt.blankLineRatio.toFixed(2),
      text: (p.text || "").slice(0, 200),
    })),
  };

  fs.writeFileSync(
    path.join(BASE, "content-analysis.json"),
    JSON.stringify(report, null, 2)
  );
  console.log("\n✓ Full analysis saved to content-analysis.json");
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function avgEng(posts) {
  if (!posts.length) return 0;
  return Math.round(posts.reduce((s, p) => s + p.eng, 0) / posts.length);
}

function median(arr) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

analyze();
