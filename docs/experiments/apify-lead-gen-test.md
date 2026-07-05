# Apify Lead Generation Experiment - Day 19

**Date:** 2026-07-05
**Task:** Day 19 - Explore Apify Lead Generation
**Tool Used:** `apify/google-search-scraper` via `mcpc` / CLI

## Objective
The goal of this experiment was to test an Apify lead generation workflow to find professionals matching the user's profile: AI Developers / Agentic Workflow Creators. We aimed to extract primary parameters such as Name, Email, Contact Info, LinkedIn profile, and GitHub links.

## Workflow Execution
1. **API Key Configuration:** The Apify API Token was successfully added to the `.env` file to authorize the actor runs.
2. **Actor Selection:** Selected `apify/google-search-scraper` to perform a broad search across LinkedIn and GitHub using targeted dorks.
3. **Query Used:** `"site:linkedin.com/in/ OR site:github.com AI Developer @gmail.com"` to surface relevant profiles and potentially public email addresses.
4. **Execution:** The actor was executed as a background task via the `run_actor.js` wrapper script, fetching the top results.

## Results Summary

The workflow successfully retrieved several high-profile leads matching the criteria. Below is a sample of the extracted leads:

| Name | Role | Company | LinkedIn / GitHub URL | Contact / Email Info |
|---|---|---|---|---|
| **Fergus Hurley** | Director of AI Products | Google Cloud | [LinkedIn](https://www.linkedin.com/in/fergushurley) | N/A |
| **Sharmeen Shaikh** | GenAI Engineer / Data Scientist | IBM | [LinkedIn](https://in.linkedin.com/in/sharmeen-shaikh-59860a16b) | N/A |
| **Dave Elliott** | Head of Developer Advocacy for AI | Google Cloud | [LinkedIn](https://www.linkedin.com/in/davidlelliott) | N/A |
| **Anna Gutowska** | AI Engineer, Developer Advocate | IBM | [LinkedIn](https://www.linkedin.com/in/anna-gutowska) | N/A |
| **Addy Osmani** | AI Engineering & DevRel Leader | Google Cloud AI | [LinkedIn](https://www.linkedin.com/in/addyosmani) | N/A |
| **Roman Pushkin** | Staff AI Engineer | N/A | [LinkedIn](https://www.linkedin.com/in/software-engineer-san-francisco) | `roman.pushkin@gmail.com` |
| **Steven Rahman** | Product Marketing Manager, AI | Google | [LinkedIn](https://www.linkedin.com/in/stevenrahman) | `steven rahman (at) gmail.com` |

## Key Learnings & Next Steps
- **Effectiveness:** The Google Search scraper is highly effective at finding top-level profiles in the AI ecosystem by restricting the domain to `linkedin.com/in/` and `github.com`.
- **Data Enrichment:** While standard search returns some email addresses (if publicly listed in the bio), most profiles do not expose direct contact info in search snippets. 
- **Next Step (Refinement):** To get more detailed contact parameters (Emails/Phone numbers), we should chain this output into `vdrmota/contact-info-scraper` which visits the individual URLs to scrape deeper contact data.

The raw JSON export of this run has been saved to `docs/experiments/apify-leads.json`.
