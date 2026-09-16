# Global skill storage

This repository is the canonical source for the user-managed skills used by
Codex, Claude, and Google Antigravity on this Windows machine.

Run the following from the repository root after adding or restoring global
skills:

```powershell
powershell -ExecutionPolicy Bypass -File .\link-global-skills.ps1
```

The script creates directory junctions for every directory containing
`SKILL.md` in these host locations:

- `%USERPROFILE%\.agents\skills`
- `%USERPROFILE%\.claude\skills`
- `%USERPROFILE%\.gemini\config\skills` (Antigravity IDE / Antigravity 2.0)
- `%USERPROFILE%\.gemini\antigravity-cli\skills` (Antigravity CLI)
- `%USERPROFILE%\.codex\skills`

For compatibility, the script also mirrors the older
`%USERPROFILE%\.gemini\antigravity\.agents\skills` location when it exists.

Skills found only in a host location are imported into this repository. When a
host already has a same-named physical skill, the repository version becomes
canonical and the old directory is moved to `%USERPROFILE%\.ai-skills-backup\`.
Host-specific unmanaged directories and Codex runtime directories are left in
place.

Because junctions are local filesystem metadata, they are not committed to
Git. A fresh Windows checkout should run the script once on that machine.
