# Quality check: claim checker and LinkedIn outlines

Run 2026-11-14. Generator `groq:openai/gpt-oss-120b`, decisions `groq:openai/gpt-oss-20b`.
Command: `python scripts/quality_check.py --out results/quality-check.md`.

## Claim verdicts

30 claims, 10 per verdict, labelled by the script's author from the fixtures' text. 8 model calls, 22.7 s.

- Accuracy: **30 of 30** (100%)
- Called supported when not supported: **0 of 20** (the error that matters most for a checker)

| Label \ verdict | supported | contradicted | not_found |
|---|---|---|---|
| supported | 10 | 0 | 0 |
| contradicted | 0 | 10 | 0 |
| not_found | 0 | 0 | 10 |

## LinkedIn outlines

8 of 8 questions answered and exported.

- Outlines with a figure not in their answer: **0 of 8**
- Outline points checked against the collection: 21; supported 14, contradicted 1, not found 6

- What is the warranty on the inverter, and who covers it?: not_found, supported.
- How much is the annual service visit?: supported, supported, not_found.
- How often should the panels be cleaned, and how?: supported, supported, not_found.
- What does a 3 kW system cost, and what subsidy does it get?: supported, not_found, supported.
- How long does a standard rooftop installation take?: supported, contradicted, supported.
- When is an alert sent by the monitoring app?: supported, supported.
- How long do refunds take, and where are they paid?: supported, supported.
- What is the payback period of a system?: supported, not_found, not_found.

## What these numbers say

- **The claim set is easy.** Each claim was written from one sentence of the fixtures and
  changes one figure or name, or states something the files never mention. 30 of 30 shows
  the checker handles clear-cut claims on a real model, including one read by OCR from a
  scanned page. It is a ceiling, not a benchmark: paraphrased, partial and multi-part claims
  were not tested, and the labels are the author's, not an independent reader's.
- **Outlines invent no figures** (0 of 8), but **4 of 8 add filler the sources do not
  support**, despite the prompt: "Ensures optimal performance and reduces downtime", "without
  scratching", "becomes cash-flow positive", "compare against other investment
  opportunities". The page already calls the outline a draft; this is why. Running the claim
  checker over each outline before showing it (the outline self-check card) would flag them.
- **The checker misses points that lose their subject.** "Warranty length: 10 years" and "It
  qualifies for a subsidy of 78 000 rupees" are true, but on their own they do not say what
  they are about, so they come back not found. One meta line ("No additional time factors
  are mentioned") came back contradicted. The checker is built for claims that stand alone;
  the split step rewrites claims that way, and outline points skip that step here.
