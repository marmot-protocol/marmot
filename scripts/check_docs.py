#!/usr/bin/env python3
"""Check repository-local Markdown links and GitHub-style heading anchors offline.

Checks inline links/images, full/collapsed/shortcut reference links, and HTML
href/src attributes. Fenced code and inline code are examples, not links.
Fragments on Markdown targets are checked; non-Markdown assets are checked for
existence only. Remote URLs are deliberately not fetched.
"""

from __future__ import annotations

import html
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit


def without_fences(text: str) -> str:
    result = []
    fence = None
    for line in text.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            if re.match(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$", line):
                fence = None
            result.append("\n" if line.endswith("\n") else "")
        elif match:
            fence = match[1]
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(line)
    return "".join(result)


def without_code(text: str) -> str:
    return re.sub(r"(`+)([\s\S]*?)(?<!`)\1(?!`)", lambda m: "\n" * m[0].count("\n"), text)


def slug(title: str) -> str:
    title = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", title)
    title = re.sub(r"<[^>]+>", "", title)
    title = html.unescape(title).lower().replace("`", "")
    title = "".join(c for c in title if c in "_- " or unicodedata.category(c)[0] in "LNM")
    return title.replace(" ", "-")


def anchors(text: str) -> set[str]:
    text = without_fences(text)
    found = set()
    used = set()
    previous = ""
    for line in text.splitlines():
        match = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        title = match[1] if match else None
        if re.match(r"^ {0,3}(?:=+|-+)\s*$", line) and previous.strip():
            title = previous.strip()
        if title is not None:
            base = slug(title)
            candidate = base
            suffix = 0
            while candidate in used:
                suffix += 1
                candidate = f"{base}-{suffix}"
            used.add(candidate)
            found.add(candidate)
        previous = line
    for match in re.finditer(r"<[^>]+\b(?:id|name)\s*=\s*(['\"])(.*?)\1[^>]*>", text):
        found.add(html.unescape(match[2]))
    return found


def label_key(label: str) -> str:
    return " ".join(label.split()).casefold()


def destination(text: str, start: int) -> tuple[str, int]:
    """Read a link destination, allowing escaped/nested parentheses and <spaces>."""
    i = start
    while i < len(text) and text[i].isspace():
        i += 1
    if i < len(text) and text[i] == "<":
        end = text.find(">", i + 1)
        if end != -1:
            return text[i + 1:end], end + 1
    begin = i
    depth = 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            i += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        elif char.isspace() and depth == 0:
            break
        i += 1
    return re.sub(r"\\([\\() <>])", r"\1", text[begin:i]), i


def links(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    text = without_fences(text)
    definitions = {}
    output = []
    errors = []
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        match = re.match(r"^ {0,3}\[([^]]+)\]:\s*(.*)", line)
        if match:
            target, _ = destination(match[2], 0)
            definitions.setdefault(label_key(match[1]), target)
            output.append((i + 1, target))
            lines[i] = "\n" if line.endswith("\n") else ""
    text = without_code("".join(lines))
    # Match nested brackets in link labels with a stack, then read their target.
    stack = []
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "[":
            stack.append(i)
        elif text[i] == "]" and stack:
            begin = stack.pop()
            label = text[begin + 1:i]
            line = text.count("\n", 0, begin) + 1
            next_i = i + 1
            if next_i < len(text) and text[next_i] == "(":
                target, end = destination(text, next_i + 1)
                output.append((line, target))
                i = max(i, end - 1)
            elif next_i < len(text) and text[next_i] == "[":
                end = text.find("]", next_i + 1)
                if end != -1:
                    key = label_key(text[next_i + 1:end] or label)
                    if key in definitions:
                        output.append((line, definitions[key]))
                    else:
                        errors.append(f"{line}: undefined reference [{key}]")
                    i = end
            elif label_key(label) in definitions:
                output.append((line, definitions[label_key(label)]))
        i += 1
    for match in re.finditer(r"<[^>]+\b(?:href|src)\s*=\s*(['\"])(.*?)\1[^>]*>", text):
        output.append((text.count("\n", 0, match.start()) + 1, html.unescape(match[2])))
    return output, errors


def check(root: Path, paths: list[Path]) -> list[str]:
    supplied_root = root
    root = root.resolve()
    errors = []
    cache = {}
    for source in paths:
        name = source.relative_to(supplied_root).as_posix()
        source = root / name
        if not source.is_file():
            errors.append(f"{name}: missing Markdown file or broken symlink")
            continue
        targets, parse_errors = links(source.read_text(encoding="utf-8"))
        errors.extend(f"{name}:{error}" for error in parse_errors)
        for line, target in targets:
            try:
                url = urlsplit(target)
            except ValueError:
                errors.append(f"{name}:{line}: malformed target {target!r}")
                continue
            if url.scheme or url.netloc:
                continue
            path = unquote(url.path)
            if path.startswith("/"):
                resolved = (root / path.lstrip("/")).resolve()
            elif path:
                resolved = (source.parent / path).resolve()
            else:
                resolved = source.resolve()
            if not resolved.is_relative_to(root):
                errors.append(f"{name}:{line}: target escapes repository: {target}")
            elif not resolved.exists():
                errors.append(f"{name}:{line}: missing target: {target}")
            elif url.fragment and resolved.suffix.lower() == ".md" and resolved.is_file():
                if resolved not in cache:
                    cache[resolved] = anchors(resolved.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in cache[resolved]:
                    errors.append(f"{name}:{line}: missing anchor: {target}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=root, check=True, capture_output=True,
    )
    paths = sorted({root / p.decode("utf-8") for p in result.stdout.split(b"\0") if p})
    errors = check(root, paths)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"Documentation checks failed: {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Documentation checks passed: {len(paths)} Markdown files; local links and anchors only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
