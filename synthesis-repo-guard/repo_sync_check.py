#!/usr/bin/env python3
"""
repo_sync_check.py — Detect unsynced git repositories in a workspace.

Scans a workspace root for git repositories and reports any that have:
  - Uncommitted changes (modified, staged, or untracked files)
  - Unpushed commits (ahead of remote)
  - Unpulled commits (behind remote)

Designed to run standalone from a terminal, as an AI tool session-end hook
(Claude Code, Codex, Cursor, etc.), or on a schedule via cron/launchd.

Zero external dependencies — uses only Python stdlib + git CLI.

Exit codes:
  0 — All repos clean and synced
  1 — One or more repos need attention
  2 — Error (e.g., git not found, workspace doesn't exist)

Examples:
  # Check default workspace ~/workspaces
  ./repo_sync_check.py

  # Check a specific workspace
  ./repo_sync_check.py --workspace ~/projects

  # Quiet mode — exit code only, no output (for hooks)
  ./repo_sync_check.py --quiet

  # With macOS alert sound on failure
  ./repo_sync_check.py --alert

  # JSON output for programmatic consumption
  ./repo_sync_check.py --json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def find_git_repos(workspace: Path, max_depth: int = 3) -> list[Path]:
    """Find all git repositories under workspace, up to max_depth."""
    repos = []
    workspace = workspace.resolve()

    def _scan(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            git_dir = directory / ".git"
            if git_dir.exists():
                repos.append(directory)
                return  # Don't recurse into nested repos
            for child in sorted(directory.iterdir()):
                if child.is_dir() and not child.name.startswith("."):
                    _scan(child, depth + 1)
        except PermissionError:
            pass

    _scan(workspace, 0)
    return repos


def git_cmd(repo: Path, *args: str) -> tuple[int, str]:
    """Run a git command in a repo directory. Returns (exit_code, stdout)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo)] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except FileNotFoundError:
        return -1, "git not found"


def check_repo(repo: Path) -> dict:
    """Check a single repo for unsynced state. Returns a status dict."""
    name = repo.name
    status = {
        "name": name,
        "path": str(repo),
        "clean": True,
        "issues": [],
    }

    # Check for uncommitted changes
    rc, output = git_cmd(repo, "status", "--porcelain")
    if rc != 0:
        status["clean"] = False
        status["issues"].append({"type": "error", "detail": f"git status failed: {output}"})
        return status

    if output:
        lines = output.splitlines()
        status["clean"] = False
        status["issues"].append({
            "type": "uncommitted",
            "detail": f"{len(lines)} uncommitted file(s)",
            "files": lines[:10],  # Cap at 10 for readability
            "total": len(lines),
        })

    # Get current branch
    rc, branch = git_cmd(repo, "branch", "--show-current")
    if rc != 0 or not branch:
        # Detached HEAD or error — report and move on
        if not output:  # Only if no uncommitted changes already reported
            status["issues"].append({"type": "detached", "detail": "detached HEAD or no branch"})
        return status

    # Check ahead/behind remote
    rc, counts = git_cmd(repo, "rev-list", "--left-right", "--count", f"origin/{branch}...{branch}")
    if rc != 0:
        # No remote tracking — not necessarily a problem
        return status

    parts = counts.split()
    if len(parts) == 2:
        behind, ahead = int(parts[0]), int(parts[1])
        if ahead > 0:
            status["clean"] = False
            status["issues"].append({
                "type": "unpushed",
                "detail": f"{ahead} unpushed commit(s) on {branch}",
                "count": ahead,
            })
        if behind > 0:
            status["clean"] = False
            status["issues"].append({
                "type": "behind",
                "detail": f"{behind} commit(s) behind origin/{branch}",
                "count": behind,
            })

    return status


def play_alert() -> None:
    """Play macOS alert sound. No-op on other platforms."""
    if sys.platform == "darwin":
        sound = "/System/Library/Sounds/Glass.aiff"
        for _ in range(3):
            subprocess.run(["afplay", sound], capture_output=True)


def speak_warning(dirty_count: int) -> None:
    """Speak a warning on macOS. No-op on other platforms."""
    if sys.platform == "darwin":
        msg = f"Warning: {dirty_count} {'repository has' if dirty_count == 1 else 'repositories have'} unsynced changes."
        subprocess.run(["say", msg], capture_output=True)


def format_text_report(results: list[dict]) -> str:
    """Format results as human-readable text."""
    dirty = [r for r in results if not r["clean"]]
    clean_count = len(results) - len(dirty)

    if not dirty:
        return f"All {len(results)} repositories clean and synced."

    lines = []
    lines.append(f"Repositories needing attention: {len(dirty)} of {len(results)}")
    lines.append("")

    for repo in dirty:
        lines.append(f"  {repo['name']}/")
        for issue in repo["issues"]:
            marker = {
                "uncommitted": "dirty",
                "unpushed": "ahead",
                "behind": "behind",
                "detached": "detached",
                "error": "error",
            }.get(issue["type"], issue["type"])
            lines.append(f"    [{marker}] {issue['detail']}")
            if "files" in issue:
                for f in issue["files"]:
                    lines.append(f"      {f}")
                if issue.get("total", 0) > len(issue.get("files", [])):
                    lines.append(f"      ... and {issue['total'] - len(issue['files'])} more")
        lines.append("")

    lines.append(f"Clean: {clean_count} repositories")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check workspace git repositories for unsynced state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--workspace", "-w",
        type=Path,
        default=Path.home() / "workspaces",
        help="Workspace root to scan (default: ~/workspaces)",
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=3,
        help="Maximum directory depth for repo discovery (default: 3)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output — exit code only",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--alert", "-a",
        action="store_true",
        help="Play macOS alert sound if repos are dirty",
    )
    parser.add_argument(
        "--speak", "-s",
        action="store_true",
        help="Speak warning via macOS text-to-speech if repos are dirty",
    )
    parser.add_argument(
        "--dirty-only",
        action="store_true",
        help="Only include dirty repos in output (skip clean repos)",
    )
    args = parser.parse_args()

    # Validate workspace
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        if not args.quiet:
            print(f"Error: workspace not found: {workspace}", file=sys.stderr)
        return 2

    # Verify git is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        if not args.quiet:
            print("Error: git is not installed or not in PATH", file=sys.stderr)
        return 2

    # Find and check repos
    repos = find_git_repos(workspace, args.max_depth)
    if not repos:
        if not args.quiet:
            print(f"No git repositories found under {workspace}")
        return 0

    results = [check_repo(repo) for repo in repos]
    dirty = [r for r in results if not r["clean"]]

    # Output
    if not args.quiet:
        if args.json:
            output = results if not args.dirty_only else dirty
            print(json.dumps(output, indent=2))
        else:
            print(format_text_report(results))

    # Alerts
    if dirty:
        if args.alert:
            play_alert()
        if args.speak:
            speak_warning(len(dirty))

    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
