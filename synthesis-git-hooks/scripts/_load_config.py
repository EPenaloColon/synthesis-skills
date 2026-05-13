#!/usr/bin/env python3
"""synthesis-engineering git-hook config loader (sidecar).

Reads ~/.synthesis/git-hook-config.yaml (or `$SYNTHESIS_GIT_HOOK_CONFIG`),
classifies the current repo by examining its push remotes against the
configured `personal_remote_patterns`, and emits the active pattern set
for the bash engine at `./pre-commit`.

The sidecar is the single source of truth for:

* WHICH patterns belong to which tier (data, not code)
* HOW a repo classifies (personal vs strict)
* WHICH patterns are active for this commit (Tier 0 + optionally Tier 1)

Output formats:

* `--emit-shell-vars` (default): shell-safe assignments via shlex.quote.
* `--classify`: prints just `personal` or `strict`.
* `--print-active-regex`: prints the regex string only.

Exit code is 0 on success, 2 on missing/broken config.

This file ships with the `synthesis-git-hooks` skill at
https://github.com/synthesisengineering/synthesis-skills.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, List

try:
    import yaml
except ImportError:  # pragma: no cover - install-time concern, surfaced clearly
    print(
        "synthesis-git-hooks: PyYAML is required.\n"
        "  Install with: pip3 install --user PyYAML",
        file=sys.stderr,
    )
    sys.exit(2)


DEFAULT_CONFIG = Path.home() / ".synthesis" / "git-hook-config.yaml"


def get_push_remotes() -> List[str]:
    """Return the URLs of all push remotes for the cwd repo, or []."""
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:  # pragma: no cover - git not on PATH
        return []
    urls: List[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            urls.append(parts[1])
    return urls


def classify_repo(personal_patterns: List[str], push_urls: List[str]) -> str:
    """Return ``"personal"`` if every push remote matches at least one
    personal-remote pattern (case-insensitive). Otherwise ``"strict"``.

    Empty remote list classifies as ``"strict"`` — the safe default for a
    fresh ``git init`` or any repo without a defined upstream.
    """
    if not push_urls:
        return "strict"
    if not personal_patterns:
        return "strict"
    compiled = [re.compile(p, re.IGNORECASE) for p in personal_patterns]
    for url in push_urls:
        if not any(c.search(url) for c in compiled):
            return "strict"
    return "personal"


def flatten_patterns(node: Any) -> List[str]:
    """Recursively gather string leaves from a YAML node (list/dict/str)."""
    out: List[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for item in node:
            out.extend(flatten_patterns(item))
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(flatten_patterns(value))
    return out


def build_active_regex(config: dict, repo_class: str) -> str:
    """Concatenate the active patterns into a single alternation regex."""
    parts: List[str] = []
    tier0 = config.get("tier_0_always") or {}
    parts.extend(flatten_patterns(tier0))
    if repo_class == "strict":
        tier1 = config.get("tier_1_strict_only") or {}
        parts.extend(flatten_patterns(tier1))
    # Deduplicate while preserving order — common patterns shouldn't appear
    # twice in the final regex, but config authors are humans.
    seen: set[str] = set()
    deduped: List[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return "|".join(deduped)


def build_allowlist_regex(config: dict) -> str:
    """Concatenate allowlist lines (legitimate matches to suppress)."""
    parts = flatten_patterns(config.get("allowlist_lines") or [])
    return "|".join(parts)


# Built-in path exclusions — paths whose content is, by design, the pattern
# catalog itself. The diff scanner skips these so adding a name to the policy
# is not flagged as leaking it.
DEFAULT_DIFF_EXCLUDE_PATHS = (
    r'(^|/)\.githooks/pre-commit$',
    r'(^|/)\.githooks/extra-patterns\.ya?ml$',
    r'(^|/)\.synthesis/git-hook-config\.ya?ml$',
    r'(^|/)git-hook-config\.example\.ya?ml$',
    r'(^|/)anti-shortcut-catalog\.ya?ml$',
)


def build_diff_exclude_regex(config: dict) -> str:
    """Concatenate path-exclusion regexes (defaults + user-configured)."""
    user_paths = flatten_patterns(config.get("diff_exclude_paths") or [])
    all_paths = list(DEFAULT_DIFF_EXCLUDE_PATHS) + user_paths
    return "|".join(all_paths)


def load_config(path: Path) -> dict:
    if not path.exists():
        print(
            f"synthesis-git-hooks: config not found at {path}",
            file=sys.stderr,
        )
        sys.exit(2)
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    if not isinstance(config, dict):
        print(
            f"synthesis-git-hooks: config at {path} is not a mapping",
            file=sys.stderr,
        )
        sys.exit(2)
    return config


def emit_shell_vars(config: dict) -> None:
    personal_patterns = config.get("personal_remote_patterns") or []
    push_urls = get_push_remotes()
    repo_class = classify_repo(personal_patterns, push_urls)
    active = build_active_regex(config, repo_class)
    allowlist = build_allowlist_regex(config)
    diff_excludes = build_diff_exclude_regex(config)
    check_msg_enabled = bool(config.get("check_commit_message", True))
    check_msg = "1" if (repo_class == "strict" and check_msg_enabled) else "0"
    # shlex.quote handles regex escapes safely under bash `eval`.
    print(f"REPO_CLASS={shlex.quote(repo_class)}")
    print(f"ACTIVE_REGEX={shlex.quote(active)}")
    print(f"ALLOWLIST_REGEX={shlex.quote(allowlist)}")
    print(f"DIFF_EXCLUDE_REGEX={shlex.quote(diff_excludes)}")
    print(f"CHECK_COMMIT_MSG={check_msg}")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="synthesis-engineering git-hook config loader",
    )
    parser.add_argument(
        "--config",
        default=os.environ.get(
            "SYNTHESIS_GIT_HOOK_CONFIG",
            str(DEFAULT_CONFIG),
        ),
        help="Path to git-hook-config.yaml (default: $SYNTHESIS_GIT_HOOK_CONFIG or ~/.synthesis/git-hook-config.yaml)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--emit-shell-vars",
        action="store_true",
        help="Emit shell-quoted assignments for REPO_CLASS, ACTIVE_REGEX, ALLOWLIST_REGEX, CHECK_COMMIT_MSG (default).",
    )
    mode.add_argument(
        "--classify",
        action="store_true",
        help="Print just the repo class (personal|strict) and exit.",
    )
    mode.add_argument(
        "--print-active-regex",
        action="store_true",
        help="Print the active regex (Tier 0 [+ Tier 1]) and exit.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    config = load_config(config_path)

    if args.classify:
        push_urls = get_push_remotes()
        print(classify_repo(
            config.get("personal_remote_patterns") or [],
            push_urls,
        ))
        return 0

    if args.print_active_regex:
        push_urls = get_push_remotes()
        repo_class = classify_repo(
            config.get("personal_remote_patterns") or [],
            push_urls,
        )
        print(build_active_regex(config, repo_class))
        return 0

    # Default: emit shell vars.
    emit_shell_vars(config)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
