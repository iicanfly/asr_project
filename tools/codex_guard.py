from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable
from typing import Sequence

from check_doc_corruption import scan_file


REPO_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_SUFFIXES = {
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".env",
    ".txt",
}
IMPLEMENTATION_ROOTS = {
    "services",
    "src",
    "static",
    "templates",
    "tests",
    "tools",
}
IMPLEMENTATION_FILES = {
    ".env",
    "config.py",
    "main.py",
    "index.html",
    "package.json",
    "package-lock.json",
    "requirements.txt",
}
PROJECT_DOC_FILES = {
    "AGENTS.md",
    "CODING_PROTOCOL.md",
    "README.md",
}


def run_git(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def git_lines(args: Sequence[str]) -> list[str]:
    result = run_git(args)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def gather_changed_paths(*, staged_only: bool) -> list[Path]:
    if staged_only:
        tracked = git_lines(["diff", "--cached", "--name-only", "--diff-filter=ACMRD"])
        candidates = tracked
    else:
        tracked = git_lines(["diff", "--name-only", "--diff-filter=ACMRD", "HEAD"])
        untracked = git_lines(["ls-files", "--others", "--exclude-standard"])
        candidates = tracked + untracked

    unique_paths = {Path(item.replace("\\", "/")) for item in candidates if item}
    return sorted(unique_paths, key=lambda item: item.as_posix())


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def is_project_doc(path: Path) -> bool:
    return is_markdown(path) or path.name in PROJECT_DOC_FILES


def is_implementation_change(path: Path) -> bool:
    if is_project_doc(path):
        return False
    if path.name in IMPLEMENTATION_FILES:
        return True
    if path.suffix.lower() in IMPLEMENTATION_SUFFIXES:
        return True
    return bool(path.parts and path.parts[0] in IMPLEMENTATION_ROOTS)


def scan_markdown_files(paths: Iterable[Path]) -> list[str]:
    failures: list[str] = []
    for relative_path in paths:
        absolute_path = REPO_ROOT / relative_path
        if not absolute_path.is_file():
            continue
        issues = scan_file(absolute_path)
        for issue in issues:
            location = f"{relative_path.as_posix()}:{issue.line_no}" if issue.line_no else relative_path.as_posix()
            failures.append(f"{location} - {issue.reason}")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Codex task guard: check doc sync and doc corruption before commit/finalization."
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Only inspect staged changes (used by pre-commit hook).",
    )
    parser.add_argument(
        "--allow-no-doc-update",
        action="store_true",
        help="Allow implementation changes without markdown updates for this run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    changed_paths = gather_changed_paths(staged_only=args.staged)
    if not changed_paths:
        print("codex_guard: no changes detected.")
        return 0

    markdown_paths = [path for path in changed_paths if is_markdown(path)]
    implementation_paths = [path for path in changed_paths if is_implementation_change(path)]
    project_doc_paths = [path for path in changed_paths if is_project_doc(path)]

    print("codex_guard: changed paths")
    for path in changed_paths:
        print(f"  - {path.as_posix()}")

    failures: list[str] = []
    failures.extend(scan_markdown_files(markdown_paths))

    allow_no_doc_update = args.allow_no_doc_update or os.getenv("CODEX_ALLOW_NO_DOC_UPDATE") == "1"
    if implementation_paths and not project_doc_paths and not allow_no_doc_update:
        failures.append(
            "Implementation changes detected without any markdown/doc update. "
            "Update the relevant docs or rerun with CODEX_ALLOW_NO_DOC_UPDATE=1 after making an explicit decision."
        )

    if failures:
        print("codex_guard: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("codex_guard: OK")
    if implementation_paths and not project_doc_paths:
        print("  - doc update was explicitly bypassed for this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
