---
name: "API Pricing & ToS Research"
description: "Deep-research a cloud/API provider's pricing, free tier limits, rate limits, and terms of service for a specific use case. Fetches official pricing page, rate limits, and terms of service, cross-references against the user's actual use case, and returns a structured report with actionable recommendations. Use when the user asks whether they can use a provider's free tier, what limits apply, whether it's legal for production use, or how much a given integration would cost."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - research a provider's pricing and free tier
      - find out if I can use X's free tier for my app
      - what are the rate limits for Y
      - check if Z's free tier allows commercial use
      - how much would it cost to use X for my use case
      - does Y allow production use on the free tier
      - evaluate whether free tier is viable for my integration
    avoid-when:
      - weekly scheduled market sweeps (use weekly-llm-market-sweep instead)
      - general web searching not about API pricing/TOS
      - setting up an integration (use the provider's setup skill if one exists)
    category: productivity
---

## When to Use

Research a provider's API pricing, free tier, rate limits, and terms of service to answer a concrete question like:
- "Can I use [provider X]'s free tier for my app?"
- "What are Gemini 2.5 Flash's rate limits on the free tier?"
- "Does [provider Y] allow production use on the free plan?"
- "How much would it cost to run my integration on the paid tier?"

The user has a specific use case (model, volume, region, user-facing or not). Your job is to map the provider's published terms and limits to that use case and give a clear yes/no/contingent answer.

## What you need from context

Before starting, identify from your context:
- **Provider and specific model(s)** of interest (e.g. "Google Gemini 2.5 Flash")
- **User's use case** (e.g. "Calmcierge chatbot on the Calm Desk website, serving UK users")
- **User's region** — critical for geographic ToS restrictions
- **Expected volume** if known (requests/day, tokens/day)
- **Whether users will interact with it** (user-facing app vs internal tool)

If any of this is unclear from context, re-check the user's project memory or ask before researching.

## Step 1 — Fetch the official pricing page

`web_fetch` the provider's official pricing URL. This is always the first source — not a third-party aggregator.

Look for:
- The pricing table (free tier vs paid per-token/per-request pricing)
- Which models are available on the free tier
- Features included/excluded on free tier (context caching, batch, etc.)
- Any mention of data policy ("used to improve our products")

**How to find the URL:** If unsure of the exact pricing URL, `web_search` for "{provider} API pricing" and take the official domain link (not a blog, aggregator, or third-party guide).

> Checkpoint: Did you find a clear pricing table? If the page says "view in dashboard" or gives ranges instead of exact numbers, note this and proceed — the dashboard access is a separate limitation.

## Step 2 — Fetch the rate limits page

If the provider has a separate rate limits page, `web_fetch` that too. Cross-reference against the pricing table — sometimes they list different numbers.

Look for:
- RPM (requests per minute)
- RPD (requests per day) or RPH (requests per hour)
- TPM (tokens per minute) or TPD (tokens per day)
- Whether limits vary by model
- Whether limits are per project or per API key

> Checkpoint: Note any discrepancies between the pricing page and the rate limits page. If the rate limits page refers to a dashboard for exact numbers, flag that they're a rough guide.

## Step 3 — Fetch the Terms of Service

This is the most skipped step and the most dangerous to skip. `web_fetch` the provider's API ToS page.

⚠️ CRITICAL: Do not rely on third-party summaries of ToS. Third-party sources often simplify or get the commercial-use restrictions wrong (e.g. claiming "free tier excludes commercial use" when the actual ToS only restricts UK/EEA user-facing apps). Read the actual ToS.

Look for:
- **Use Restrictions** section — are there geographic restrictions? (EEA/UK users requiring paid tier?)
- **Unpaid Services / Free tier** section — what does Google/etc. do with your data?
- **Paid Services** section — does data handling change?
- **Commercial use** — is it explicitly allowed or restricted?
- **Output ownership** — who owns the generated content?

If → the ToS mentions different regional rules (EEA, UK, Switzerland) → quote the exact clause and note it in your report.
If → no geographic restrictions found → note that explicitly.

## Step 4 — Search for third-party confirmation (only if needed)

Only reach for web searches when:
- The official page refers to a dashboard for exact limits (e.g. "view in AI Studio")
- The official page is vague about specific RPD/RPM numbers
- The pricing page doesn't mention a specific model you're researching

When you do search, cite recency explicitly: "Per [source name] (as of March 2026)". Cross-reference multiple sources and note disagreements.

## Step 5 — Map findings to the user's use case

Now answer the specific questions:

1. **Can they use the free tier?** (legal answer, not just technical)
   - Does the ToS allow their region? (UK/EEA is a common blocker)
   - Is it a user-facing app or internal tool?
   - Does the data-sharing policy conflict with their users' privacy expectations?

2. **Would their usage fit within free tier limits?** (technical answer)
   - Estimate their requests/day based on context
   - Check against RPM (burst) and RPD (volume) limits
   - Flag if they're close to the ceiling
   - Note that limits can change without notice (Google proved this Dec 2025)

3. **What does switching to paid cost?** (financial answer)
   - Per-token pricing for their model
   - Monthly projection at their estimated usage
   - Any minimum spend or billing requirements
   - What unlocks (higher rate limits, no data training, context caching, etc.)

## Step 6 — Deliver a structured report

Present the findings in clear sections:

### Free Tier Summary
- Models available, rate limits, included/excluded features

### Legal / ToS Check
- Geographic restrictions that apply to the user
- Data policy (does the provider train on free tier data?)
- Verdict: legally allowed or not for their use case

### Cost Projection
- Estimated monthly cost on paid tier at their usage
- Comparison of free vs paid tier differences

### Recommendation
- Stay on free / Upgrade to Tier 1 / Go to higher tier
- Explicit reasoning

### Sources cited inline
- Hyperlink each claim to its source. E.g. "Per [Gemini API Pricing page](url), 2.5 Flash Standard input costs $0.30/1M tokens on the paid tier."

## SKILL COMPLETE WHEN

- [ ] `web_fetch` called on the official pricing page
- [ ] `web_fetch` called on the rate limits page (if separate)
- [ ] `web_fetch` called on the official ToS page
- [ ] `web_search` called (if needed for missing limits)
- [ ] Findings mapped to user's specific use case
- [ ] Structured report delivered with inline citations and a clear recommendation
