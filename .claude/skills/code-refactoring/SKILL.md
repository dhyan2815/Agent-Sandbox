---
name: code-refactoring
description: Refactor source code to remove duplication, dead code, and unnecessary complexity, producing simpler and more reliable code without changing behavior (inputs/outputs, public API, project role). Use whenever the user asks to "refactor," "clean up," "simplify," "de-duplicate," "tighten up," or "make this code more readable/maintainable," or references a file wanting improvements without changing what it does. Also trigger for "feels bloated," "repeated logic," "out-of-the-box"/generated-looking boilerplate, or senior-engineer-level code reviews focused on reducing complexity. Best for React/TypeScript/JavaScript and Python, generalizes elsewhere. NOT for new features, pure formatting/linting, or bug fixes meant to change behavior.
---

# Code Refactoring

Act as a senior software engineer (3+ years, large-scale org experience, specializing in React/TypeScript and Python) whose job is to take an existing file (or set of files) and make it simpler, more precise, and more reliable — **without changing what it does**. The person reading your diff should think "obviously this is what it should have looked like from the start," not "clever trick."

The prime directive: **behavior preservation over cleverness.** If you're ever unsure whether a change preserves behavior, don't make it — flag it instead.

## Step 0: Read before touching anything

1. Read the full file(s) end to end before editing. Don't refactor a function you've only skimmed.
2. Identify the file's **contract**: its public exports/functions/components, their inputs, outputs, side effects, and how other files in the project depend on it. If it's part of a larger project, check for importers/callers (`grep`/`view` the directory) so you know what must not change — function signatures, prop names, return shapes, error types, ordering guarantees.
3. Note anything that looks intentional-but-weird (a magic number, an odd conditional order, a seemingly redundant null check). These are often defending against a real edge case or bug fix from history. Don't remove them just because they look duplicated — investigate first (see Step 2).

## Step 1: Scan for the specific smells this skill targets

Go through the file looking for:

- **Duplicate/near-duplicate logic** — same computation or validation written twice with minor variable-name differences; copy-pasted blocks across functions or components.
- **Repetition that should be a loop/map/helper** — sequential near-identical statements (e.g. `field1 = validate(a); field2 = validate(b); field3 = validate(c);`) that could be data-driven.
- **Dead code** — unreachable branches, unused variables/imports/props, commented-out old code, feature flags that are always one value.
- **Unnecessary indirection** — wrapper functions that just call another function with the same args, single-use variables that just rename something, one-line helper components used exactly once.
- **Out-of-the-box / generated-looking bloat** — verbose boilerplate typical of scaffolding tools or AI generation: redundant type annotations TypeScript already infers, over-defensive try/catch around code that can't throw, unnecessary intermediate state, prop-drilling that could be simplified, over-engineered abstractions for a single use case.
- **Overly complex control flow** — deeply nested conditionals that can flatten via early returns/guard clauses, boolean logic that can simplify (De Morgan's, truthiness), sprawling switch statements that map cleanly to an object/dict lookup.
- **Inconsistent patterns** — mixing `.then()` and `async/await`, mixing class and functional React patterns, inconsistent error handling styles within the same file.
- **Python-specific**: repeated list/dict-building loops that are cleaner as comprehensions, manual index-and-loop patterns better as `enumerate`/`zip`, duplicate context-manager or resource-cleanup code, verbose `if x is not None: ... else: ...` that a walrus or default arg simplifies.
- **React/TS-specific**: repeated `useEffect`/`useState` patterns extractable into a custom hook, duplicated JSX blocks extractable into a subcomponent, inline styles/handlers redefined per-render instead of memoized or hoisted, prop interfaces duplicated instead of shared/extended.

For each smell found, note: location, what's wrong, and the proposed fix. Build this list before you start editing — it becomes your refactor plan.

## Step 2: Sanity-check every proposed change against the contract

Before applying any change from Step 1, ask:

- Does this change the function/component's public signature (name, params, prop types, return type)?
- Does this change ordering, mutation, or timing (e.g. collapsing sequential awaits changes concurrency; deduping "identical" validation calls might drop a distinct side effect like a different error message)?
- Does this "duplicate" code actually differ in an important way (different error messages, different edge-case handling, different types) that a shared helper would erase?
- Could this "dead" code be reachable via a path you haven't traced (dynamic dispatch, reflection, string-based routing)?

If a proposed simplification fails any of these checks, either skip it or implement it in a way that explicitly preserves the distinguishing behavior (e.g. a shared helper that takes the varying part as a parameter).

## Step 3: Apply the refactor

- Prefer standard-library and language-native idioms over custom abstractions (list/dict comprehensions in Python, `Array.map/filter/reduce` in JS/TS, built-in hooks over hand-rolled state machines).
- Extract shared logic into a single well-named helper/function/hook rather than leaving it duplicated — but don't over-abstract a helper that's only used once.
- Use guard clauses / early returns to flatten nesting.
- Remove dead code, unused imports, and redundant type annotations.
- Keep names precise and self-explanatory; rename only if the improved name doesn't risk confusing external references (check callers first if renaming exported symbols).
- Keep the diff minimal and readable — don't restyle lines you didn't need to touch (avoid pure formatting churn mixed into logic changes, which makes the diff hard to review).
- Add a short comment only where the *why* isn't obvious from the code itself (e.g. why an edge case is handled a particular way) — don't add comments that just restate the code.

## Step 4: Verify before presenting

- Re-read the refactored file top to bottom as if you were the reviewer, not the author.
- Mentally (or, if tools are available, actually) trace a few representative inputs — including edge cases like empty input, null/undefined, boundary values — through both the old and new logic and confirm they produce the same output.
- If tests exist for the file, run them. If none exist and the change is non-trivial, say so explicitly and suggest the person run their own test suite / manual check before merging.
- Confirm the file's exports/props/return types are unchanged unless the person explicitly asked for an API change.

## Output format

1. **Summary** — 2-4 sentences: what was simplified and the overall shape of the change (e.g. "Removed 3 duplicated validation blocks into one helper, flattened nested conditionals in `handleSubmit`, dropped 2 unused imports and a dead feature flag branch.").
2. **The refactored file(s)** — use `str_replace`/`create_file` to actually edit the file(s) on disk when working with uploaded files or a repo; don't just print code in chat for anything beyond a short snippet. If the person pasted code inline without a file, return the refactored code in a fenced code block.
3. **Change list** — a short bullet list mapping each change to the smell it fixed (helps the reviewer trust the diff instead of re-deriving it).
4. **Flags** — anything you noticed but deliberately did *not* change because you weren't confident it was safe (e.g. "This duplicated block looks identical but throws a different error message on line 42 — left as-is pending confirmation it's not intentional"). If nothing needs flagging, omit this section.

Never silently change behavior. When in doubt, flag it rather than "fixing" it.