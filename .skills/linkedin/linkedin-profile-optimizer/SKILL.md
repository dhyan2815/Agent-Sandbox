---
name: linkedin-profile-optimizer
description: >
  Audits and rewrites LinkedIn profiles using a structured strategist framework.
  Use this skill whenever the user shares their LinkedIn URL and wants to improve
  it, get more visibility, attract recruiters, grow followers, or increase
  conversions. Also trigger when the user says things like "optimize my LinkedIn",
  "rewrite my LinkedIn", "improve my profile", "audit my LinkedIn", "make my
  LinkedIn better", "LinkedIn headline help", "LinkedIn About section", or
  "LinkedIn for job search". Even if the user only shares a URL, use this skill
  to navigate to the profile and guide the improvement.
---

# LinkedIn Profile Optimizer

A skill for auditing and rewriting LinkedIn profiles to maximize visibility, credibility,
and conversions — whether the user's goal is getting hired, growing a following, or
generating leads.

---

## When This Skill Triggers

- User shares a LinkedIn profile URL
- User asks to improve/rewrite/audit any LinkedIn section via URL
- User mentions wanting more profile views, recruiter reach, or better personal branding via their profile URL

---

## Input Handling

LinkedIn profiles arrive in several forms. Handle each:

| Input Type | How to Handle |
|---|---|
| LinkedIn URL | Use browser tools to visit the URL and extract all visible profile content |
| Partial section URL | If a specific post or section URL is shared, optimize that while suggesting profile-wide improvements |
| No URL provided | Ask the user to share their LinkedIn URL to begin the audit |

---

## Core Workflow

### Step 1 — Adopt the Strategist Persona

Begin every optimization as a LinkedIn strategist. Your lens:
- **Hiring managers** skim for clarity, results, and fit in under 10 seconds
- **Recruiters** use ATS keyword matching before even reading
- **Followers/buyers** respond to personality, authority, and value signals

### Step 2 — Audit the Profile

Evaluate each section systematically. For each, flag:
- ❌ **Errors**: Generic language, missing results, keyword gaps, typos
- ⚠️ **Gaps**: Sections that exist but underperform
- ✅ **Strengths**: What's working and should be preserved

**Sections to audit:**

| Section | What to Check |
|---|---|
| **Headline** | Uses job title only? No value prop? No keywords? |
| **About** | First-person? Clear hook in line 1? Covers who/what/why? Under 2,600 chars? |
| **Experience** | Results-oriented bullets? XYZ formula used? Keyword-rich? |
| **Skills** | Top 3 pinned? Matches job targets? Missing industry terms? |
| **Education / Certs** | Complete? Relevant to goals? |
| **Featured / Banner** | Present? Signals credibility? |

### Step 3 — Ask Clarifying Questions

Before writing, ask targeted questions to personalize the output. Keep it to 3–5 focused questions. Examples:

- "What is your primary goal right now — getting hired, freelance clients, building an audience, or something else?"
- "What roles or industries are you targeting?"
- "What's your biggest professional achievement in the last 2 years?"
- "Is there a specific tone you want — corporate, conversational, thought leader?"
- "Are there keywords from job postings you've been targeting?"

**Do not skip this step** — the answers dramatically improve output quality.

### Step 4 — Rewrite Each Section

Apply the formulas below. Always show the **before** (if provided) and the **after**.

---

## Writing Formulas

### Headline Formula
```
[Role/Identity] | [Value Proposition] | [Who You Help or Key Credential]
```
**Example:**
> Product Manager | Turning ambiguous problems into shipped features | 0→1 SaaS | ex-Google

Avoid: Job title only ("Software Engineer at Acme Corp")

---

### About Section Formula
```
Hook (1 sentence — who you are + what makes you different)
↓
What you do + who you help (2–3 sentences)
↓
Key results or proof points (2–3 bullets or sentences)
↓
Call to action (1 sentence — what you want them to do)
```
- Write in **first person**
- Aim for **3–5 short paragraphs**, under 2,000 characters
- Front-load the first 2 lines (visible before "see more")

---

### Experience Bullet Formula (XYZ)
```
I accomplished [X] by doing [Y], resulting in [Z]
```
Rewritten as an achievement bullet:
> Reduced customer onboarding time by 40% by redesigning the activation flow, resulting in a 22% increase in 30-day retention.

Rules:
- **Max 3 bullets per role** (unless a role is highly relevant — then up to 5)
- Lead with a **strong action verb** (Led, Built, Reduced, Launched, Grew...)
- Include **numbers wherever possible** (%, $, time saved, team size)
- Embed **ATS-friendly keywords** naturally (use exact phrases from job descriptions)

---

### Skills Section
- Ensure the top 3 pinned skills match the user's target role
- Add skills that appear frequently in job postings they're targeting
- Remove outdated or irrelevant skills that dilute the profile

---

## Output Format

Deliver optimizations in this order:

1. **Audit Summary** — 3–5 bullet observations (what's hurting the profile most)
2. **Rewritten Headline** — 2–3 options with brief rationale
3. **Rewritten About Section** — 1 full version, with a note on what was changed
4. **Experience Bullets** — Rewritten bullets for each role (up to 3 per role)
5. **Skills Additions** — 5–10 recommended skills to add
6. **Quick Wins** — Other improvements (banner, featured section, URL customization)

---

## Refinement Loop

After delivering the first draft, invite the user to refine:

> "Let me know if anything feels off — too formal, too casual, too long, or not quite *you*. Just tell me what to adjust."

Common refinement requests and how to handle them:

| Request | Response |
|---|---|
| "Too long" | Cut to specified length; prioritize results and keywords |
| "Too corporate" | Loosen tone; add personality markers and first-person voice |
| "Doesn't sound like me" | Ask for 2–3 phrases the user *would* say; rewrite using their voice |
| "Add more keywords" | Identify 5 target job postings, extract recurring terms, weave in naturally |
| "More achievement-focused" | Apply XYZ formula more strictly; add metrics or estimates |

---

## Quality Checklist

Before delivering output, verify:

- [ ] Headline has value prop, not just a job title
- [ ] About section opens with a hook (not "I am a...")
- [ ] Every experience bullet starts with an action verb
- [ ] At least 60% of bullets include a quantified result
- [ ] Skills list contains ATS-relevant industry keywords
- [ ] Tone matches user's stated goal and industry
- [ ] No bullet exceeds 2 lines
- [ ] No section exceeds platform character limits

---

## Notes

- **LinkedIn URL**: Ensure the URL is public or accessible to the agent's browser tool.
- **Privacy settings**: If the profile is private, ask the user to temporarily make it public or share a PDF export as a fallback.
- **Profile photo / banner**: Mention if missing or unprofessional based on the visual scan of the URL, but don't rewrite — just flag as a quick win.
- **Dynamic Content**: LinkedIn pages are dynamic; ensure the browser tool waits for full page load before extraction.