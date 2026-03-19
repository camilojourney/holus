# LinkedIn Reference People — Content Intelligence

Profiles of people succeeding in AI/ML/Data Science on LinkedIn. Each folder contains a deep profile analyzing career path, audience metrics, content strategy, and lessons for Juan.

## How to Use

1. Study individual profiles to understand what works
2. Read [patterns.md](patterns.md) for synthesized learnings + actionable playbook
3. Read [linkedin_blueprint.md](linkedin_blueprint.md) for the standardized research template
4. Add new people: create a folder with `profile.md` following the blueprint
5. Stats: use [Favikon](https://www.favikon.com) for LinkedIn creator analytics
6. Scrape posts: use `scraper/linkedin-scraper.js` (see scraper README)

## Profiles (19 total)

### Original Research (English AI/ML creators)

| Person | Followers | Niche | Language | Relevance |
|--------|-----------|-------|----------|-----------|
| [Alex Wang](Alex%20Wang/profile.md) | 1M | AI/DS education | EN | Content strategy model |
| [Chip Huyen](Chip%20Huyen/profile.md) | 200K | Production ML, MLOps | EN | Authority model |
| [Andrej Karpathy](Andrej%20Karpathy/profile.md) | 300-500K | Neural nets, LLMs | EN | Technical content model |
| [Allie K Miller](Allie%20K%20Miller/profile.md) | 2M | AI business strategy | EN | Business+tech hybrid |
| [Cassie Kozyrkov](Cassie%20Kozyrkov/profile.md) | 500K | Decision intelligence | EN | Naming/framing model |
| [Andrew Ng](Andrew%20Ng/profile.md) | 1.8M | AI education | EN | Aspirational |
| [Santiago Valdarrama](Santiago%20Valdarrama/profile.md) | 80K LI | Production ML | EN | **Most similar to Juan** |
| [Daliana Liu](Daliana%20Liu/profile.md) | 300K | Career + tech honesty | EN | Career content model |
| [Sundas Khalid](Sundas%20Khalid/profile.md) | 1M cross | Data science careers | EN | Diversity narrative |
| [Armand Ruiz](Armand%20Ruiz/profile.md) | 200K | AI architecture | EN | Visual content model |
| [Shawn Wang (swyx)](Shawn%20Wang/profile.md) | 50K LI | AI engineering, agents | EN | **Niche overlap** |

### Voice AI + Agent Infrastructure

| Person | Followers | Niche | Language | Relevance |
|--------|-----------|-------|----------|-----------|
| [Mati Staniszewski](Mati%20Staniszewski/profile.md) | — | Voice AI (ElevenLabs CEO) | EN | Voice AI market leader |
| [Harrison Chase](Harrison%20Chase/profile.md) | — | Agent orchestration (LangChain) | EN | Agent infra authority |

### AI Adoption

| Person | Followers | Niche | Language | Relevance |
|--------|-----------|-------|----------|-----------|
| [Ruben Hassid](Ruben%20Hassid/profile.md) | 725K | "How to AI" without coding | EN | Adoption content model |
| [Ethan Mollick](Ethan%20Mollick/profile.md) | 300K | Research-backed AI adoption | EN | Academic adoption model |

### Spanish / Bilingual

| Person | Followers | Niche | Language | Relevance |
|--------|-----------|-------|----------|-----------|
| [Freddy Vega](Freddy%20Vega/profile.md) | 455K | Platzi, AI education LatAm | **ES/EN** | **Colombian, bilingual model** |
| [Nina Fernanda Duran](Nina%20Fernanda%20Duran/profile.md) | 41K | AI architecture | **ES/EN** | Visual bilingual model |
| [Carlos Santana/DotCSV](Carlos%20Santana%20Vega/profile.md) | 800K YT | Spanish AI education | ES | Top Spanish AI educator |
| [Sebastian Ramirez](Sebastian%20Ramirez/profile.md) | 50K | FastAPI, open source | **EN/ES** | **Colombian builder** |

## The Gap Juan Can Fill

**No one on LinkedIn is doing voice AI adoption content.** The builders (ElevenLabs, Deepgram) target developers. The adoption creators (Ruben Hassid, Bernard Marr) cover general AI. Nobody bridges both worlds for the adoption audience.

## Priority Connections (Colombian Network)

1. **Freddy Vega** — Platzi CEO, bilingual, fellow Colombian
2. **Sebastian Ramirez** — FastAPI creator, fellow Colombian
3. **Santiago Valdarrama** — Production ML, similar career path
4. **Henry Jiménez** — Evolupedia, largest Spanish AI community, Colombian in Spain
5. **Laura Montoya** — LatinX in AI founder, Colombian heritage

## Scraped Data

Profiles with `posts-raw.json` + `screenshots/` + `scrape-report.md` have been scraped via Playwright. Run `scraper/scrape-all.sh` to refresh.
