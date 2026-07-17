---
name: "YouTube Comment Scraper"
description: "Scrape YouTube video comments using Piped alternative frontend API — no API key, no OAuth, no JS rendering needed. Use when you need to extract viewer comments from YouTube videos but the page is JS-rendered and static web_fetch only returns boilerplate HTML. Works for extracting questions, feedback, sentiment, or any comment data from any public YouTube video."
metadata:
  jason:
    emoji: 💬
    activation-hints:
      - need to scrape youtube comments
      - extract comments from video
      - what are people saying about
      - youtube comment analysis
      - viewer questions from video
      - scrape youtube without api key
      - find questions people ask in youtube comments
    avoid-when:
      - need real-time comment counts (use YouTube Data API instead)
      - need to post/reply to comments (read-only only)
      - need comment replies/threads beyond top-level (not supported)
    category: content
---

# YouTube Comment Scraper (via Piped API)

Scrape YouTube video comments using the Piped alternative frontend API — no API key, no OAuth, no JS rendering. Works because Piped renders YouTube content server-side and exposes comments as JSON.

## When to Use

Use when you need to extract viewer comments from YouTube videos — for research, question extraction, sentiment analysis, or competitor analysis — but the YouTube page is JS-rendered and `web_fetch` returns only boilerplate HTML. This skill uses the Piped API (a libre YouTube frontend) to fetch comments as structured JSON.

## Step 1 — Find a working Piped API instance

Piped instances are listed at https://piped-instances.kavin.rocks/ (returns JSON). Call `web_fetch` on this URL to get the latest list. Each entry contains:

- `name`: instance name
- `api_url`: the API base URL (e.g. `https://api.piped.private.coffee`)
- `up_to_date`: boolean — prefer `true`
- `uptime_24h`: uptime percentage — prefer >= 99%

```
web_fetch("https://piped-instances.kavin.rocks/")
```

Pick the first instance that is up-to-date and has high uptime. As of Jul 2026, `api.piped.private.coffee` works reliably.

## Step 2 — Fetch comments for a video

Call the comments endpoint on your chosen API instance:

```
web_fetch(f"{api_url}/comments/{videoId}")
```

Where `videoId` is the 11-character YouTube video ID (e.g. `9vkgG13ooMY` from `https://www.youtube.com/watch?v=9vkgG13ooMY`).

**Set `max_chars` high enough to capture all returned comments** — the JSON can be 10-15KB per page. 40000 is a safe default.

## Step 3 — Parse the JSON response

The response uses this shape:

```json
{
  "comments": [
    {
      "author": "@username",
      "commentId": "Ugx...",
      "commentText": "The comment text",
      "commentedTime": "2 years ago",
      "commentorUrl": "/channel/...",
      "likeCount": 5,
      "replyCount": 0,
      "hearted": false,
      "pinned": false,
      "repliesPage": null
    }
  ],
  "nextpage": "...",  // pagination token if more comments exist
  "disabled": false,
  "commentCount": 196
}
```

Key fields:
- `commentText` — the actual comment text (HTML-escaped, may contain `<br>` tags)
- `author` — the commenter's @ handle
- `likeCount` — number of likes
- `replyCount` — number of replies
- `hearted` — whether the creator hearted it
- `pinned` — whether it's pinned
- `replyCount` > 0 — this comment has replies, but reply content requires fetching a separate `repliesPage` URL

## Step 4 — Handle pagination (optional)

If the response includes `nextpage`, you can fetch the next page by passing the same video ID to get more comments. The `nextpage` value is an encoded continuation string, so the simplest approach is:

```
web_fetch(f"{api_url}/comments/{videoId}")
```

This returns the first page (top ~20 most popular comments). For high-comment videos (100+), you'll only get the first page — the free API doesn't expose full pagination simply. This is usually sufficient for research.

## Step 5 — Extract questions from comments

Once you have the JSON, pass the `commentText` values through text analysis to identify questions. Use the `analyze_query` tool or manual text scanning for phrases like:

- "how do you/1/I"
- "why does my"
- "what's the"
- "can you/could you"
- "I can't get my"
- "how do I make"
- "what software"
- "where can I find"
- Ending with "?"

## Known Issues and Gotchas

1. **Comments may be disabled**: Response has `"disabled": true` and `"commentCount": -1` — check for this before processing.
2. **Only top-level comments**: The API returns top-level comments, not replies. Reply content requires fetching the `repliesPage` URL which is complex (base64-encoded continuation data). For most research, top-level comments suffice.
3. **Unavailable instances**: Piped instances get blocked by YouTube periodically. Always check the instance list at Step 1 before relying on one. Have a fallback plan (use YouTube Data API with an API key as alternative).
4. **Rate limiting**: The free API has no documented rate limit but be respectful — don't hammer it.
5. **Content encoding**: HTML entities in `commentText` (`&apos;`, `&lt;`, `&gt;`, `&quot;`, `&amp;`, `<br>`) need decoding for clean text.
6. **The instance list itself at piped-instances.kavin.rocks may only return 1-3 working instances** — this is normal. Pick the best one.

## SKILL COMPLETE WHEN

- [ ] `web_fetch` returned valid JSON with a `comments` array
- [ ] Comments were extracted and the relevant data (questions, feedback, etc.) saved to a workspace file
- [ ] User has been shown the results

## Alternative: YouTube Data API (when Piped fails)

If no Piped instance works, fall back to the official YouTube Data API:

```
GET https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={VIDEO_ID}&key={API_KEY}&maxResults=100
```

This requires an API key from Google Cloud Console and has quota limits (10,000 units/day, ~100 comments per request).
