# Brand Kit v3 — Field Guide

*Coexists with `brand-kit.md` (Build Log v2.1). This is a separate, distinct system — not a merge. Skills default to `brand-kit.md` unless told to use this file specifically.*

---

## Identity

A warm editorial explainer. Reads like a well-designed how-to guide or field manual, not a terminal log and not a marketing template. Near-black and cream slides alternate for rhythm. Serif display headlines carry narrative weight, with italics doing the emphasis work mono capitals did in Build Log. One burnt-orange accent runs through every slide as the connective thread. Structure carries the "more appealing" feeling: each slide stacks a label, a headline, a body, and a payoff element (callout strip, screenshot, or step list) — never just one flat idea.

---

## Canvas

- **Dimensions:** 1080 × 1080px (square)
- **Slide rhythm:** Cover = dark gradient. Proof/screenshot slides = cream. Step/explainer slides = near-black. Alternate dark/cream across the set so no two adjacent slides share a background — this alternation is itself a signature, not an accident.
- **Slide counter:** Top-right, `0N / NN`, small, muted, tabular numerals
- **Progress bar:** Directly beneath the content block on every content slide (not the cover) — thin track in the slide's muted tone, filled portion in accent orange, width = slide N of total

### Vertical layout rule
The slide is a flex column: top row, content, then progress bar, each following the one above with a fixed gap. The progress bar is **never pinned to the canvas bottom** — any leftover space falls below it, not between the headline and the bar. A slide whose content leaves more than roughly a third of the frame empty is under-filled: add a real element (a numbered list, a second step, a recap row), never padding. The cover is the exception — its lower info band uses `margin-top: auto` to sit on the bottom edge, with the headline scaled up (80–90px) to hold the top.

---

## Colours

| Role                  | Hex       | Usage |
|------------------------|-----------|-------|
| Background (dark)       | `#171310` | Warm near-black — step slides, cover base |
| Background (dark, cover gradient) | `#171310 → #8A431F` | Diagonal gradient, black to burnt orange, cover only |
| Background (cream)      | `#F3EDE4` | Proof/screenshot slides |
| Text on dark (primary)  | `#F3EDE4` | Headlines, body on dark slides |
| Text on dark (muted)    | `#B8AFA3` | Labels, captions on dark slides |
| Text on cream (primary) | `#171310` | Headlines, body on cream slides |
| Text on cream (muted)   | `#7A7266` | Labels, captions on cream slides |
| Accent (orange)         | `#E0672E` | Section labels, episode number, icons, progress fill |
| Accent (callout fill)   | `#B8481C` | Background of the TL;DR callout strip, cream text on top |

One accent colour, two backgrounds. Never introduce a second accent hue.

---

## Typography

| Role              | Font              | Weight        | Notes |
|--------------------|-------------------|---------------|-------|
| Display headline    | Fraunces          | 500 / 600     | Serif. One phrase per headline in italic for emphasis — never the whole headline italic. |
| Body                | Inter             | 400           | Sentence case, generous line height (1.5) |
| Section label        | Inter             | 600, tracked 0.08em, small caps via uppercase | e.g. `PROOF · IT'S REAL` |
| Counters / captions   | JetBrains Mono    | 400, small    | The one mono crossover — reserved for `0N / NN`, figure captions (`FIG. 01`), and callout-strip text only |

### Size Floor
- Headlines: 44–72px depending on length
- Body: 18–20px
- Labels: 13–14px, tracked
- Callout strip text: 14–16px, mono, uppercase

---

## Slide Types

### 1. Cover
- Dark gradient background (`#171310 → #8A431F`, diagonal)
- Top-left: author name + small dot marker, small tracked caps
- Top-right: episode/series tag, e.g. `NO. 31 — TOPIC`
- Section label: `@handle · N jobs` or equivalent context line, orange
- Headline: large serif, one phrase italic, 3–5 lines max
- Optional mascot (see Mascot Rule) — bottom-right, only if genuinely relevant to this topic
- Lower band (cream or slightly lighter dark): `RUNS ON / N CONNECTED TOOLS` label + small tool icon chips, then one sentence of proof copy, then a muted logo strip for social proof
- No progress bar, no slide counter on the cover

### 2. Proof / Screenshot slide
- Cream background
- Top-right counter, top-left section label (orange, tracked caps) — e.g. `PROOF · IT'S REAL`
- Serif headline, one phrase italic
- One paragraph of body copy, muted
- Real screenshot in a bordered card with soft shadow, cream frame matching page background
- Figure caption below the card: `FIG. 0N — source/url`, mono, muted
- Callout strip at the bottom: full-width bar, `#B8481C` fill, cream mono uppercase text, one payoff line

### 3. Step / Explainer slide
- Dark background
- Top-left section label (`SET IT UP · 1 OF 2`), top-right counter
- Serif headline, one phrase italic
- Numbered step list (2–3 steps per slide): each step = bold number + short serif subhead + one-line body + its own orange-bordered callout strip directly underneath (not one shared strip for the whole slide)
- Progress bar at the very bottom

---

## Narrative Arc (how the copy is sequenced)

Every carousel runs one story, not a list of facts: **Problem → Experience → Insight → Action**. Slides serve the arc; the slide types above are just how each beat gets dressed.

| Beat | Slides | What it does |
|------|--------|--------------|
| **Problem** | 1–2 | Name a specific pain the reader already feels. The cover states it, the next slide makes it concrete with real numbers or a real list. Never open with a definition or a product name. |
| **Experience** | 3–4 | What you actually noticed or found. This is what turns generic advice into insight, and it is where authority comes from. |
| **Core** | 5–6 | How the thing works, one idea per slide, with the mechanism shown (step list, labelled chain, real screenshot). |
| **Insight** | 7 | The "aha". The lesson that outlives the specific tool. State it as a position, not a summary. |
| **Action** | 8 | One concrete thing the reader does next, small enough to do today. A recap row may sit above it. The follow ask comes last, never instead of the homework. |

### Honesty guardrail
The Experience beat must be real. For a topic you built with, that is the build story. For a topic you read about or found (news, a launch, someone else's tool), the experience is **the discovery and what it changed in your thinking** — never a fabricated "I tried it and struggled" arc. If there is no genuine experience of either kind, cut the beat rather than invent one.

### Emotion, in this voice
`voice.md` never does sentiment, so the "add emotion" step lands as **stakes and tension**, not feelings: what it costs to keep doing it the old way, what you were getting wrong, what breaks at scale. Tension, not vulnerability.

### Length
8 slides is the default for a full arc. 6 only when the Problem and Experience beats genuinely collapse into one slide each. Never more than 10.

---

## Mascot Rule

Use a mascot only when the topic itself suggests a character or agent worth personifying — never by default, never as filler. When used: appears once, on the cover only, small enough to sit beside the headline without competing with it. If the content has no natural character concept (an abstract system, a pricing update, a pure data point), skip the mascot entirely rather than forcing one in. No placeholder art — either a real asset exists for this topic or the slide goes without.

---

## Callout Strip (the payoff element)

A full-width or step-width bar, `#B8481C` fill, cream mono uppercase text, one line, ≤12 words. This is the "so what" of the slide or step — the one thing to remember if nothing else is read. Every step slide and every proof slide gets exactly one per unit (one per step, one per slide for proof slides). Never decorative, always the single highest-value takeaway of that block.

---

## Screenshot Card

Real screenshots only — never illustrated mockups in this kit (that's Build Log's job). Bordered card, soft shadow, background matches the slide (cream frame on cream slides). Always captioned underneath: `FIG. 0N — source or url`, mono, muted, small.

---

## Tool / Logo Strip

Small, muted, grayscale-leaning row of partner or tool logos/wordmarks, used only on the cover as social proof. Never more than 4 logos. Never full-colour competing with the orange accent.

---

## Aesthetic Rules

1. **Alternate backgrounds across the set.** No two adjacent slides share dark or cream.
2. **One accent hue only** — burnt orange. No secondary accent colour anywhere.
3. **One italic phrase per headline**, never the whole headline, never more than one phrase.
4. **Every step or proof slide carries a callout strip.** This is the structural richness that replaces a single flat visual — always the payoff, never decorative.
5. **Real screenshots only** in this kit, always captioned.
6. **Progress bar on every content slide**, absent only on the cover.
7. **Mascot is conditional and rare** — see Mascot Rule. Default is no mascot.

---

## Build Method

Same as Build Log: HTML/CSS, not diffusion image generation. One shared stylesheet per carousel, per-slide HTML with the copy and screenshots swapped in, rendered and screenshotted at exactly 1080×1080 (Playwright, full resolution — not the chat preview's downscaled capture). This is what guarantees the alternating backgrounds and repeated structural elements (callout strip, progress bar, screenshot card) land pixel-identical across every slide of a set.

---

## Tone

Same voice as `voice.md`: direct, practical, field-tested. The serif and italics buy a slightly more narrative register than Build Log's terminal bluntness, but the content discipline is identical: no fluff, one clear payoff per unit, real evidence (real screenshots, real dates, real docs) over abstract claims.

- **No em dashes anywhere**, in slide copy or captions. Project-wide rule from `voice.md`. Use a full stop or a colon instead.
- **No exclamation marks, no motivational filler.** Say what it is, say why it matters, stop.

---

## Usage

This file is a second, complete brand system alongside `brand-kit.md`. They are not blended. When asked to build a carousel, confirm which kit applies before defaulting — Build Log for technical/system-build posts, Field Guide for tutorial/how-to/setup-guide posts (this one suits step-by-step content better).

---

*Brand Kit v3.0 · Field Guide · Dhyan Patel · @dhyan2815*
