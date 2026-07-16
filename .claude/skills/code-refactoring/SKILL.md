---
name: code-refactoring
description: Refactor source code to remove duplication, dead code, and unnecessary complexity, producing simpler and more reliable code without changing behavior (inputs/outputs, public API, project role). Use whenever the user asks to "refactor," "clean up," "simplify," "de-duplicate," "tighten up," or "make this code more readable/maintainable," or references a file wanting improvements without changing what it does. Also trigger for "feels bloated," "repeated logic," "out-of-the-box"/generated-looking boilerplate, or senior-engineer-level code reviews focused on reducing complexity. Best for React/TypeScript/JavaScript and Python, generalizes elsewhere. NOT for new features, pure formatting/linting, or bug fixes meant to change behavior.
---

# Code Refactoring: 4-Phase Structured Approach

Act as a senior software engineer (3+ years, large-scale org experience, specializing in React/TypeScript and Python) whose job is to take an existing file (or set of files) and make it simpler, more precise, and more reliable — **without changing what it does**. The person reading your diff should think "obviously this is what it should have looked like from the start," not "clever trick."

The prime directive: **behavior preservation over cleverness.** If you're ever unsure whether a change preserves behavior, don't make it — flag it instead.

---

## Overview: The 4-Phase Process

When refactoring a file (or set of files), follow this structured workflow to ensure consistent, safe, and effective cleanup:

1. **Phase 1: Audit & Understand** — Read the file, identify its contract, understand dependencies
2. **Phase 2: Identify Bloat** — Scan for code smells and build a refactor plan (don't edit yet)
3. **Phase 3: Apply & Refactor** — Execute the refactor plan with safety checks
4. **Phase 4: Verify & Present** — Test, trace logic, confirm behavior preservation, present results

---

## Phase 1: Audit & Understand (Before Any Changes)

### Goal
Understand what you're refactoring and what must not change.

### Steps

1. **Read the full file end-to-end** before touching anything. Don't refactor a function you've only skimmed.

2. **Identify the file's contract** — its public surface and dependencies:
   - What does it export/expose? (functions, components, classes, constants)
   - What are the inputs and outputs of each export?
   - What side effects occur? (API calls, database writes, state mutations, logging)
   - How do other files depend on it? (use `grep`/`view` the directory to check importers/callers)
   - What **must not change**: function signatures, prop names, return shapes, error types, ordering guarantees, return order, timing

3. **Note anything intentional-but-weird** (magic numbers, odd conditional order, redundant null checks). These often defend against real edge cases or historical bug fixes. Don't remove them just because they look duplicated — investigate first (see Phase 2).

4. **Understand the context**:
   - Is this part of a larger project undergoing codebase cleanup?
   - Are there established patterns elsewhere (error handling, naming, async style)?
   - Are there any constraints (performance-sensitive code, legacy compatibility, specific framework patterns)?

---

## Phase 2: Identify Bloat (Scan & Plan — No Editing Yet)

### Goal
Build a comprehensive refactor plan before making any changes.

### Steps

1. **Go through the file systematically looking for code smells:**

   - **Duplicate/near-duplicate logic** — same computation or validation written twice with minor variable-name differences; copy-pasted blocks across functions or components.
   
   - **Repetition that should be a loop/map/helper** — sequential near-identical statements (e.g. `field1 = validate(a); field2 = validate(b); field3 = validate(c);`) that could be data-driven.
   
   - **Dead code** — unreachable branches, unused variables/imports/props, commented-out old code, feature flags that are always one value.
   
   - **Unnecessary indirection** — wrapper functions that just call another function with the same args, single-use variables that just rename something, one-line helper components used exactly once.
   
   - **Out-of-the-box / generated-looking bloat** — verbose boilerplate typical of scaffolding tools or AI generation:
     - Redundant type annotations TypeScript already infers
     - Over-defensive try/catch around code that can't throw
     - Unnecessary intermediate state
     - Prop-drilling that could be simplified
     - Over-engineered abstractions for a single use case
   
   - **Overly complex control flow** — deeply nested conditionals that can flatten via early returns/guard clauses, boolean logic that can simplify (De Morgan's, truthiness), sprawling switch statements that map cleanly to an object/dict lookup.
   
   - **Inconsistent patterns** — mixing `.then()` and `async/await`, mixing class and functional React patterns, inconsistent error handling styles within the same file.
   
   - **Python-specific**:
     - Repeated list/dict-building loops that are cleaner as comprehensions
     - Manual index-and-loop patterns better as `enumerate`/`zip`
     - Duplicate context-manager or resource-cleanup code
     - Verbose `if x is not None: ... else: ...` that a walrus or default arg simplifies
   
   - **React/TS-specific**:
     - Repeated `useEffect`/`useState` patterns extractable into a custom hook
     - Duplicated JSX blocks extractable into a subcomponent
     - Inline styles/handlers redefined per-render instead of memoized or hoisted
     - Prop interfaces duplicated instead of shared/extended

2. **Build the refactor plan** — For each smell found, document:
   - **Location** (line numbers, function name)
   - **What's wrong** (what's the code smell?)
   - **Proposed fix** (what will you change and why?)
   - **Risk level** (low/medium/high — does it touch the public API, ordering, or timing?)
   
   This list becomes your refactor roadmap and helps you catch issues before they happen.

---

## Phase 3: Apply & Refactor (Safety Checks Built In)

### Goal
Execute the refactor plan while ensuring behavior preservation.

### Step 3A: Sanity-check Every Proposed Change

Before applying any change from your Phase 2 plan, ask these questions:

- **Does this change the public signature?** (function/component name, params, prop types, return type)
- **Does this change ordering, mutation, or timing?** (e.g. collapsing sequential awaits changes concurrency; deduping "identical" validation calls might drop a distinct side effect like a different error message)
- **Does this "duplicate" code actually differ in an important way?** (different error messages, different edge-case handling, different types) that a shared helper would erase?
- **Could this "dead" code be reachable via a path I haven't traced?** (dynamic dispatch, reflection, string-based routing)

If a proposed change fails any of these checks:
- **Skip it** (leave the code as-is) and flag it in your notes, OR
- **Implement it carefully** in a way that explicitly preserves the distinguishing behavior (e.g. a shared helper that takes the varying part as a parameter)

### Step 3B: Apply the Refactor

Execute your plan with these principles:

- **Prefer standard-library and language-native idioms** over custom abstractions:
  - Python: list/dict comprehensions, `enumerate`/`zip`, walrus operator
  - JS/TS: `Array.map/filter/reduce`, template literals, optional chaining, nullish coalescing
  - React: built-in hooks over hand-rolled state machines, composition over prop drilling

- **Extract shared logic into a single well-named helper/function/hook** rather than leaving it duplicated.
  - **Rule**: Only extract if used 2+ times in the file. Don't over-abstract a helper that's only used once.
  - Name the helper for what it does, not where it's used (e.g. `validateEmail`, not `checkField1And2`)

- **Use guard clauses / early returns to flatten nesting**:
  ```python
  # Before: deeply nested
  if user:
      if user.is_active:
          if user.has_permission('edit'):
              return do_edit(user)
  
  # After: guard clauses
  if not user or not user.is_active or not user.has_permission('edit'):
      return None
  return do_edit(user)
  ```

- **Remove dead code** aggressively:
  - Unused imports
  - Unused variables
  - Unreachable branches
  - Redundant type annotations (if TypeScript/linter can infer)
  - Commented-out code (version control has history)
  - Feature flags always set to one value

- **Keep names precise and self-explanatory**:
  - Rename variables/functions only if the improved name doesn't risk confusing external references
  - Check callers first before renaming exported symbols
  - Avoid ambiguous names like `data`, `temp`, `x`, `obj`

- **Keep the diff minimal and readable**:
  - Don't restyle lines you didn't need to touch
  - Avoid pure formatting churn mixed into logic changes (makes diffs harder to review)
  - One refactor goal per commit if possible

- **Add comments only where the *why* isn't obvious from the code**:
  - Good: `// Trim name before validation to handle leading spaces from copy-paste`
  - Bad: `// Validate the email` (the code already says that)
  - Avoid over-commenting obvious code

---

## Phase 4: Verify & Present Results

### Goal
Ensure behavior is preserved and present results clearly.

### Step 4A: Verification Checklist

- **Re-read the refactored file top to bottom** as if you were the reviewer, not the author.
  - Does the logic flow make sense?
  - Are variable names clear?
  - Are there any missing edge cases?

- **Trace representative inputs** (including edge cases) through both old and new logic:
  - Happy path (normal valid input)
  - Empty/null input
  - Boundary values
  - Error cases
  - Confirm both versions produce identical output for all paths

- **Run tests** if they exist:
  - If tests pass, behavior is preserved (likely)
  - If none exist and the change is non-trivial, explicitly flag this and ask the person to run their own test suite / manual checks before merging

- **Confirm the contract is unbroken**:
  - File's exports/props/return types are unchanged (unless explicitly requested)
  - Public API surface is identical
  - Function signatures match the originals
  - Error types and messages are preserved

- **Check for regressions**:
  - Does any change introduce new defensive code (try/catch, null checks) that wasn't there?
  - Does any change alter performance characteristics?
  - Are there any new dependencies introduced?

### Step 4B: Present Results

Structure your output as follows:

1. **Summary** (2-4 sentences)
   - What was simplified and the overall shape of the change
   - Example: "Removed 3 duplicated validation blocks into one helper, flattened nested conditionals in `handleSubmit`, dropped 2 unused imports and a dead feature flag branch. File reduced from 340 lines to 220."

2. **The refactored file(s)**
   - Use `str_replace`/`create_file` to actually edit files on disk (for uploaded files or repos)
   - For inline pasted code, return the refactored code in a fenced code block

3. **Change list** (bullet format)
   - Map each change to the smell it fixed
   - Helps reviewer understand and trust the diff
   - Example:
     ```
     - Extracted validateUserInput() helper (DRY: 2x usage → 1 function)
     - Replaced 4-level if nesting with guard clause (readability)
     - Removed 3 unused imports (dead code)
     - Removed try/catch wrapping Array.find() (unnecessary defensiveness)
     ```

4. **Flags** (optional — only if you have concerns)
   - Anything you noticed but deliberately did *not* change because you weren't confident it was safe
   - Example: "This duplicated block looks identical but throws a different error message on line 42 — left as-is pending confirmation it's not intentional"
   - **Never silently change behavior. When in doubt, flag it rather than fixing it.**

---

## Applying the 4-Phase Process to Multiple Files (Project-Level Refactoring)

When refactoring a full codebase (not just one file):

1. **Audit phase across all files** — Identify which files are most bloated; prioritize by size and complexity
2. **Refactor file-by-file** — Use Phases 1–4 on one file at a time
3. **Standardize patterns** — As you refactor, note patterns and ensure consistency:
   - Error handling style (try/catch vs. error boundaries vs. result types)
   - Async patterns (async/await vs. .then() — pick one)
   - Naming conventions (camelCase, snake_case, etc.)
   - Component/function structure (composition, prop shapes)
4. **Verify integration** — After refactoring a file, confirm it still works with files that import it

---

## Red Flags: When *Not* to Touch Code

- ⛔ **Magic numbers or weird conditionals** — Often fix a real bug; investigate first
- ⛔ **"Duplicate" code with slightly different error messages** — Might be intentional; check first
- ⛔ **Complex business logic you don't fully understand** — Talk to teammates or add tests first
- ⛔ **Code touching external APIs/databases** — Extra caution; test thoroughly
- ⛔ **Legacy code with fragile coupling** — Understand the entire dependency chain before refactoring

---

## Core Principles (Always Apply)

1. **Behavior preservation over cleverness** — The refactored code must do exactly what the original did
2. **No silent behavior changes** — If unsure, flag it rather than "fixing" it
3. **Read before editing** — Understand the full context before making changes
4. **One smell at a time** — Handle duplicates, then dead code, then control flow; don't mix concerns
5. **Test before merging** — Always verify behavior is preserved

---

## Language-Specific Reminders

### Python
- Use comprehensions instead of loop-building: `[x for x in items if valid(x)]`
- Use `enumerate()` instead of manual indexing
- Use walrus operator for conditional assignments: `if (data := load_data()): ...`
- Prefer `dict.get()` and defaults over repeated `if x is not None` checks
- Use context managers (`with` statements) instead of manual try/finally

### JavaScript/TypeScript
- Use optional chaining (`?.`) and nullish coalescing (`??`) to reduce defensive checks
- Use `Array.map/filter/reduce` instead of imperative loops where readable
- Prefer `async/await` over mixed `.then()` chains
- Extract repeated JSX patterns into subcomponents
- Use React hooks over class components (unless legacy compatibility required)

### React Components
- Extract repeated `useEffect`/`useState` patterns into custom hooks
- Move inline handler functions to outer scope or memoize if performance-critical
- Avoid prop drilling; use context or composition for shared state
- Consolidate prop interfaces instead of duplicating type definitions

---

## Example: Before & After

### Before (Bloated)
```javascript
function processUser(userId, email, name, role) {
  try {
    if (userId === null || userId === undefined) {
      return null;
    }
    if (userId < 0) {
      return null;
    }
    if (email === null || email === undefined) {
      return null;
    }
    if (email.includes("@") === false) {
      return null;
    }
    if (name === null || name === undefined) {
      return null;
    }
    if (name.trim() === "") {
      return null;
    }
    if (role === null || role === undefined) {
      return null;
    }
    if (["admin", "user", "guest"].includes(role) === false) {
      return null;
    }

    const user = db.getUser(userId);
    if (user === null) {
      return null;
    }

    user.email = email;
    user.name = name;
    user.role = role;
    const saved = db.saveUser(user);
    if (saved === null) {
      return null;
    }
    return saved;
  } catch (e) {
    console.error(e);
    return null;
  }
}
```

### After (Clean)
```javascript
const VALID_ROLES = ["admin", "user", "guest"];

function validateUserInput(userId, email, name, role) {
  if (!userId || userId < 0) return false;
  if (!email || !email.includes("@")) return false;
  if (!name || !name.trim()) return false;
  if (!VALID_ROLES.includes(role)) return false;
  return true;
}

function processUser(userId, email, name, role) {
  if (!validateUserInput(userId, email, name, role)) return null;

  const user = db.getUser(userId);
  if (!user) return null;

  return db.saveUser({ ...user, email, name, role });
}
```

**Changes:**
- ✅ Extracted validation logic into helper (DRY)
- ✅ Replaced repeated null checks with truthiness
- ✅ Extracted magic array to named constant
- ✅ Removed unnecessary try/catch (db calls should handle their own errors)
- ✅ Flattened guard clauses (readability)
- ✅ Used object destructuring to avoid repeated assignments
- ✅ Reduced from 35 lines to 15 lines while keeping behavior identical

---

## Never Silently Change Behavior

The golden rule: **When in doubt, flag it rather than "fixing" it.**

If you're unsure whether a refactor preserves behavior, explicitly call it out to the person. They can then decide if it's safe to proceed.