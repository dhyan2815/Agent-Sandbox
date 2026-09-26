# Brand Kit — Build Log

---

## Identity

Not a content-creator carousel. Looks like a live engineering log — terminal chrome, monospace accents, real (or realistic) product screenshots in clean cards, with one gradient "pop" moment per slide. Feels like a screenshot of someone actually shipping, not a designed template. Matches the voice in `voice.md`: direct, urgent, technical builder narrating live experiments.

---

## Canvas

- **Dimensions:** 1080 × 1350px (LinkedIn portrait)
- **Format output:** PNG per slide + one combined PDF
- **Slide numbering:** **Top-right**, format `0N/NN` (e.g. `03/10`), muted mono
- **Handle watermark:** Bottom-left of every slide — avatar + `dhyan2815 · [link or tag]` — muted, never bold
- **Swipe cue:** Bottom-right of every non-final slide — `SWIPE →` in muted mono

---

## Colours

| Role                | Hex       | Usage                                              |
|---------------------|-----------|-----------------------------------------------------|
| Background          | `#0B0E14` | Slide background — near-black, slight blue cast |
| Grid texture         | `#161B24` | Faint dot-grid overlay on background, low opacity (~15%), never a hard visible line grid |
| Panel / card         | `#12151C` | Code blocks, screenshot cards — one step lighter than background |
| Text primary         | `#E6E8EB` | Headlines, body text — off-white, never pure `#FFFFFF` |
| Text muted           | `#6B7280` | Labels, line numbers, footer, watermark |
| Accent (signal)      | `#7CFF6B` | Terminal green — cursor, prompts, headline glyphs, "run"/success states |
| Accent (link)        | `#58A6FF` | Cool accent — links, tags, gradient endpoint |
| Gradient highlight    | `#7CFF6B → #58A6FF` | Background of the one gradient highlight box per slide (dark `#0B0E14` text on top) |
| Accent (diff add)    | `#3FB950` | Git-diff green — `+` lines, "after"/correct side |
| Accent (diff del)    | `#F85149` | Git-diff red — `-` lines, "before"/wrong-way callouts |

The gradient (`#7CFF6B → #58A6FF`) is reserved for exactly two places: the headline highlight box and the step pill. It never appears anywhere else on a slide — that scarcity is what makes it read as a "pop," not decoration.

---

## Typography

| Role          | Font            | Weight | Case          |
|---------------|-----------------|--------|---------------|
| Headlines      | JetBrains Mono  | 700    | Sentence case (never ALL CAPS) |
| Body           | Inter           | 400/500| Sentence case |
| Code / labels  | JetBrains Mono  | 400    | As-written, `#7CFF6B` on `#12151C` |
| Step pill / swipe cue | Inter | 600    | As-written, small tracked caps allowed only here |

### Font Size Floor
- Never below 15px for any visible text
- Body text minimum: 18px
- Headlines: 56–100px depending on length (fewer words = bigger type)
- Line-number / label text: 12–14px

Mono headlines are the whole differentiator. One phrase per headline sits inside the gradient highlight box (dark text on the gradient) — this is the single "designed" moment per slide, everything else stays flat and typographic.

---

## Signature Motifs (use across every asset)

1. **Prompt-glyph headline prefix** — every headline is preceded by `>` in accent green: `> How RAG actually works`
2. **Gradient highlight box** — exactly one key phrase per slide sits in a rounded box filled with the signal→link gradient, dark text on top. This is the scroll-stopping moment, used once per slide, never twice.
3. **Blinking-cursor block `█`** — accent-green, reserved for cover and CTA slides only (not every slide)
4. **Screenshot / mockup card** — the primary bottom-half visual: a rounded card (`#12151C`, 14px radius, soft dark shadow) holding a real screenshot when one exists, or a realistic coded mockup (terminal, code editor, diff) when it doesn't. Real over illustrated whenever a real screenshot is available.
5. **Gradient step pill** — top-left label per body slide, small rounded pill filled with the signal→link gradient, dark text, e.g. `STEP 1` or `ARCHITECTURE`
6. **Diff-style before/after** — inside a code card only: `- ` (red) and `+ ` (green) prefixed lines like a real git diff
7. **Line-number gutter** — inside code/terminal cards showing sequential output, editor-style (`01`, `02`), not a slide-level element anymore (superseded by the step pill at slide level)

---

## Slide Structure

### Every Content Slide Must Include
1. **Gradient step pill** — top-left, e.g. `STEP 2` or `THE PROBLEM`
2. **Slide counter** — top-right, muted mono, `0N/NN`
3. **Headline** — JetBrains Mono Bold, `>` prompt prefix, one phrase in the gradient highlight box
4. **Body text** — max 2–3 lines, Inter, 18–20px, `#E6E8EB`
5. **Visual card** — bottom half: real screenshot if available, otherwise a realistic coded terminal/code/diff/flow mockup in a rounded `#12151C` card with soft shadow. Never left empty.
6. **Footer** — avatar + `dhyan2815 · [tag]` bottom-left; `SWIPE →` bottom-right (muted mono)

### Cover Slide (Slide 1)
- Full-bleed `#0B0E14` background with faint dot-grid texture
- Avatar + handle top-left (small)
- Massive headline, `>` prompt prefix, one phrase in the gradient highlight box
- Cursor block `█` blinking at the end of the headline
- Subline: slide count + topic tag in muted mono, e.g. `6 SLIDES · BUILD LOG`
- No step pill, no swipe cue, no slide counter on the cover

### CTA / Final Slide
- Background stays `#0B0E14` with grid texture (no colour flip)
- Cursor block `█` large, centred above CTA text
- CTA line: one direct instruction, `>` prefix, key phrase in the gradient highlight box
- Footer: avatar + `dhyan2815 · [link]`, centred or bottom-centre. No `SWIPE →` on the last slide.

---

## Visual Card Content (choose one per slide)

Priority order — pick the first one that genuinely fits the content:

1. **Real screenshot** — an actual product UI, terminal output, or app screenshot the user supplies, placed in the rounded card as-is (cropped/framed, never stretched)
2. **Realistic coded terminal block** — dark terminal chrome, monospace prompt and output, `#7CFF6B` text
3. **Realistic coded editor/diff block** — syntax-highlighted code or git-diff formatting (red `-` / green `+`)
4. **Flow diagram** — CSS-only, numbered nodes connected by thin accent-green arrows, used only when no screenshot or code fits (e.g. architecture overviews)
5. **Comparison table** — headers in accent green, alternating row shading in `#12151C`

No emoji icons. No stock illustrations. No clipart. Real or realistic beats illustrated every time.

---

## Aesthetic Rules

1. **Dark-first, dark-always** — every slide, including CTA, stays on `#0B0E14` with the faint grid texture. No light slides, no colour-flip finale.
2. **High contrast** — `#E6E8EB` text on `#0B0E14` must pass WCAG AA.
3. **One idea per slide.** Structured density, never cluttered.
4. **Gradient and rounded pills are allowed in exactly two places**: the headline highlight box and the step pill. Everywhere else stays flat, sharp-ish (small radius on cards only), no drop shadows except the one soft shadow under visual cards.
5. **Consistent spacing** — 48px padding on all edges of slide content area.
6. **Max 2 font weights per slide** (excluding the step pill/swipe cue, which use their own small Inter 600).
7. **Left-align everything** except the cover headline and CTA line, which may centre.

---

## Asset Paths

```
assets/
  headshot.png           ← Avatar used in every footer and on the cover
  screenshots/            ← Real product/UI screenshots to drop into visual cards
  logos/                 ← Brand logos for use in content if needed
  icons/                 ← Any approved icon PNGs
```

Claude reads `assets/` before building. Never hardcode image paths outside this folder.

---

## Tone

Matches `voice.md`: direct, urgent, hands-on, contrarian where earned.

- **Headlines:** `>` prompt + sentence case, action-first, one phrase in the gradient box. ("How RAG actually works", "I stopped writing code three weeks ago")
- **Body:** One punchy sentence. Bold the payoff phrase in accent green.
- **No exclamation marks, no motivational filler, no ALL CAPS shouting.** Say what it is, say why it matters, stop.

---

## Build Method

Carousels are built as **HTML/CSS, not diffusion image generation**. One shared stylesheet per carousel, per-slide HTML with the copy swapped in, rendered and screenshotted at exactly 1080×1350. This guarantees pixel-identical spacing, colour, and type across every slide in a set — something no image model currently holds reliably across independent generations.

---

## Usage

This file is read automatically by `gemini-carousel`, `graphic-designer`, and `pinned-comment` before every build. It is the single source of truth for colours, fonts, layout, and tone. Do not override values inline — edit here and rebuild.

---

*Brand Kit v2.1 · Build Log · Dhyan Patel · @dhyan2815*
