# Global skill storage

This repository is the canonical source for user-managed skills across Codex, Claude, and Google Antigravity on Windows, macOS, and Linux.

## Setup & Linking

Run the unified manager from the repository root:

```bash
# Link all skills to global agent directories (macOS / Linux / Windows)
python3 script/manage.py link

# On Windows PowerShell:
python script/manage.py link
```

The script automatically handles filesystem differences:
- **Windows**: Creates standard symbolic links (`os.symlink`) first for Go 1.23+ / Antigravity compatibility, falling back to NTFS Directory Junctions if symlink privileges are unavailable.
- **macOS / Linux**: Creates standard POSIX symbolic links.

Global host locations linked:
- `~/.gemini/config/skills` (Antigravity IDE / Antigravity 2.0)
- `~/.gemini/antigravity-cli/skills` (Antigravity CLI)
- `~/.claude/skills` (Claude Code)
- `~/.codex/skills` (Codex)
- `~/.agents/skills` (Agent Reach / OpenCLI)
- `~/.gemini/antigravity/.agents/skills` (Antigravity Legacy mirror)

## Checking and Syncing Upstreams

```bash
# Check if upstream skills have updates
python3 script/manage.py check

# Sync all allowlisted skills from upstream repos
python3 script/manage.py sync

# Sync specific upstream repo (e.g. ecc, hyperframes, taste-skill, superpowers, caveman)
python3 script/manage.py sync --target ecc
```

## Running Tests

```bash
python3 script/manage.py test
```
