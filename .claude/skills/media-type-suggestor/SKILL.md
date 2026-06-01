---
name: media-type-suggestor
description: Use when someone asks for media format recommendations, which format to use for LinkedIn, suggest media type for my post, or what media should I use for this caption.
argument-hint: "LinkedIn caption text"
disable-model-invocation: true
---

## What This Skill Does

Analyzes a LinkedIn post caption and recommends the optimal media format (Carousel, Native Video, Single Image, or Text-only) to maximize reach and engagement based on LinkedIn's algorithm preferences.

## Context

LinkedIn's algorithm prioritizes dwell time (how long users spend on your content) and engagement signals. Each media format serves different purposes:

- **PDF Carousel**: Best for educational content, step-by-step guides, listicles. High dwell time potential.
- **Native Video**: Best for personal stories, emotional content, behind-the-scenes. Builds trust and connection.
- **Single Image**: Best for announcements, statistics, quotes, quick tips. High shareability.
- **Text-only**: Works for thought leadership, hot takes, short updates. Low barrier to engagement.

## Steps

1. **Receive the caption**: Ask the user to paste their LinkedIn caption if not provided.

2. **Analyze the caption** using these criteria:

   **Educational Score** (0-10):
   - Contains step-by-step instructions? (+2)
   - Has numbered lists or bullet points? (+2)
   - Explains a concept or process? (+2)
   - Contains "how to", "tips", "ways to", "steps"? (+2)
   - Is comprehensive and detailed? (+2)

   **Emotional/Personal Score** (0-10):
   - First-person storytelling ("I", "my", "me")? (+2)
   - Contains personal challenges or struggles? (+2)
   - Uses emotional language (exciting, frustrating, amazing)? (+2)
   - Shares a journey or transformation? (+2)
   - Contains vulnerability or authenticity? (+2)

   **Announcement/Stat Score** (0-10):
   - Short and punchy (under 100 words)? (+3)
   - Contains numbers, percentages, statistics? (+2)
   - Is a bold statement or hot take? (+2)
   - Announces something new or announces? (+3)

   **Technical/Deep Score** (0-10):
   - Contains code, technical concepts? (+3)
   - Deep dive or comprehensive analysis? (+3)
   - Industry-specific expertise? (+2)
   - Data-driven insights? (+2)

3. **Calculate recommendations**:
   - If Educational Score >= 6: Recommend **PDF Carousel**
   - If Emotional/Personal Score >= 6: Recommend **Native Video** or **Personal Photo**
   - If Announcement/Stat Score >= 6 AND length < 100 words: Recommend **Single Image** or **Text-only**
   - If Technical/Deep Score >= 6: Recommend **PDF Carousel** (allows detailed code/screenshots)
   - If scores are mixed: Recommend based on highest score
   - If all scores are low (< 4): Default to **Text-only** or ask for clarification

4. **Provide the recommendation** in this format:

```
## Media Format Recommendation

**Recommended Format:** [Carousel / Native Video / Single Image / Text-only]

**Confidence:** [High / Medium / Low]

**Reasoning:**
- [Primary reason based on highest score]
- [Secondary observations]

**Why This Format:**
[Explanation of how this format serves the content and leverages LinkedIn's algorithm]

**Alternative to Consider:**
[If applicable, suggest a backup format]
```

## Notes

- Always ask for the caption if not provided. Never assume.
- If the caption is ambiguous, ask follow-up questions about the intended message.
- Consider the user's available resources (do they have video editing skills? Can they create a carousel?)
- Factor in timing: Carousels take longer to create but perform well; text-only is fastest.
- For threads or long text, recommend splitting into a Carousel instead.
- If the user wants engagement on a controversial topic, text-only often sparks discussion.
- For product launches or announcements, Single Image with a strong visual performs well.