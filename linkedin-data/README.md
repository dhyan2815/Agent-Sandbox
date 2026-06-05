# LinkedIn Data Cache Notes

## What this contains
- `Dhyan-all-posts.json`: starter dataset built from public snippets of `https://www.linkedin.com/in/dhyan2815/`.

## Why this is a starter set
This file is not a full export of your last 100 posts. It is a partial cache from publicly indexed profile snippets and is useful for immediate scoring setup only.

## How to refresh for accurate scoring
1. Run `post-scorer` and choose `Scrape my posts`.
2. Use LinkedIn username: `dhyan2815`.
3. Pull 100 posts via Apify actor `apimaestro/linkedin-profile-posts`.
4. Save output as `Dhyan-all-posts.json` in the `linkedin-data` directory (or `[username]-all-posts.json` in the project root).
5. Keep `total_reactions` and `comments` fields intact so engagement scoring works.
