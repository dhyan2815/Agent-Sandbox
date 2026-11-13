# Phase 5: a long-book golden set, before and after book structure (2026-11-13)

A 200-page manual (10 chapters, 2 sections each, a PDF outline), 20 questions, answered by the configured model (live). Before: no outline paths, no summaries. After: outline paths, extractive section summaries, chapter summaries written on demand, summaries searched first for questions about a whole.

| | Fact questions: fact in answer | Whole-book questions: topic terms in the passages kept for the answer | ... in the answer | Model calls per question (mean) |
|---|---|---|---|---|
| before | 1.0 | 0.75 | 0.344 | 3.2 |
| after | 1.0 | 0.797 | 0.541 | 3.5 |

## Whole-book questions

| Question | Before: context / answer / calls | After: context / answer / calls |
|---|---|---|
| What is chapter 4 about? | 1.0 / 0.0 / 3 | 0.75 / 0.0 / 4 |
| What does chapter 7 cover? | 1.0 / 1.0 / 3 | 1.0 / 0.5 / 4 |
| Summarise chapter 9. | 1.0 / 0.75 / 3 | 0.75 / 0.75 / 4 |
| What is chapter 1 about? | 1.0 / 0.0 / 3 | 0.75 / 0.75 / 4 |
| Summarise chapter 10. | 1.0 / 1.0 / 3 | 1.0 / 0.75 / 4 |
| Compare chapters 2 and 3. | 0.0 / 0.0 / 5 | 0.875 / 0.625 / 5 |
| Which chapter covers net metering, and what does it say? | 1.0 / 0.0 / 3 | 0.75 / 0.75 / 6 |
| What is this book about overall? | 0.0 / 0.0 / 5 | 0.5 / 0.2 / 3 |

## What this does not show

- The book is synthetic: chapters on distinct topics make the gain easy to see. A real book's chapters overlap more.
- The 'answer' score counts topic terms, a proxy for a good summary, not a judge.
- The first whole-book question pays for the chapter summaries it needs; later ones reuse them, so the mean calls fall as the collection is used.
