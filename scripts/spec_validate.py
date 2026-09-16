#!/usr/bin/env python3
"""Deterministic validation for Marmot specification pull requests."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SURFACES = {"foundation", "protocol-core", "app-components", "transports", "features"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REGISTRY_COMPONENT_RE = re.compile(
    r"^\| `(?P<id>0x8[0-9a-f]{3})`[ \t]+\| `(?P<name>[^`]+)`[ \t]+\| "
    r"\[(?:doc|draft)\]\(\.\./app-components/(?P<doc>[^)]+\.md)\)[ \t]+\|$",
    re.MULTILINE,
)
REGISTRY_KIND_RE = re.compile(
    r"^\| `(?P<kind>\d+)`[ \t]+\|.*\| \[[^]]+\]\([^)]+\)[ \t]+\|$", re.MULTILINE
)


class ValidationError(RuntimeError):
    pass


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def fail(message: str) -> NoReturn:
    raise ValidationError(message)


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        fail(f"{path.relative_to(ROOT)} is not valid UTF-8: {error}")


def changed_files(base: str, head: str) -> list[Path]:
    result = run("git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}")
    return [ROOT / line for line in result.stdout.splitlines() if line]


def check_diff_hygiene(base: str, head: str) -> None:
    result = run("git", "diff", "--check", f"{base}...{head}", check=False)
    if result.returncode:
        fail("git diff --check failed:\n" + result.stdout + result.stderr)
    print("PASS diff hygiene (git diff --check)")


def link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    # Markdown titles follow the URL after whitespace. Repository paths do not contain spaces.
    return target.split(maxsplit=1)[0]


def check_markdown(paths: list[Path]) -> None:
    checked = 0
    for path in paths:
        if path.suffix.lower() != ".md" or not path.exists():
            continue
        text = read_utf8(path)
        checked += 1
        for match in LINK_RE.finditer(text):
            target = link_target(match.group(1))
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("#", "//")):
                continue
            relative = unquote(parsed.path)
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                fail(f"{path.relative_to(ROOT)} links outside the repository: {target}")
            if not resolved.exists():
                line = text.count("\n", 0, match.start()) + 1
                fail(f"{path.relative_to(ROOT)}:{line} has a missing relative link: {target}")
    print(f"PASS changed Markdown UTF-8 and relative links ({checked} files)")


def unique(values: list[str], label: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        fail(f"duplicate {label}: {', '.join(duplicates)}")


def check_registry_and_components(paths: list[Path]) -> None:
    registry = read_utf8(ROOT / "foundation/registries.md")
    components = list(REGISTRY_COMPONENT_RE.finditer(registry))
    if not components:
        fail("foundation/registries.md has no parseable component registry rows")
    unique([m.group("id") for m in components], "component ids")
    unique([m.group("name") for m in components], "component names")
    unique([m.group("doc") for m in components], "component documents")

    kinds_heading = "## Nostr event kinds used by Marmot"
    if kinds_heading not in registry:
        fail("foundation/registries.md is missing the Nostr event-kinds section")
    kinds_section = registry.split(kinds_heading, 1)[1].split("\n## ", 1)[0]
    kinds = [match.group("kind") for match in REGISTRY_KIND_RE.finditer(kinds_section)]
    if not kinds:
        fail("foundation/registries.md has no parseable Nostr kind rows")
    unique(kinds, "Nostr event kinds")

    registry_by_doc = {m.group("doc"): (m.group("id"), m.group("name")) for m in components}
    layout = read_utf8(ROOT / "layout.md")
    component_index = read_utf8(ROOT / "app-components/README.md")

    for path in paths:
        relative = path.relative_to(ROOT)
        if len(relative.parts) != 2 or relative.parts[0] not in SURFACES or path.suffix != ".md":
            continue
        if path.name in {"README.md", "AGENTS.md"}:
            continue
        if path.name not in layout:
            fail(f"{relative} is missing from layout.md")
        surface_index = read_utf8(ROOT / relative.parts[0] / "README.md")
        if path.name not in surface_index:
            fail(f"{relative} is missing from {relative.parts[0]}/README.md")

        if relative.parts[0] != "app-components":
            continue
        text = read_utf8(path)
        id_match = re.search(r"^- Component id: `(0x[0-9a-f]{4})`$", text, re.MULTILINE)
        name_match = re.search(r"^- Name: `([^`]+)`$", text, re.MULTILINE)
        if not id_match or not name_match:
            fail(f"{relative} must declare one component id and name")
        assert id_match is not None and name_match is not None
        registered = registry_by_doc.get(path.name)
        declared = (id_match.group(1), name_match.group(1))
        if registered != declared:
            fail(f"{relative} declares {declared}, registry has {registered}")
        if path.name not in component_index:
            fail(f"{relative} is missing from app-components/README.md")

    print(f"PASS registry uniqueness and changed component/surface consistency ({len(components)} components)")


def check_surface_boundaries(paths: list[Path]) -> None:
    forbidden = re.compile(
        r"Rust crate|database table|queue shape|retry worker|local API|test harness|"
        r"\bdarkmatter\b|CgkaEngine|PendingStateRef|drain_auto_publish|"
        r"drain_auto_proposals|confirm_published|publish_failed"
    )
    findings: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT)
        if path.suffix != ".md" or not path.exists() or path.name in {"AGENTS.md"}:
            continue
        if relative.parts[0] not in SURFACES:
            continue
        text = read_utf8(path)
        for number, line in enumerate(text.splitlines(), 1):
            if forbidden.search(line):
                findings.append(f"{relative}:{number}: {line.strip()}")
    if findings:
        fail("implementation details leaked into changed spec surfaces:\n" + "\n".join(findings))
    print("PASS changed normative surface-boundary leak check")


def require(text: str, fragment: str, source: str) -> None:
    normalized_text = " ".join(text.split())
    normalized_fragment = " ".join(fragment.split())
    if normalized_fragment not in normalized_text:
        fail(f"{source} is missing focused V1 assertion: {fragment}")


def check_history_purge_v1() -> None:
    component_name = "app-components/history-purge-v1.md"
    conformance_name = "foundation/conformance.md"
    registry_name = "foundation/registries.md"
    component = read_utf8(ROOT / component_name)
    conformance = read_utf8(ROOT / conformance_name)
    registry = read_utf8(ROOT / registry_name)

    component_fragments = [
        "at most one open request per group",
        "parent_group_context_hash` MUST equal `SHA-256(TLS-serialize(candidate_parent_group_context))`",
        "without Marmot-specific re-encoding",
        "contains at\nmost one record per account",
        "A No is not an advisory app event",
        "MUST refuse a second or conflicting decision",
        "one valid Yes for every `members` account",
        "Every terminal Commit removes the GroupContext `0x800d` entry",
        "Any missing, duplicate, or\nextra proposal makes the terminal transition invalid.",
        "Expiry is never consent.",
        "A client MUST durably install one reversible suppression boundary",
        "Best-effort destructive cleanup begins only after the authorization remains selected",
        "resumes after restart",
        "external copies are outside enforceable scope",
        "A receipt is valid only when `finalization_id` identifies the accepted finalization",
        "non-canonical finalization is invalid and MUST NOT contribute to a completion projection",
    ]
    for fragment in component_fragments:
        require(component, fragment, component_name)

    conformance_fragments = [
        "## Consensual history purge scenarios",
        "wrong-signer decision",
        "validator presented conflicting proofs MUST reject them",
        "timeout, silence, restart, and expiry never produce consent",
        "verifying rejection with no retention, suppression, or deletion effect",
        "suppression is withdrawn and destructive deletion has not begun",
        "completion of remaining\neligible cleanup after restart",
        "MUST NOT claim physical overwrite, deletion of external copies",
    ]
    for fragment in conformance_fragments:
        require(conformance, fragment, conformance_name)

    registry_fragments = [
        "| `0x800d`     | `marmot.group.history-purge.v1`",
        "| `453`   | History-purge control event",
        "| `454`   | History-purge member decision",
        "| `455`   | History-purge request proof",
        "| `456`   | History-purge cancellation proof",
        "| `457`   | History-purge terminal proof",
    ]
    for fragment in registry_fragments:
        require(registry, fragment, registry_name)

    print("PASS focused history-purge V1 assertions (authorization, lifecycle, replay, restart, recovery limits)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="base commit")
    parser.add_argument("--head", default="HEAD", help="head commit")
    parser.add_argument("--mode", choices=("fast", "focused", "all"), default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run("git", "rev-parse", "--verify", f"{args.base}^{{commit}}")
        run("git", "rev-parse", "--verify", f"{args.head}^{{commit}}")
        paths = changed_files(args.base, args.head)
        if args.mode in {"fast", "all"}:
            check_diff_hygiene(args.base, args.head)
            check_markdown(paths)
            check_registry_and_components(paths)
            check_surface_boundaries(paths)
        if args.mode in {"focused", "all"}:
            check_history_purge_v1()
    except (ValidationError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS spec validation mode={args.mode} base={args.base} head={args.head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
