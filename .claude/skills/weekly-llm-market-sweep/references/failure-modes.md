# Weekly LLM Market Sweep — Failure Modes

## LLM Stats page is JS-rendered
Static fetch returns limited content. The page title and meta are visible but body content may be missed. Cross-reference with BenchLM and direct searches to fill gaps.

## BenchLM page is large
~35K extracted chars. Set max_chars to at least 15000-20000 to capture the pricing table. The extracted text is a flat list of model rows — look for the score/$, price columns, and provider names.

## Web search freshness parameter needs adjusting
When searching with `freshness: pw` (past week) on Monday, results from Friday-Sunday may still be too recent for comprehensive coverage. Consider using both pw and pm (past month) to catch end-of-prior-week releases.

## No dramatic change is also valid data
Don't over-report. If nothing changed, the report should say "No new models or price changes this week" — that's a valid dispatch. Dwight doesn't need noise.

## Provider-specific: DeepSeek
DeepSeek model names include version suffixes (V4 Flash, V4 Pro, V4 Flash High). Cache pricing (marked with * or similar) may differ. Distinguish between standard and high/infrared variants.

## Provider-specific: Anthropic (Claude)
Claude models are at 200K context. Costs are always $3/$15 for Sonnet 4.5 — check for Opus pricing if a new Opus model dropped. Also check for batch pricing which is ~50% off.