---
name: "Deep Niche Research"
description: "Run iterative multi-round research on a niche topic: start with broad search, drill into promising sources, then narrow with follow-up searches informed by findings. Ends with a structured workspace file synthesizing all findings with actionable takeaways. Use when the user asks to research a niche, deep-dive a topic, find experts/sources in an obscure field, or understand a domain that's poorly covered in mainstream sources."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - research [niche topic] and find [specific type of resource]
      - who are the real experts in [field]
      - deep dive on [obscure topic]
      - find tutorials/teachers for [niche craft or instrument]
      - there's not much info on [topic], dig deeper
    avoid-when:
      - User just needs a quick fact check or simple lookup (use web_search
        directly)
      - User wants to research a location or service
      - Single-round research is sufficient
    category: content
---

# Deep Niche Research

Iterative multi-round research on a niche or poorly-covered topic. Start broad, drill into promising sources, then follow threads the sources reveal. Ends with a structured workspace file.

## When to Use

Use when the user asks to research a niche topic that's poorly covered in mainstream sources — obscure instruments, traditional craft techniques, regional specialists, underground scenes, historical methods that few people teach. Also use when the first search round returns mostly shallow or wrong-audience results (e.g. non-expert tutorials, SEO spam, AI-generated content).

Avoid when:
- The user just needs a quick fact check (single web_search call is enough)
- The topic is well-covered and a single search + fetch yields sufficient depth
- The user wants location-based research (use a dedicated geo/local skill)

## How it works

A series of increasingly-tight search passes, each informed by the last:
1. **Broad pass** — search the general topic
2. **Source evaluation** — fetch promising results, identify the REAL credible sources vs. surface-level content
3. **Follow-up passes** — search on newly-discovered names, terms, techniques, historical context
4. **Gap detection** — what's missing? Are there genuine authorities who aren't teaching? Is there a market gap?
5. **Synthesis** — write everything to a structured workspace file

## Required preconditions

None, but the skill works best when the user has named a specific domain (e.g. "Jamaican percussionists teaching congas for roots reggae") rather than a vague one ("music").

## Step 1 — Initial broad search

Search the primary topic. Do not over-specific the first query — cast a wide net to see what exists.

```
web_search(query: "<broad topic> YouTube tutorial")
web_search(query: "<broad topic> lesson")
```

Review results. Look for:
- Actual practitioners vs. non-native teachers
- Community / cultural sources vs. SEO content
- Named individuals, terms, techniques to drill into
- Absences — what SHOULD exist that doesn't

## Step 2 — Follow-up passes

For each promising lead discovered in Step 1, run a targeted search. These are iterative — you may run 2-5 follow-up passes depending on what you find.

**Pattern pair: person + source type**
```
web_search(query: "<name> <craft> interview lesson tutorial")
web_search(query: "<name> teaching <specific technique>")
```

**Pattern pair: cultural/technical root**
```
web_search(query: "<indigenous/cultural term> drumming lesson YouTube")
web_search(query: "<root tradition> explained for beginners")
```

**Pattern pair: key recording as research source**
```
web_search(query: "<name> interview <craft> history")
web_search(query: "<record> <artist> percussion credits")
```

**Pattern pair: market gap**
```
web_search(query: "best <topic> online course paid")
web_search(query: "learn <topic> from <authentic source>")
```

## Step 3 — Fetch the strongest sources

Use `web_fetch` to read the most promising individual pages/articles/interviews from search results. Focus on:
- Interview transcripts (primary sources, first-person knowledge)
- Cultural/biographical articles about key figures
- Museum or institutional pages (often contain archival knowledge with no agenda)
- Documentary / festival pages

Skip:
- SEO blog posts that just aggregate other sources
- Spammy tutorial platforms
- Pages that claim to teach but clearly aren't from practitioners

## Step 4 — Gap detection

After rounds 1-3, explicitly assess:
1. Are there authentic practitioners who teach this? Where?
2. Is there a systematic educational resource (course, book, paid product) that covers it?
3. Who are the canonical names in this domain (living and deceased)?
4. Is there a market opportunity — an empty lane where nobody authentic is teaching?

This is the insight that makes the research more than a list of links. Capture it explicitly.

## Step 5 — Synthesize to workspace file

Save a structured file to `/workspace/<topic-slug>.md` with:
- **Headline finding** — one-paragraph summary of what's true about this niche
- **Tier 1 — The authentic sources** (real practitioners, cultural authorities, primary material)
- **Tier 2 — Useful secondary sources** (technically solid but non-authentic, worth knowing about)
- **Key names** — who they are, what they did, and (critically) WHY they matter
- **Practical takeaways** — actionable insights the user can apply immediately
- **Market/opportunity note** — if there's a gap the user could fill

Include inline markdown links to the source URLs for every named claim.

## Performance notes

- Search provider may surface truncated or irrelevant results for very obscure topics. If a pass returns nothing useful, rephrase using a known framework term discovered earlier.
- The barrier between Tier 1 and Tier 2 is CRITICAL for this research pattern. Getting it wrong means treating a YouTube tutorial by a non-practitioner as an authentic source. The judgment call: did this person learn from the culture/community, or from other tutorials?

## SKILL COMPLETE WHEN

- [ ] Initial broad search executed
- [ ] At least 2 follow-up search passes executed (more if warranted by discoveries)
- [ ] Strongest individual sources fetched
- [ ] Gap/market assessment made
- [ ] Workspace file written at `/workspace/<topic-slug>.md` with all 6 sections
- [ ] User told the file location and given a 3-bullet summary of findings
