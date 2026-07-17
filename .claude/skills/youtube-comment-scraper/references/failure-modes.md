# YouTube Comment Scraper — Failure Modes and Recovery

## Failure Mode 1: API instance down (HTTP 502/526/403)

**Symptom**: `web_fetch` returns HTTP 502, 526, or 403 from the instance.

**Recovery**: Go back to Step 1 and check piped-instances.kavin.rocks for a different instance. As of Jul 2026, yewtu.be (Invidious) is often blocked. Piped instances at api.piped.private.coffee and api.piped.streaminfra.de have been more reliable.

## Failure Mode 2: Too few comments returned

**Symptom**: Only 5-15 comments when the commentCount field says 100+.

**Recovery**: This is expected — the Piped API returns the first page of top-level comments sorted by relevance/popularity. For comprehensive scraping you'd need the YouTube Data API with pagination. For most research (finding questions people ask), the top comments are the most useful anyway.

## Failure Mode 3: Unparseable JSON

**Symptom**: `web_fetch` returns raw HTML (often a CAPTCHA or block page) instead of JSON.

**Recovery**: The instance is blocked by YouTube. Try a different instance. If all instances fail, YouTube may have blocked the IP range — fall back to the Data API approach.

## Failure Mode 4: Comments disabled on video

**Symptom**: Response has `"disabled": true` and/or `"commentCount": -1`.

**Recovery**: Nothing to scrape. Skip this video. Check another video on the same topic.

## Failure Mode 5: Piped instances list returns empty array

**Symptom**: piped-instances.kavin.rocks returns `[]`

**Recovery**: This is rare. Try known instances directly: api.piped.private.coffee, api.piped.streaminfra.de, pipedapi.kavin.rocks (though the last has SSL issues).

## Cached Values (as of Jul 2026)

- **Instance list URL**: https://piped-instances.kavin.rocks/
- **Working instance**: https://api.piped.private.coffee
- **Thumbnail proxy**: https://proxy.piped.private.coffee
- **Comments endpoint**: GET /comments/{videoId}
- **Video ID length**: 11 characters