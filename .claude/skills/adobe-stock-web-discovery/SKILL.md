---
name: "Adobe Stock Web Discovery"
description: "Find Adobe Stock image URLs and ftcdn.net thumbnail preview URLs when Adobe Stock's captcha (DataDome) blocks direct web_fetch access. Uses multi-round web_search to discover individual image pages indexed by search engines, then reports full URL + thumbnail or search URL as fallback. Use when the user asks to curate Adobe Stock images but you can't load stock.adobe.com due to captcha."
metadata:
  jason:
    emoji: 🔎
    activation-hints:
      - user asks to find/curate Adobe Stock images
      - user asks to search Adobe Stock
      - needs Adobe Stock thumbnails or preview URLs
      - stock.adobe.com is blocked by captcha
    avoid-when:
      - the user can browse Adobe Stock from their own browser / Mac
      - only need to know how many results exist, not individual image URLs
    category: content
---

# Adobe Stock Web Discovery

Use multi-round web search to find individual Adobe Stock image page URLs and ftcdn.net thumbnail preview URLs when Adobe Stock's DataDome captcha blocks direct web_fetch access.

## When to Use

Use this skill when the user asks you to curate, search, or find Adobe Stock images but web_fetch to stock.adobe.com returns HTTP 403 with "Please enable JS and disable any ad blocker" (DataDome captcha). This technique works when the images the user wants have been indexed by Brave/Google and you can discover their URLs through web_search.

Do NOT use this skill:
- If the user can browse Adobe Stock from their own Mac browser (much more efficient)
- If you only need result counts, not individual image page URLs
- The browser CLI tool may bypass the captcha entirely if available — try `assistant browser navigate` first

## How Adobe Stock blocks requests

- **Search pages** (stock.adobe.com/search?k=...) → All blocked by DataDome captcha (403)
- **Individual image pages** (stock.adobe.com/images/.../{id}) → Also blocked (403)
- **ftcdn.net thumbnails** (t{4}.ftcdn.net/jpg/...) → The thumbnail URL contains a random hash segment that CANNOT be derived from the image ID alone. You MUST find the ftcdn URL through web search or by loading the page.

## Step 1 — Try browser navigation first

If you have the `assistant browser` CLI tool (a real browser), try navigating to Adobe Stock that way first — it may bypass the captcha:

```
assistant browser navigate "https://stock.adobe.com/uk/search?k=YOUR+SEARCH&filters%5Bcontent_type%3Aphoto%5D=1"
```

If that works and renders the page → use browser snapshot/extract to get image URLs directly.

If browser is unavailable or also blocked → proceed with Step 2.

## Step 2 — Search for individual image pages

Use targeted web_search queries to find Adobe Stock image pages indexed by search engines. The URL pattern for individual images is:

```
https://stock.adobe.com/{lang}/images/{slug}/{numeric-id}
```

The numeric ID is usually 9-10 digits. Search for different phrasings:

```
stock.adobe.com/images {search terms}
```

**Search strategies ranked by effectiveness:**

1. **Best:** Include `/images` in the query and use the specific thing you're looking for:
   ```
   stock.adobe.com/images {object} {context} {attribute}
   ```

2. **Good:** Search with the numeric ID when the search result snippet includes it:
   ```
   "{numeric-id}" {search terms} adobe stock
   ```

3. **Fallback:** If no individual pages appear, search the search page URL (which Brave may index the title of):
   ```
   site:stock.adobe.com/search?k={keyword}
   ```
   This yields the search landing page, not individual images, but you get a link the user can click to browse manually.

> ✓ Checkpoint: Did you find at least some individual image page URLs? If yes, proceed to extract thumbnails. If not, skip to Step 5 and deliver search URLs only.

## Step 3 — Extract ftcdn thumbnails (optional, hard)

The ftcdn.net thumbnail URL format is:
```
https://t{cdn-server}.ftcdn.net/jpg/{p1}/{p2}/{p3}/360_F_{id}_{hash}.jpg
```

Where:
- `cdn-server` is typically `3` or `4`
- `p1`, `p2`, `p3` are the image ID split into roughly 2-digit segments
- `hash` is a random-looking alphanumeric string

**The hash CANNOT be computed from the ID alone.** The only ways to find the ftcdn URL:
- ❌ Constructing from the ID (the path segments DO NOT map predictably — "360_F_2073467340" is NOT the same as the path segments)
- ✅ Discovering it through web search
- ✅ Loading the actual image page (blocked)
- ✅ Loading the ftcdn URL directly with a guessed path (almost always 404)

To search for already-indexed ftcdn thumbnails:
```
"360_F_" {search terms} ftcdn.net jpg
```
This is very unlikely to work — ftcdn URLs are rarely indexed by search engines.

> ✓ Checkpoint: Could not find ftcdn thumbnails → proceed to Step 4 (deliver what you have).

## Step 4 — Build fallback search URLs

If you couldn't find enough individual image pages, build pre-filtered Adobe Stock search URLs for the user to browse manually from their Mac. The pattern is:

```
https://stock.adobe.com/uk/search?k={url-encoded-keywords}&filters%5Bcontent_type%3Aphoto%5D=1&safe_search=1
```

Build searches for each variation of the user's request (e.g. different body parts, angles, settings).

## Step 5 — Deliver the results

Present as a markdown list. For each image you found:
```markdown
{number}. **{title/description}** — {brief context}
   - https://stock.adobe.com/{lang}/images/{slug}/{id}
   - ![preview](https://t{cdn}.ftcdn.net/jpg/{path}/360_F_{id}_{hash}.jpg)  *(include if found)*
```

For search URLs the user can browse manually:
```markdown
{number}. **{search term}** (N results) — {description}
   - https://stock.adobe.com/uk/search?k=...
```

## Failure modes

- **ftcdn thumbnails:** Almost never discoverable through web search alone. The hash is random and not indexed. Accept this limitation.
- **Fewer individual images than requested:** Search engines index only a tiny fraction of Adobe Stock's library. You may only find 3-6 individual pages from Brave for niche searches. Supplement with search URLs.
- **No individual pages at all:** For very specific product terms (e.g. "foam roller back recovery"), Brave returns only result pages, never individual images. Fall back entirely to search URLs.
- **Alternative stock sites in results:** Brave heavily prefers DepositPhotos, iStock, Shutterstock, Dreamstime, and Getty over Adobe Stock. You may need many search rounds to find Adobe Stock specifically.

## SKILL COMPLETE WHEN

- [ ] For each discovered individual image: delivered its full Adobe Stock URL + ftcdn thumbnail URL (if found)
- [ ] For the remainder: delivered pre-filtered search URLs for manual browsing
- [ ] Explained to the user that the DataDome captcha prevented deeper access
- [ ] Recommended the user browse from their own Adobe CC Pro account on Mac
