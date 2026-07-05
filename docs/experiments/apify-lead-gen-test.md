# Day 19 Experiment: Apify Lead Generation Skill Exploration

## Objective

Review the `apify-lead-generation` skill and design a concrete lead generation workflow for the Agent Sandbox project. The goal is to understand how Apify Actors integrate with the CLI workflow, what inputs and outputs look like, and what a production-ready run would entail.

> **Status:** Dry-run / design review. The `APIFY_TOKEN` is not yet configured in `.env`. This document captures the skill review, planned workflow, and setup steps needed before a live run.

---

## Skill Review

**File:** `.claude/skills/apify-lead-generation/SKILL.md`

The skill provides a 5-step workflow for scraping leads from platforms like Google Maps, Instagram, TikTok, Facebook, and YouTube using hosted Apify Actors over their REST API.

### Key Components

| Component | Details |
|---|---|
| **Runtime** | Node.js 20.6+ (native `--env-file` flag) |
| **Auth** | `APIFY_TOKEN` in `.env` file |
| **CLI tool** | `mcpc` (`npm install -g @apify/mcpc`) for schema introspection |
| **Runner script** | `reference/scripts/run_actor.js` (12 KB, handles start, poll, export) |
| **Output formats** | CSV, JSON, or quick-answer (top 5 displayed in chat) |

### Available Actors (Selected)

| Use Case | Actor ID | Notes |
|---|---|---|
| Local business leads | `compass/crawler-google-places` | Best for restaurants, clinics, shops |
| Email extraction | `poidata/google-maps-email-extractor` | Extracts emails from Maps listings |
| Contact enrichment | `vdrmota/contact-info-scraper` | Scrapes emails/phones from known URLs |
| Instagram profiles | `apify/instagram-profile-scraper` | Influencer/creator discovery |
| TikTok creators | `clockworks/tiktok-profile-scraper` | Creator outreach |
| Google Search | `apify/google-search-scraper` | Broad lead discovery |

---

## Planned Workflow: Tech Startup Leads in Mumbai

This is a concrete workflow that would be executed once the `APIFY_TOKEN` is configured.

### Target: AI / Tech Startups on Google Maps — Mumbai, India

**Step 1: Select Actor**

`compass/crawler-google-places` — best for local business scraping with structured output (name, address, phone, website, rating, reviews).

**Step 2: Fetch Actor Schema (once mcpc is installed)**

```bash
# Requires mcpc and a valid APIFY_TOKEN in .env
export $(grep APIFY_TOKEN .env | xargs)
mcpc --json mcp.apify.com \
  --header "Authorization: Bearer $APIFY_TOKEN" \
  tools-call fetch-actor-details \
  actor:="compass/crawler-google-places" | jq -r ".content"
```

**Step 3: Define Input Parameters**

```json
{
  "searchStringsArray": ["AI startup", "tech startup", "software company"],
  "locationQuery": "Mumbai, Maharashtra, India",
  "maxCrawledPlacesPerSearch": 20,
  "language": "en",
  "exportPlaceUrls": true
}
```

- 3 search terms x 20 results = up to 60 raw leads
- Language set to English for consistent output
- Place URLs exported for follow-up enrichment

**Step 4: Run Command**

```bash
# Export to CSV for filtering
node --env-file=.env \
  .claude/skills/apify-lead-generation/reference/scripts/run_actor.js \
  --actor "compass/crawler-google-places" \
  --input '{"searchStringsArray":["AI startup","tech startup","software company"],"locationQuery":"Mumbai, Maharashtra, India","maxCrawledPlacesPerSearch":20,"language":"en","exportPlaceUrls":true}' \
  --output 2026-07-05_mumbai-tech-leads.csv \
  --format csv
```

Expected run time: 2-4 minutes. Default timeout: 600 seconds.

**Step 5: Expected Output Fields**

From the Google Places Actor, each row would contain:

| Field | Example Value |
|---|---|
| `title` | TechMahindra Ltd |
| `address` | Andheri East, Mumbai, MH 400069 |
| `phone` | +91 22 6739 4200 |
| `website` | https://www.techmahindra.com |
| `rating` | 4.2 |
| `reviewsCount` | 318 |
| `placeUrl` | https://maps.google.com/?cid=... |
| `categoryName` | Software company |

---

## Setup Checklist (To Execute Live Run)

- [ ] Create an [Apify account](https://apify.com/) and retrieve the API token from the Console
- [ ] Add `APIFY_TOKEN=apify_api_...` to the `.env` file in the repo root
- [ ] Ensure Node.js 20.6+ is installed: `node --version`
- [ ] Install the `mcpc` CLI: `npm install -g @apify/mcpc`
- [ ] Verify `.env` is in `.gitignore` (never commit the token)
- [ ] Run the actor command above and review the output CSV

---

## Script Architecture Summary

The `run_actor.js` script handles the complete lifecycle of an Apify Actor run:

1. **Argument parsing** via Node's native `parseArgs`
2. **Actor start** — `POST /v2/acts/{actorId}/runs` with JSON input body
3. **Status polling** — `GET /v2/actor-runs/{runId}` every 5 seconds (configurable) until `SUCCEEDED`, `FAILED`, `ABORTED`, or `TIMED-OUT`
4. **Dataset fetch** — `GET /v2/datasets/{datasetId}/items` with `format=json`
5. **Export** — CSV serialization via manual header+row generation, or JSON stringify

The script uses only Node.js built-ins (`node:util`, `node:fs`) plus native `fetch` — no external npm packages required beyond the runtime.

---

## Key Learnings

1. **Actor ID format:** The skill uses `author/actor` but the REST API requires `author~actor` — the script handles this automatically with `.replace('/', '~')`.
2. **Polling pattern:** The script only prints status changes (not on every poll), keeping output clean during long runs.
3. **Quick-answer mode:** Omitting `--output` displays only the top 5 results in the terminal — useful for iterative exploration without writing files.
4. **Token security:** The `.env`-based auth pattern keeps the token out of shell history and is compatible with the Node.js `--env-file` flag introduced in v20.6.
5. **Enrichment pipeline:** Google Places output (website URLs) can feed directly into `vdrmota/contact-info-scraper` for email extraction — a natural two-step lead gen workflow.
