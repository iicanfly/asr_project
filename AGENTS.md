# AGENTS.md

## Versioning Rule (Must Follow)
- Any project modification must be recorded in Git version control immediately.
- At minimum, each dialogue round that introduces changes should end with a commit.
- Commit messages should clearly describe the round purpose so the full project can be rolled back at any time.
- Do not push to the remote repository unless the user explicitly requests a push in that round.

## Recommended Round Workflow
1. Make the requested changes.
2. Run `git status` and review diffs.
3. Commit all intended changes with a clear message.
4. Push only if the user explicitly requests a remote update.

## Tool and Skill Routing
- Prefer the `Browser Use` plugin when the task involves opening, testing, clicking, typing, or inspecting a local web page such as `localhost`, `127.0.0.1`, or a file-based UI.
- Prefer the `GitHub` plugin when the task involves repository triage, pull requests, issues, reviews, or CI diagnostics.
- Auto-use installed skills when the task clearly matches them, even if the user does not name the skill explicitly.
- Use `openai-docs` for current OpenAI product and API guidance.
- Use `transcribe` for audio or video transcription requests, especially batch conversion and diarization.
- Use `speech` for text-to-speech or voice asset generation.
- Use `playwright` for terminal-driven browser automation and repeatable UI checks.
- Use `playwright-interactive` for persistent browser debugging sessions across multiple frontend iterations.
- Use `jupyter-notebook` for experiment notebooks, exploratory analysis, and reproducible demos.
- Use `sentry` for read-only production issue inspection when Sentry is configured.
- Use `security-best-practices` only for explicit secure coding guidance or security review requests.
- Use `security-threat-model` only for explicit threat-modeling requests.

## Project-Specific Working Norms
- This repository supports both internet and intranet deployment modes; preserve environment-specific behavior and avoid collapsing the two paths without explicit approval.
- For changes that affect runtime behavior, verify whether the impact is internet-only, intranet-only, or shared.
- Keep long-running collaboration context in project files under `docs/PM/` so future sessions can recover quickly with low context overhead.
- Treat `docs/PM/CODEX_PLAYBOOK.md` as the default reference for task intake, skill usage, and collaboration cadence.
