#!/bin/bash
# Scrape all reference people's LinkedIn posts
# Usage: ./scrape-all.sh [--max-posts 30]
#
# First run: node linkedin-scraper.js --login
# Then: ./scrape-all.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_POSTS="${1:-30}"

# All handles to scrape
HANDLES=(
  "alexwang2911"
  "chiphuyen"
  "andrej-karpathy-9a650716"
  "alliekmiller"
  "kozyrkov"
  "andrewyng"
  "svpino"
  "dalianaliu"
  "sundaskhalid"
  "armand-ruiz"
  "shawnswyxwang"
)

NAMES=(
  "Alex Wang"
  "Chip Huyen"
  "Andrej Karpathy"
  "Allie K Miller"
  "Cassie Kozyrkov"
  "Andrew Ng"
  "Santiago Valdarrama"
  "Daliana Liu"
  "Sundas Khalid"
  "Armand Ruiz"
  "Shawn Wang"
)

echo "═══════════════════════════════════════"
echo "  LinkedIn Batch Scraper"
echo "  Profiles: ${#HANDLES[@]}"
echo "  Max posts per profile: $MAX_POSTS"
echo "═══════════════════════════════════════"
echo ""

for i in "${!HANDLES[@]}"; do
  handle="${HANDLES[$i]}"
  name="${NAMES[$i]}"

  echo "──────────────────────────────────────"
  echo "[$((i+1))/${#HANDLES[@]}] Scraping: $name (@$handle)"
  echo "──────────────────────────────────────"

  node "$SCRIPT_DIR/linkedin-scraper.js" --handle "$handle" --max-posts "$MAX_POSTS" --headless

  # Random delay between profiles (60-120 seconds) to avoid detection
  if [ $i -lt $((${#HANDLES[@]} - 1)) ]; then
    delay=$((RANDOM % 60 + 60))
    echo ""
    echo "⏳ Waiting ${delay}s before next profile..."
    sleep $delay
  fi
done

echo ""
echo "═══════════════════════════════════════"
echo "  Done! All ${#HANDLES[@]} profiles scraped."
echo "═══════════════════════════════════════"
