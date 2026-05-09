from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


DEFAULT_PATTERNS = [
    "*.md",
    "docs/**/*.md",
]

DEFAULT_EXCLUDES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".idea",
    "exports",
    "temp_audio",
    "cert",
}


@dataclass
class Issue:
    path: Path
    line_no: int
    reason: str
    line: str


def iter_target_files(root: Path, patterns: Sequence[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if any(part in DEFAULT_EXCLUDES for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def is_suspicious_question_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    question_count = stripped.count("?")
    if question_count < 5:
        return False
    if "http://" in stripped or "https://" in stripped:
        return False
    if stripped.startswith("```") or stripped.startswith("    "):
        return False

    non_space_len = len(stripped.replace(" ", ""))
    if non_space_len == 0:
        return False

    ratio = question_count / non_space_len
    return ratio >= 0.3


def scan_file(path: Path) -> List[Issue]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [
            Issue(
                path=path,
                line_no=0,
                reason=f"文件不是有效的 UTF-8 文本: {exc}",
                line="",
            )
        ]

    issues: List[Issue] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if is_suspicious_question_line(line):
            issues.append(
                Issue(
                    path=path,
                    line_no=idx,
                    reason="检测到异常密集的问号，疑似中文内容被写坏",
                    line=line,
                )
            )
    return issues


def scan_paths(root: Path, patterns: Sequence[str]) -> List[Issue]:
    issues: List[Issue] = []
    for path in iter_target_files(root, patterns):
        issues.extend(scan_file(path))
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="扫描项目中的中文文档损坏风险（例如异常密集的 ? 问号）。"
    )
    parser.add_argument(
        "patterns",
        nargs="*",
        default=DEFAULT_PATTERNS,
        help="要扫描的 glob 模式。默认扫描仓库中的 Markdown 文档。",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    issues = scan_paths(root, args.patterns)

    if not issues:
        print("未发现疑似文档损坏。")
        return 0

    print("发现疑似文档损坏：")
    for issue in issues:
        location = f"{issue.path}:{issue.line_no}" if issue.line_no else str(issue.path)
        print(f"- {location}")
        print(f"  原因: {issue.reason}")
        if issue.line:
            print(f"  内容: {issue.line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
