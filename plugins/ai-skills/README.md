# AI Skills plugin

This directory is the portable plugin package for the skills in the
[`jjundev/ai-skills`](https://github.com/jjundev/ai-skills) repository.

The package intentionally contains skills only. It does not include an MCP
server, so it provides reusable instructions and workflows but does not by
itself expose live GitHub data or arbitrary repository actions to ChatGPT.

The source skill directories remain at the repository root for compatibility
with existing Claude Code, Codex, and Antigravity users. The directories under
`skills/` are the portable package copy consumed by plugin hosts.
