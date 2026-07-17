---
name: "Weekly LLM Market Sweep"
description: "Check all major LLM providers for new model releases, pricing changes, and cheaper/better alternatives each week. Reports actionable changes worth considering for HQ model picker or tool swaps. Use as a standing weekly intelligence routine."
metadata:
  jason:
    emoji: 📊
    activation-hints:
      - weekly LLM market sweep
      - check for new models and pricing
      - LLM landscape update
      - see what new AI models came out this week
    category: integrations
---

# Weekly LLM Market Sweep

## When to Use

Weekly market intelligence scan across all major LLM providers. Run every Sunday night / Monday morning (standing rule). Covers new model releases, price cuts, and anything worth adding to or swapping in HQ's model picker or other tools.

Activate when: the user asks for the weekly LLM sweep, it's Monday and the sweep hasn't run yet, or the user asks "anything new in LLM pricing/models this week?"

## Sources to Check

Hit these in parallel:

1. **BenchLM pricing comparison** — `https://benchlm.ai/llm-pricing` — full table of 128+ models across 12 providers with input/output/cached/batch pricing and score/$. Best single source for price movements.
2. **LLM Stats changelog** — `https://llm-stats.com/llm-updates` — new model releases and API changes. Note: JS-rendered, static fetch may miss some content.
3. **Provider-specific searches** for this week (freshness: pw):
   - "OpenAI new models pricing July 2026"
   - "Anthropic Claude new model release July 2026"
   - "Google Gemini new model July 2026"
   - "DeepSeek new model pricing July 2026"
   - Also check: Mistral, xAI/Grok, Meta Llama, Cohere
4. **OpenRouter prices** — `https://openrouter.ai/prices` — good cross-reference for multi-provider rates.

## Analysis

For each notable change, note:
- Model name + provider
- New price (input/output per million tokens)
- Score/performance tier (budget, production, frontier)
- Impact: does it replace anything in HQ's model picker? Is it worth adding?

Key tiers to watch:
- **Frontier** (score 80+): Best quality, premium pricing
- **Production** (score 70+): Good quality, reasonable price — the sweet spot
- **Budget** (score 60+): Lowest cost, usable for simple tasks

## Report Format

Present findings as a chat message with:
1. **What's new** — new model releases this week
2. **Price movements** — any cuts or increases
3. **Recommendation** — what to add/swap in HQ, and urgency (immediate / this week / no action needed)
4. **Headline** — one-line summary of whether anything changed

## SKILL COMPLETE WHEN

- [ ] All 4 source groups checked
- [ ] Findings compiled per the report format
- [ ] Report delivered in chat
- [ ] NO action items left dangling (recommendations made, urgency stated)

## Failure modes (see references/failure-modes.md)

## References
- BenchLM: https://benchlm.ai/llm-pricing
- LLM Stats: https://llm-stats.com/llm-updates
- OpenRouter: https://openrouter.ai/prices
