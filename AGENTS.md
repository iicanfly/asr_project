# AGENTS.md

## Versioning Rule (Must Follow)
- Any project modification must be recorded in Git version control immediately.
- At minimum, each dialogue round that introduces changes should end with a commit.
- Commit messages should clearly describe the round purpose so the full project can be rolled back at any time.

## Recommended Round Workflow
1. Make the requested changes.
2. Run `git status` and review diffs.
3. Commit all intended changes with a clear message.
4. If remote is available, push to keep local/remote history aligned.
