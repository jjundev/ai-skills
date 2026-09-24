#!/usr/bin/env bash
# ==============================================================================
# Tests sync-hyperframes.sh against fake local upstream repo.
# Run: ./tests/sync-hyperframes.test.sh
# ==============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "ok: $*"; }

git_q() { git -c user.name=t -c user.email=t@t -c commit.gpgsign=false "$@"; }

# Build a fake upstream hyperframes repo
mkdir -p "$WORK/hyperframes/skills/hyperframes"
mkdir -p "$WORK/hyperframes/skills/motion-graphics"
mkdir -p "$WORK/hyperframes/skills/faceless-explainer"
mkdir -p "$WORK/hyperframes/assets"
mkdir -p "$WORK/hyperframes/.claude-plugin"

cat <<'EOF' > "$WORK/hyperframes/skills/hyperframes/SKILL.md"
---
name: hyperframes
description: Entry point
---
# Hyperframes Router
EOF

cat <<'EOF' > "$WORK/hyperframes/skills/motion-graphics/SKILL.md"
---
name: motion-graphics
description: Motion
---
# Motion Graphics
EOF

cat <<'EOF' > "$WORK/hyperframes/skills/faceless-explainer/SKILL.md"
---
name: faceless-explainer
description: Explainer
---
# Faceless Explainer
EOF

printf 'fake-icon' > "$WORK/hyperframes/assets/icon.png"
printf '{"name":"hyperframes","version":"1.0.0"}' > "$WORK/hyperframes/.claude-plugin/plugin.json"

git_q -C "$WORK/hyperframes" init -q
git_q -C "$WORK/hyperframes" add -A
git_q -C "$WORK/hyperframes" commit -q -m "feat: initial hyperframes release"
git_q -C "$WORK/hyperframes" tag v1.0.0

# Build fake local skills repo
LOCAL="$WORK/local"
mkdir -p "$LOCAL/plugins/ai-skills/skills"
mkdir -p "$LOCAL/.agents/plugins"
cat <<'EOF' > "$LOCAL/.agents/plugins/marketplace.json"
{
  "name": "ai-skills",
  "plugins": [
    {
      "name": "ai-skills",
      "source": { "source": "local", "path": "./plugins/ai-skills" }
    }
  ]
}
EOF

cp "$HERE/sync-hyperframes.sh" "$LOCAL/sync-hyperframes.sh"
git_q -C "$LOCAL" init -q
git_q -C "$LOCAL" add -A
git_q -C "$LOCAL" commit -q -m "chore: initial commit"

export HYPERFRAMES_REPO="file://$WORK/hyperframes"

# --- Run 1: real sync with commit ---
OUT1="$( cd "$LOCAL" && ./sync-hyperframes.sh 2>&1 )" || { echo "$OUT1"; fail "run 1 exited non-zero"; }

[ -f "$LOCAL/hyperframes/SKILL.md" ] && pass "root hyperframes skill created" || fail "root hyperframes skill missing"
[ -f "$LOCAL/motion-graphics/SKILL.md" ] && pass "root motion-graphics skill created" || fail "root motion-graphics skill missing"
[ -f "$LOCAL/faceless-explainer/SKILL.md" ] && pass "root faceless-explainer skill created" || fail "root faceless-explainer skill missing"

[ -f "$LOCAL/plugins/hyperframes/skills/hyperframes/SKILL.md" ] && pass "plugin hyperframes skill created" || fail "plugin hyperframes skill missing"
[ -f "$LOCAL/plugins/hyperframes/plugin.json" ] && pass "plugin.json created" || fail "plugin.json missing"
[ -f "$LOCAL/plugins/hyperframes/assets/icon.png" ] && pass "plugin assets copied" || fail "plugin assets missing"

[ -f "$LOCAL/plugins/ai-skills/skills/hyperframes/SKILL.md" ] && pass "ai-skills portable mirror created" || fail "ai-skills portable mirror missing"

grep -q "hyperframes" "$LOCAL/.agents/plugins/marketplace.json" && pass "marketplace.json registered hyperframes" || fail "marketplace.json missing hyperframes"

HF_SHA7="$(git -C "$WORK/hyperframes" rev-parse --short=7 HEAD)"
[ "$(git -C "$LOCAL" log -1 --format=%s)" = "chore: sync hyperframes v1.0.0 ($HF_SHA7)" ] && pass "commit message format with tag" || fail "unexpected commit message: $(git -C "$LOCAL" log -1 --format=%s)"

# --- Run 2: no-op run reports up-to-date ---
OUT2="$( cd "$LOCAL" && ./sync-hyperframes.sh 2>&1 )" || fail "run 2 exited non-zero"
echo "$OUT2" | grep -q "already up-to-date" && pass "no-op run reports up-to-date" || fail "run 2 output: $OUT2"

# --- Run 3: NO_COMMIT=1 leaves changes uncommitted ---
printf 'v2\n' >> "$WORK/hyperframes/skills/hyperframes/SKILL.md"
git_q -C "$WORK/hyperframes" commit -q -am "v2 update"

OUT3="$( cd "$LOCAL" && NO_COMMIT=1 ./sync-hyperframes.sh 2>&1 )" || fail "run 3 exited non-zero"
echo "$OUT3" | grep -q "NO_COMMIT=1" && pass "NO_COMMIT=1 recognized" || fail "NO_COMMIT=1 not recognized"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "NO_COMMIT makes no commit" || fail "NO_COMMIT committed"

if [ "$FAILS" -eq 0 ]; then echo "ALL PASSED"; else echo "$FAILS FAILED"; exit 1; fi
