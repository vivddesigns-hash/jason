---
name: "Draft Emergent Build Prompt"
description: "Draft a comprehensive build prompt for the Emergent AI agent platform — read context files and existing architecture, write a structured prompt with clear feature specs, tech requirements, integration points, and acceptance criteria, then deliver as a copy block for the user to paste into Emergent's builder chat."
metadata:
  jason:
    emoji: 🏗️
    activation-hints:
      - draft an emergent prompt
      - write a build prompt for emergent
      - need a prompt for the agent
      - create a build spec for emergent
    avoid-when:
      - user wants to paste the prompt themselves and just needs it written quickly
      - user wants to drive the build through ACP/Codex instead of Emergent
      - user is asking for a code review or QA audit, not a build
    category: development
---

# Draft Emergent Build Prompt

## When to Use

The user needs a feature built on one of their Emergent-hosted apps (Content CoPilot, Ashlan beta site, OpenWord/KFM, Calm Desk, HQ) and wants a comprehensive prompt ready to paste into the Emergent builder chat. You've already gathered the requirements through conversation and need to turn them into a structured, copy-paste-ready build prompt.

Do NOT use this when the user wants to drive the build through ACP/Codex instead of Emergent, or when they're asking for a code review/QA audit of an existing build.

## Prerequisites

Before drafting, ensure you have:

- Read the relevant memory/concepts/*.md files for the app being built (e.g. content-pilot-25.md, ashlan-beta-site.md, kfm.md, calm-desk.md)
- Read any existing build prompts or feature specs in /workspace/*.md that cover the same app
- Read the app's brand identity file if one exists (especially for Content CoPilot/Ashlan — ashlan-brand-identity.md)
- Confirmed with Dwight which app's Emergent chat this goes into (each app has its own Emergent conversation)
- Confirmed whether builds go to preview only (yes, Dwight deploys) or can deploy to production
- Confirmed what external API keys or credentials are needed, and whether Dwight has them

## Step 1 — Read existing architecture and context

Read the relevant memory files and any existing prompts/specs for the app. You need to understand:
- What the app already has built (don't suggest rebuilding existing features)
- The tech stack (React, shadcn, HTML5 Canvas, Clerk org roles, etc.)
- The brand/style (ALL-LIGHT Ashlan aesthetic, Montserrat font, teal palette #5FA8B4, no dark mode)
- The role/permission model (admin/editor vs member/approver)
- The governance model (AI creates → human approves via "Needs review" lane)
- What existing patterns the new feature should follow (modal patterns, API patterns, integration points)

## Step 2 — Draft the prompt

Write to /workspace/content-copilot-p{phase}-{feature-name}-prompt.md (for CC) or /workspace/ashlan-{app}-{feature}-prompt.md (for other apps).

The prompt structure:

```markdown
# [App Name] — [Feature Name] ([Date])

**Paste into the Emergent builder chat for [app-specific URL or name].**

---

Build [feature description]. This follows [previous feature, link to it].

## What to build

### 1. [Component/Feature 1]

[Clear description of what it is, the user flow step by step, visual details]

**Flow:**
1. User does X → Y happens
2. [Continue flow...]

[Specs: dropdown options, format constraints, color codes, character limits, etc.]

[Tech requirements: component names, API endpoints, file locations, libraries]

### 2. [Component/Feature 2 - if multiple]

[...same pattern...]

### 3. Integration points

- **[App feature]:** how this wires in
- **[Other feature]:** how this wires in

## Tech requirements

- **Framework:** [React component, Canvas, API endpoint, etc.]
- **Modal/Dialog:** use existing [shadcn dialog / other pattern]
- **API:** [new endpoints needed, server-side proxying for external keys, etc.]
- **State:** [client-side vs persisted]
- **Mobile:** [touch-friendly requirements]
- **Performance:** [debounce, requestAnimationFrame, etc.]

## Style

- [Match existing aesthetic: colours, fonts, light/dark, icons]
- [Specific brand rules: ALL-LIGHT, no dark presets, etc.]

## Don't break

- [List of existing features that must keep working]
- [Security patterns that must be preserved]
- [Role/permission gates to maintain]

## Acceptance criteria

1. [Testable criteria, each one starting with an action]
2. [Example: Click X → Y happens]
...

Build this and deploy to preview when ready. Do NOT deploy to production — I will do that myself.
```

## Step 3 — Add important conventions automatically

Always include in every Emergent build prompt:

- **Deploy rule:** "Build this and deploy to preview when ready. Do NOT deploy to production — I will do that myself." (Dwight deploys, never let Emergent deploy to production)
- **Brand gate:** If the app has an ALL-LIGHT aesthetic (Ashlan-themed apps), always add "ALL-LIGHT. No dark mode. No dark presets."
- **Role gate:** For Content CoPilot features that create/edit content, always add "Admin/editor only — members/approvers don't get this tool"
- **Governance gate:** For AI-generated content, always add "routes to 'Needs review' lane — AI creates, human approves"
- **API keys:** Always specify server-side proxying for external API keys (never expose client-side)
- **Secret name:** Tell Dwight to add the key to Emergent Secrets with a specific env var name (e.g. `REMOVE_BG_API_KEY`)

## Step 4 — Deliver as a copy block

Present the prompt to Dwight using a copy_block surface so he can paste it directly into the Emergent chat for that app:

```markdown
ui_show with:
  surface_type: "copy_block"
  data.label: "[Feature name] — paste into [app] Emergent chat"
  data.text: [the full prompt markdown]
```

If there are multiple apps getting prompts at the same time (e.g. CC + beta site), make it clear which goes to which Emergent chat by labelling the copy blocks distinctly.

## SKILL COMPLETE WHEN

- [ ] `file_write` created the prompt at a named path in /workspace
- [ ] `ui_show` with surface_type copy_block displayed the prompt
- [ ] Dwight confirmed he knows which Emergent chat this goes into
- [ ] Any required API key / Emergent Secret name was communicated to Dwight

## Failure modes

- **Prompt too vague:** Emergent's agents need explicit file names, colour hex codes, character limits, and clear "Don't break" lists. If you find yourself writing "integrate with existing system", stop and get specific.
- **Missing deploy rule:** Forgetting "preview only, Dwight deploys" is the most common error. Emergent will deploy to production if told to. Always include the deploy rule.
- **No acceptance criteria:** Without 5-10 testable criteria, you can't verify the build. Always write acceptance criteria numbered 1-N.
- **Cross-contamination:** P6 goes in the CC Emergent chat. Beta site update goes in the Ashlan beta site Emergent chat. They are separate apps. Make the user knows which is which.
