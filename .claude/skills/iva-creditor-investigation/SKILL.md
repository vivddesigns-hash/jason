---
name: "IVA Creditor Investigation"
description: "Investigate whether a specific debt or creditor was included in a user's IVA by searching Gmail for creditor correspondence, IVA approval dates, breathing space records, and debt collector emails. Correlate debt dates against IVA approval date. Draft dual notification emails to the IVA provider and debt collector."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - check if [creditor/company] is in my IVA
      - is [creditor/company] included in my debt solution
      - investigate whether a debt was included in my IVA
      - a debt collector is chasing me for a debt that should be in my IVA
    avoid-when:
      - setting up a new IVA or debt solution
      - general email decluttering unrelated to debt investigation
    category: productivity
---

# IVA Creditor Investigation

Investigate whether a specific debt was included in a user's IVA by cross-referencing creditor correspondence, breathing space records, debt collector emails, and IVA approval dates. Draft dual emails to the IP and the debt collector.

## When to Use

Use this skill when the user:
- Asks if a specific creditor/company is in their IVA or debt solution
- Says a debt collector is chasing them for something that should be covered by their IVA
- Wants to verify whether a pre-IVA debt was included in their creditor list
- Asks you to "check" or "look into" whether a particular debt is part of their IVA

## Available Tools

You'll need:
- `messaging_search` (from the `messaging` skill — load it first) — search Gmail with keywords like `"from:mydesbtplaniva.hubsolv.com"`, `"creditor list"`, `"chairman"`, `"approved"`, `"IVA"`, `"breathing space"`, plus the specific creditor and any known debt collector names
- `messaging_read` — read conversation threads to get full email content (including attachments metadata)
- `web_search` / `web_fetch` — find contact details for debt collectors (they often use noreply@ addresses with no reply-to)

## Procedure

### Step 1 — Gather IVA timeline evidence

Search for:
1. IVA application / approval emails from the IVA provider (e.g. `from:mydebtplaniva.hubsolv.com` with terms like `approved`, `chairman`, `meeting of creditors`)
2. Breathing space or debt advice session records (these list included creditors)
3. Any email from the user to their IVA provider with subject `creditors` or requesting a creditor list
4. The IVA ref number (usually found in email subjects like `[1538748114/45]`)

**Key dates to extract:**
- IVA approval date
- The debt's origination date (from the creditor's invoice or final notice)
- Breathing space dates (usually 60 days)

### Step 2 — Gather creditor correspondence

Search for all emails from:
1. The specific creditor named by the user
2. Any debt collectors chasing the debt (try variations like `subject:(creditor OR "collector name") (collection OR collector OR debt OR final notice OR arrears)`)
3. The creditor's final demand / threat of debt collection

**Extract:** the outstanding amount, reference numbers, dates, and which company is collecting.

### Step 3 — Correlate dates and determine coverage

The rule (from My Debt Plan confirmed in practice): **Any debt accrued before the approval of the IVA must be included.**

- If debt date < IVA approval date → should be in the IVA
- If not in breathing space list and not in IVA modifications → it was likely missed

### Step 4 — Draft notification emails

Draft **two emails** (do not send without approval):

**Email 1: To the IVA provider**
- Address the user's IP contact
- Request the debt be added to the creditor list
- Include: debt amount, reference numbers, purchase/origination date, name of debt collector
- Ask them to confirm the total outstanding (including any collector-added charges)

**Email 2: To the debt collector**
- Notify them of the active IVA
- Provide the IP's contact details (phone, WhatsApp, ref number)
- Ask them to direct all future queries to the IP
- Ask them to confirm the total outstanding balance including any charges

### Step 5 — Surface for approval

Show both drafts in chat before sending. Do not send without explicit user confirmation.

## Failure Modes

- Debt collectors often use `noreply@` addresses — their contact info may only be findable via web search or the self-service portal on their website
- The IVA provider's chairman's report may be sent as an attachment (PDF) that can't be read inline — look for the email mentioning it and surface that to the user
- Multiple IVA ref numbers may exist — use the one most consistently referenced in recent correspondence

## SKILL COMPLETE WHEN

- [ ] Gmail searched for IVA approval date, breathing space, creditor correspondence
- [ ] Debt date compared against IVA approval date
- [ ] Conclusion determined (included or not included)
- [ ] Two drafts written and surfaced in chat
- [ ] User given option to approve sending
