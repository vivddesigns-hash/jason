# Failure modes observed in practice

## Source staleness
- **Third-party aggregators** (e.g. aifreeapi.com, tokenmix.ai, tinkerllm.com) often disagree with each other and with Google's official page. Their data can be days or months old.
- **Google's official page** is more reliable but the "Specified rate limits are not guaranteed and actual capacity may vary" disclaimer means even official numbers can be stale.
- **Live AI Studio dashboard** is the ground truth for rate limits — but requires a logged-in session we can't automate.
- **Mitigation:** Fetch the official pricing page first. If the official page is vague ("view in AI Studio"), supplement with web search but cite recency explicitly. Flag any numbers derived from third-party sources vs official ones.

## ToS contradictions
- Third-party sources sometimes claim "free tier excludes commercial use" when the actual ToS only restricts UK/EEA user-facing apps. Always read the actual ToS before citing restrictions.
- Different sections of the same ToS can contradict each other. Read the full Terms page, not just the pricing page.
- **Mitigation:** Always fetch the official ToS page. Quote verbatim the relevant clause rather than paraphrasing.

## Rate limit instability
- Google reduced free tier quotas 50-80% on Dec 7, 2025 without notice. They can do it again.
- Rate limits apply per *project* (not per API key). Creating more API keys does not increase quota.
- **Mitigation:** Always note that free tier limits can change without notice. Don't promise freeze-tier stability. Add a recommendation for when to upgrade.

## Modality-dependent costs
- Audio tokens cost 3-10x more than text tokens on most models.
- Image and video input consumes tokens proportional to resolution/duration.
- Grounding with Google Search costs per search query, not per API call. One prompt may trigger multiple search queries.
- **Mitigation:** Check separate pricing rows for audio/video/image modalities. Don't assume text-only pricing applies.

## UK/EEA legal trap
- The Gemini API Additional Terms explicitly require Paid Services for API Clients available to users in EEA, Switzerland, or the UK. This is the most common blind spot — many developers assume free tier is fine for low-volume UK apps.
- **Mitigation:** Always check the Use Restrictions clause of the ToS for geographic restrictions.
