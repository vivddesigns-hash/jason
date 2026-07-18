# FR-008: Enforce the HQ Approval Gate in Code

- **Requested by:** Security review (2026-07-18)
- **Priority:** HIGH
- **Findings:** H4 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI

## The problem
The HQ tools (`hq_agent`, `hq_confirm`) can send email and change records using
real business credentials. The "get the user's explicit approval before sending"
rule currently lives **only in the system prompt** (a soft instruction), not in
code. Combined with the unsandboxed agent (FR-005), a prompt-injection payload
could get the agent to send mail as you or read the HQ key — with no hard stop.

## The fix
- Enforce a **code-level confirmation gate** for outbound / irreversible HQ actions
  (send email, modify records): they cannot execute without a real user-approval
  signal from the UI, not the model approving itself.
- Treat model "self-approval" as insufficient; require an out-of-band human tap.

## Acceptance criteria
- An outbound HQ action cannot execute without an explicit user approval step,
  regardless of what the model decides or is told to do.
- Injected instructions in fetched content cannot trigger a send on their own.
