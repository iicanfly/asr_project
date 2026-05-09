# Codex Playbook

## Purpose
This file is the persistent collaboration guide for this repository.
It exists to keep future Codex sessions aligned even when the chat context is short.

## Core Rules
- Every code or config change must end with a local Git commit.
- Remote push is opt-in only. Do not push unless the user explicitly requests it in that round.
- Preserve both internet and intranet code paths unless the user asks for a unified refactor.
- When a task can be solved by an installed skill or enabled plugin, use it automatically.

## Default Task Intake
When the user gives a development task, interpret it with the following fields:
- Goal: what behavior or artifact must change.
- Network scope: `internet`, `intranet`, or `shared`.
- Validation: what observable result proves success.
- Git scope: local commit only unless remote push is explicitly requested.

If the user does not provide all fields, infer them from the repository and state the assumption after acting.

## Plugin Routing
### Browser Use
Use for:
- Opening or validating the local web app.
- Clicking through frontend flows.
- Inspecting rendered UI state in the in-app browser.
- Reproducing browser-side bugs on `localhost` or `127.0.0.1`.

### GitHub
Use for:
- Pull request review and comment handling.
- CI failure triage.
- Repository issue and PR summaries.
- Draft PR preparation and publication when the user requests it.

## Installed Skill Routing
### openai-docs
Use for current official OpenAI API or product guidance.
Do not rely on memory alone when the answer may have changed.

### transcribe
Use for:
- Audio or video to text conversion.
- Speaker diarization requests.
- Repeatable transcription runs using the bundled CLI workflow.

Default behavior:
- Prefer deterministic CLI-based runs.
- Keep output paths stable and review transcript quality.

### speech
Use for:
- Text-to-speech assets.
- Demo narration.
- Accessibility voice output.

Default behavior:
- Use the bundled CLI flow.
- Keep text, voice, and instruction choices explicit in the task notes.

### playwright
Use for:
- Repeatable browser automation from the terminal.
- Snapshot-driven UI validation.
- Fast reproduction of click and form flows.

Default behavior:
- Snapshot after significant UI changes.
- Prefer the skill workflow over ad hoc browser scripting.

### playwright-interactive
Use for:
- Persistent multi-step frontend debugging.
- Reusing browser handles across several edits.
- Heavier UI QA loops where restarting the browser every turn is wasteful.

Default behavior:
- Use only when a persistent interactive browser session will save time.
- Keep a small QA inventory before signoff.

### jupyter-notebook
Use for:
- Experiment notebooks.
- Analysis notebooks for ASR quality, chunking, latency, or prompt comparisons.
- Tutorial-style walkthrough notebooks.

Default behavior:
- Prefer scaffolded notebooks and reproducible cell ordering.

### sentry
Use for:
- Reading current production or staging issues after Sentry is configured.
- Error triage tied to real runtime failures.

Default behavior:
- Treat this as read-only observability.
- Use JSON output when processing CLI results.

### security-best-practices
Use for:
- Explicit security review requests.
- Secure-by-default coding help.
- Prioritized security findings with actionable fixes.

Default behavior:
- Focus on high-impact issues first.
- Avoid broad security rewrites unless requested.

### security-threat-model
Use for:
- Explicit threat-modeling requests.
- Trust boundary and abuse-path analysis for this repository or a submodule.

Default behavior:
- Ground every claim in repository evidence.
- Keep assumptions explicit.

## Recommended Repository Management Files
Maintain these files over time as the project grows:
- `docs/PM/BACKLOG.md`: prioritized upcoming tasks.
- `docs/PM/ENV_MATRIX.md`: differences between internet and intranet behavior, config, dependencies, and deployment constraints.
- `docs/PM/TEST_MATRIX.md`: what needs manual testing, scripted testing, and environment-specific regression checks.
- `docs/PM/SESSION_SUMMARY.md`: compact summary of recent decisions, active branches, and current blockers.
- `docs/PM/ADR/`: architecture decision records for cross-cutting changes.

## Suggested User-to-Codex Task Format
Use this format when possible:
1. Goal
2. Network scope
3. Acceptance check
4. Whether remote push is allowed

Example:
- Goal: improve realtime ASR buffering stability.
- Network scope: shared.
- Acceptance check: no regression in file upload transcription, and websocket updates stay smooth in browser testing.
- Remote push: no.

## Suggested Codex Response Format
For implementation tasks, respond in this order:
1. Brief task understanding and first action.
2. Context gathering and assumptions.
3. Implementation and verification.
4. Local commit hash.
5. Whether a remote push is still pending.
