# Issues & TODOs Tracker

**Purpose:** Centralized list of bugs, technical debt, and blockers.  
**Updated:** At least weekly or when issues are discovered.  
**Used by:** Team for prioritization, Claude Code for understanding what needs work.

---

## 🔴 Critical Blockers (Blocks Everything)

### Issue #[ID]: [Clear, Specific Title]

**Severity:** 🔴 Critical  
**Status:** 🆕 New | 🔄 In Progress | 🟡 Blocked | ✅ Resolved  
**Assigned To:** [Name or "Unassigned"]  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD  
**Target Fix:** YYYY-MM-DD

---

**Description:**
```
What's broken or blocked? Be specific and concrete.

Example:
"Data parser fails when processing CSV files with non-UTF-8 
characters (e.g., accented letters é, ñ). Affects 15% of test 
data. Errors out with UnicodeDecodeError instead of graceful 
fallback."
```

**Root Cause (if known):**
```
Why is this happening?

Example:
"Parser uses Python's default UTF-8 encoding without fallback. 
Need to implement encoding detection or accept multiple encodings."
```

**Impact:**
```
Who/what is affected? How severely?

Example:
"Blocks completing email campaign feature for Spanish/French 
language support. Affects go-live date by X weeks."
```

**Workaround (if available):**
```
Temporary solution to unblock progress.

Example:
"Use ASCII-only characters in test data for now. Pre-filter 
data to remove accented characters before processing."
```

**Files Involved:**
- `src/parser.py` (line 45-67)
- `tests/test_parser.py`

**Steps to Reproduce:**
```
1. Load CSV file with accented characters
2. Call parser.parse(file_path)
3. Observe: UnicodeDecodeError
```

**Acceptance Criteria (to mark as resolved):**
- [ ] Parser accepts UTF-8 and ISO-8859-1 encodings
- [ ] Falls back gracefully on unsupported encoding
- [ ] Logs encoding detection attempt
- [ ] All tests pass including edge cases
- [ ] Documentation updated

**Attempted Solutions:**
- ❌ Attempt 1: [What didn't work and why]
- ❌ Attempt 2: [What didn't work and why]
- 🔄 Attempt 3: [What we're trying now]

**Next Steps:**
1. Research Python encoding handling options
2. Implement encoding detection
3. Add test cases for edge encodings
4. Update documentation

**Related Issues:**
- Relates to: Issue #X [How they're connected]
- Blocks: Issue #Y [What this blocks]
- Blocked by: Issue #Z [What blocks this]

---

### Issue #[ID]: [Another Critical Issue]

**Severity:** 🔴 Critical  
**Status:** 🔄 In Progress  
**Assigned To:** [Name]  
**Created:** YYYY-MM-DD  
**Target Fix:** YYYY-MM-DD

[Use same template as above]

---

---

## 🟡 Medium Priority (Slows Progress)

### Issue #[ID]: [Title]

**Severity:** 🟡 Medium  
**Status:** 🆕 New  
**Assigned To:** [Name or "Unassigned"]  
**Created:** YYYY-MM-DD

**Description:** [What's the problem?]

**Impact:** [How does it affect us?]

**Workaround:** [Can we work around it?]

**Files Involved:** [Which files?]

**To Fix:** [What needs to be done?]

---

### Issue #[ID]: [Title]

**Severity:** 🟡 Medium  
**Status:** 🆕 New  
**Assigned To:** [Name or "Unassigned"]  
**Created:** YYYY-MM-DD

[Use template above]

---

---

## 🟢 Low Priority (Minor Friction)

These are nice-to-haves that don't block progress.

### Issue #[ID]: [Title]

**Severity:** 🟢 Low  
**Status:** 🆕 New  
**Assigned To:** [Name or "Unassigned"]  
**Created:** YYYY-MM-DD

**Description:** [What could be better?]

**Impact:** [Development speed, code clarity, etc.]

**Effort:** Small | Medium | Large

**Nice to Have:** [Why include this?]

---

---

## 📋 Technical Debt

### Debt #[ID]: [Title]

**Severity:** 🟡 Medium  
**Type:** Code | Test | Documentation | Infrastructure  
**Created:** YYYY-MM-DD  
**Accrued Cost:** ~X hours per month

**Description:**
```
What shortcuts did we take?

Example:
"Hardcoded configuration values in 5 different files instead 
of using centralized config. Takes ~5 minutes to update settings 
across codebase."
```

**Why We Took This Shortcut:**
```
We needed to move fast, and this wasn't critical initially.

Example:
"Initial implementation needed to be fast. We knew configuration 
management was important but wanted to prove core concept first."
```

**Refactoring Plan:**
```
How to pay down this debt?

Example:
"1. Create config module
2. Move all hardcoded values to config
3. Update all references
4. Document configuration system
5. Add validation"
```

**Estimated Effort:** X hours

---

### Debt #[ID]: [Another Example]

**Severity:** 🟡 Medium  
**Type:** Test  
**Created:** YYYY-MM-DD  
**Accrued Cost:** ~X hours per month

[Follow template above]

---

---

## 🚀 TODOs & Enhancements

### TODO #[ID]: [Title]

**Type:** Feature | Enhancement | Improvement | Refactoring  
**Priority:** 1 | 2 | 3 (lower number = higher priority)  
**Assigned To:** [Name or "Unassigned"]  
**Created:** YYYY-MM-DD  
**Target:** YYYY-MM-DD

**Description:**
```
What should we implement?

Example:
"Add caching layer to avoid repeated API calls. Implement 
Redis-based cache with configurable TTL. Should support 
cache invalidation via webhook."
```

**Why This Matters:**
```
What problem does it solve?

Example:
"Current implementation calls external API for every request. 
With 100 requests/second, this causes rate limiting. Caching 
would reduce by 70% based on analysis."
```

**Acceptance Criteria:**
- [ ] Feature A is implemented
- [ ] Performance improves by X%
- [ ] Tests cover happy path + edge cases
- [ ] Documentation updated

**Estimated Effort:** Small | Medium | Large (~X hours)

**Blockers:** [What needs to happen first?]

**Files to Change:** [Approximate affected files]

---

### TODO #[ID]: [Another Enhancement]

**Type:** Feature  
**Priority:** 2  
**Assigned To:** [Name]  
**Created:** YYYY-MM-DD

[Follow template above]

---

---

## 🐛 Known Limitations

### Limitation #[ID]: [Clear Description]

**Impact:** [How does it affect users?]

**Workaround:**
```
How can people work around this?

Example:
"Use ASCII characters only in names. Avoid special characters 
and non-Latin scripts."
```

**Root Cause:**
```
Why does this exist?

Example:
"Legacy parser was designed for ASCII text only. Updating to 
Unicode support was deferred to focus on core functionality."
```

**Fix Timeline:** [When might this be fixed, if ever?]

**Affects:** [Who notices this issue?]

---

### Limitation #[ID]: [Another Limitation]

**Impact:** [How does it affect users?]

**Workaround:** [Temporary solution]

**Root Cause:** [Why it exists]

**Fix Timeline:** [When might it be fixed?]

---

---

## 📊 Issue Summary Statistics

### By Severity
```
🔴 Critical:     X issues (blocks progress)
🟡 Medium:       X issues (slows progress)
🟢 Low:          X issues (minor friction)
───────────────────────
Total:           X issues
```

### By Status
```
🆕 New:          X issues (not started)
🔄 In Progress:  X issues (being worked on)
🟡 Blocked:      X issues (waiting on something)
✅ Resolved:     X issues (fixed this month)
───────────────────────
Total Open:      X issues
```

### By Type
```
🐛 Bugs:         X issues
📋 TODOs:        X issues
💰 Tech Debt:    X issues
📉 Limitations:  X issues
```

### Trend
```
Last week:  X open issues
This week:  Y open issues
Change:     +Z or -Z
```

---

## 🎯 Prioritization Matrix

| Issue | Impact | Effort | Priority | Status |
|-------|--------|--------|----------|--------|
| #X: [Title] | High | Low | 🔴 Critical | 🔄 In Progress |
| #Y: [Title] | High | High | 🟡 Medium | 🆕 New |
| #Z: [Title] | Low | Small | 🟢 Low | 🆕 New |

**Priority Decision Framework:**
- **Impact × (1/Effort) = Priority Score**
- High impact, low effort = Do first
- High impact, high effort = Plan for future
- Low impact, low effort = Do when convenient
- Low impact, high effort = Defer or drop

---

## 🔗 Related Issues

### Issue Dependencies

```
Issue #5 (Blocker)
  └─→ Issue #12 (Blocked)
      └─→ Issue #18 (Blocked)

Issue #7 (Relates to)
  └─→ Issue #9 (Same root cause)
```

### Issues to Track Together

- Issues #3 & #8: Both related to parser performance
- Issues #11, #14, #22: Part of "API refactoring" epic

---

## ✅ Resolution Log

### Recently Resolved

**Issue #[ID]: [Title]**
- Resolved: YYYY-MM-DD
- Resolution: [How it was fixed]
- Lessons Learned: [What we learned]

**Issue #[ID]: [Title]**
- Resolved: YYYY-MM-DD
- Resolution: [How it was fixed]
- Lessons Learned: [What we learned]

---

## 📈 Health Metrics

### This Month
```
Issues Created:     X
Issues Resolved:    Y
Issues Still Open:  Z

Velocity:  ~X issues/week
Backlog:   ~X weeks of work
```

### Trend Analysis
```
Critical Issues:  Were 5, now 2 ✅ (improving)
Medium Issues:    Were 8, now 12 ⚠️ (accumulating)
Low Issues:       Were 20, now 18 ✅ (improving)
```

---

## 🚨 Action Items This Week

**High Priority:**
- [ ] Start work on Issue #X (assign to [name])
- [ ] Unblock Issue #Y (depends on [issue])
- [ ] Investigate Issue #Z (unknown severity)

**This Sprint:**
- [ ] Complete Issue #A
- [ ] Complete Issue #B
- [ ] Review and prioritize new issues

---

## 📝 How to Use This Document

### When Finding a Bug
1. Check if similar issue already exists
2. Add new issue with "🆕 New" status
3. Fill out Description, Impact, Reproduction steps
4. Note any workarounds
5. Add labels (Critical/Medium/Low)

### When Starting Work
1. Find unstarred issue that's not assigned
2. Assign to yourself
3. Change status to "🔄 In Progress"
4. Update regularly with progress

### When Completing Work
1. Verify against Acceptance Criteria
2. Update status to "✅ Resolved"
3. Add resolution details
4. Link to pull request
5. Document any lessons learned

### When Reviewing Progress
1. Count open issues by severity
2. Check blocked issues (unblock them!)
3. Verify priority order matches impact
4. Move completed issues to archive

---

## 🔄 Maintenance Schedule

**Weekly:**
- [ ] Update status on in-progress issues
- [ ] Move completed issues to Resolved
- [ ] Check for blocked issues (unblock if possible)

**Monthly:**
- [ ] Review and prioritize new issues
- [ ] Assess technical debt accrual
- [ ] Archive resolved issues (move to separate section)
- [ ] Update health metrics

**Quarterly:**
- [ ] Review technical debt strategy
- [ ] Plan major refactorings
- [ ] Assess if architecture decisions contributed to current issues

---

## 📚 Related Documents

- **Project State:** `.claude/memory/project_state.json` (shows blockers)
- **Architecture:** `.claude/docs/ARCHITECTURE.md` (may explain limitations)
- **Decisions:** `.claude/memory/decision_log.md` (decisions that may have created debt)
- **Progress:** `.claude/memory/progress.md` (shows what's been completed)

---

**Last Updated:** YYYY-MM-DD  
**Maintained By:** [Your Name/Team]  
**Review Frequency:** Weekly minimum, daily during active development
