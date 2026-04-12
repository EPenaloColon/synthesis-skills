---
name: synthesis-repo-guard
description: "Session-end enforcement for git repository sync. Detects uncommitted changes and unpushed commits across a workspace. Works with any AI coding tool (Claude Code, Codex, Cursor, etc.) or standalone. Use when asked to: repo guard, check repos, session end check, sync check, repo status, workspace status."
license: "Apache-2.0"
depends_on: []
metadata:
  author: "Rajiv Pant"
  version: "1.0.0"
  source_repo: "github.com/rajivpant/synthesis-skills"
  source_type: "public"
---

# Synthesis Repo Guard

## The Problem

AI coding assistants create and modify files during a session. When the session ends — whether by completion, timeout, or the user closing the window — uncommitted or unpushed changes are stranded on that machine. For anyone who works across multiple machines, this breaks the sync chain. The work exists locally but never reaches GitHub, so the next machine starts from stale state.

No AI tool reliably commits and pushes before session end. Instructions, memory, and good intentions are not enforcement. The solution must be external to the AI.

## The Solution

A standalone Python script (`repo_sync_check.py`) that scans a workspace for git repositories and reports any that have unsynced state. It has zero AI dependencies — it uses only Python stdlib and the git CLI. It works as:

- A terminal command you run manually
- A session-end hook for any AI coding tool
- A scheduled check via cron or launchd
- A CI/CD gate

The script is the single source of truth. Everything else is a trigger.

---

## Quick Start

```bash
# Run directly — checks ~/workspaces by default
./repo_sync_check.py

# Check a specific workspace
./repo_sync_check.py --workspace ~/projects

# Quiet mode — exit code only (for hooks and scripts)
./repo_sync_check.py --quiet

# With macOS alert sound on failure
./repo_sync_check.py --alert --speak

# JSON output for programmatic consumption
./repo_sync_check.py --json --dirty-only
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All repos clean and synced |
| 1 | One or more repos need attention |
| 2 | Error (git not found, workspace doesn't exist) |

---

## What It Detects

| Condition | Report |
|-----------|--------|
| Uncommitted changes (modified, staged, untracked) | `[dirty]` with file list |
| Unpushed commits (ahead of remote) | `[ahead]` with count |
| Unpulled commits (behind remote) | `[behind]` with count |
| Detached HEAD | `[detached]` |
| Git errors | `[error]` with detail |

---

## AI Tool Integration

### Claude Code

Add a `SessionEnd` hook to your settings. The hook runs automatically when any session closes — Claude has no involvement.

In `~/.claude/settings.json` (or `~/.claude/settings.local.json`):

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/repo_sync_check.py --alert --speak --quiet",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

If the installed skill location is `~/.claude/skills/synthesis-repo-guard/`, point to that path.

### OpenAI Codex

Codex supports post-session hooks via its configuration. Add `repo_sync_check.py` to the cleanup step:

```bash
python3 /path/to/repo_sync_check.py --alert --speak
```

### Cursor

Cursor supports task hooks. Add to your `.cursor/settings.json`:

```json
{
  "task.onEnd": "python3 /path/to/repo_sync_check.py --alert --speak"
}
```

### Any Other Tool

If the tool supports any form of post-session or post-task hook, point it at the script. If it doesn't, use the scheduled approach below.

---

## Scheduled Execution

For tools that don't support hooks, or as a safety net alongside hooks, run the check on a schedule.

### macOS launchd

Create `~/Library/LaunchAgents/com.synthesis.repo-guard.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.synthesis.repo-guard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/repo_sync_check.py</string>
        <string>--alert</string>
        <string>--speak</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardErrorPath</key>
    <string>/tmp/repo-guard.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/repo-guard.out</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.synthesis.repo-guard.plist
```

### cron (Linux/macOS)

```bash
# Check every hour, alert if dirty
0 * * * * python3 /path/to/repo_sync_check.py --alert --speak --quiet
```

---

## Relationship to Other Skills

### synthesis-mac-sync

Mac-sync is the **full sync operation** — it fetches, pulls, pushes, commits dirty repos (with user approval), and syncs config files. Repo-guard is the **check** that tells you whether sync is needed.

Run repo-guard frequently (session end, hourly). Run mac-sync when repo-guard reports problems, or as part of your daily ritual.

### synthesis-context-lifecycle

Context lifecycle manages project working memory across sessions. Repo-guard ensures that the files context-lifecycle produces actually reach GitHub. Context lifecycle should commit its own changes, but repo-guard catches the cases where it doesn't.

### Daily rituals / end-of-day checklists

If you have a day-end ritual or checklist skill, add a repo-guard check as the final step. If the check fails, run mac-sync to resolve before ending the day.

---

## Command Reference

```
usage: repo_sync_check.py [-h] [--workspace PATH] [--max-depth N]
                          [--quiet] [--json] [--alert] [--speak]
                          [--dirty-only]

options:
  --workspace, -w PATH   Workspace root to scan (default: ~/workspaces)
  --max-depth, -d N      Max directory depth for repo discovery (default: 3)
  --quiet, -q            Suppress output — exit code only
  --json, -j             Output results as JSON
  --alert, -a            Play macOS alert sound if repos are dirty
  --speak, -s            Speak warning via macOS text-to-speech
  --dirty-only           Only include dirty repos in output
```

---

## Design Principles

1. **Zero AI dependencies** — works without any AI tool installed
2. **Zero external dependencies** — Python stdlib + git CLI only
3. **LLM-agnostic** — same script for Claude Code, Codex, Cursor, or manual use
4. **Non-destructive** — only reads state, never modifies repos
5. **Fast** — scans 20+ repos in under 2 seconds
6. **Composable** — exit codes and JSON output for integration with other tools
