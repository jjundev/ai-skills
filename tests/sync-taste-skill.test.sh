#!/usr/bin/env bash
# Tests sync-taste-skill.sh against a fake local upstream repository.
# Run: ./tests/sync-taste-skill.test.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "ok: $*"; }

git_q() { git -c user.name=t -c user.email=t@t -c commit.gpgsign=false "$@"; }

# Helper to build mock upstream repo
make_upstream() {
  local dir="$1"; shift
  mkdir -p "$dir/skills"
  for entry in "$@"; do
    case "$entry" in
      */) mkdir -p "$dir/skills/$entry"; printf 'upstream %s\n' "$entry" > "$dir/skills/${entry}SKILL.md" ;;
      *)  printf 'build file\n' > "$dir/skills/$entry" ;;
    esac
  done
  git_q -C "$dir" init -q
  git_q -C "$dir" add -A
  git_q -C "$dir" commit -q -m init
}

make_upstream "$WORK/taste-repo" taste-skill/ brandkit/ unlisted-skill/ compile.mjs

LOCAL="$WORK/local"
mkdir -p "$LOCAL/taste-skill" "$LOCAL/my-local-skill"
cp "$HERE/sync-taste-skill.sh" "$LOCAL/sync-taste-skill.sh"
printf 'old\n' > "$LOCAL/taste-skill/SKILL.md"
printf 'stale\n' > "$LOCAL/taste-skill/stale.md"
printf 'local\n' > "$LOCAL/my-local-skill/SKILL.md"

git_q -C "$LOCAL" init -q
git_q -C "$LOCAL" add -A
git_q -C "$LOCAL" commit -q -m init
printf 'unrelated\n' > "$LOCAL/unrelated.txt"

export TASTE_REPO="file://$WORK/taste-repo"

# --- Run 1: real sync with commit ---
OUT1="$( cd "$LOCAL" && ./sync-taste-skill.sh 2>&1 )" || { echo "$OUT1"; fail "run 1 exited non-zero"; }

[ "$(cat "$LOCAL/taste-skill/SKILL.md")" = "upstream taste-skill/" ] && pass "allowlisted taste-skill copied" || fail "taste-skill not updated"
[ ! -f "$LOCAL/taste-skill/stale.md" ] && pass "stale file removed by delete-then-copy" || fail "stale file remains"
[ -f "$LOCAL/brandkit/SKILL.md" ] && pass "allowlisted brandkit copied" || fail "brandkit not copied"
[ ! -d "$LOCAL/unlisted-skill" ] && pass "unlisted upstream skill not copied" || fail "unlisted skill copied"
[ "$(cat "$LOCAL/my-local-skill/SKILL.md")" = "local" ] && pass "unmanaged local skill untouched" || fail "local skill clobbered"
[ -f "$LOCAL/unrelated.txt" ] && pass "unrelated file untouched" || fail "unrelated file touched"

# Verify commit created with provenance
COMMIT_MSG="$(git_q -C "$LOCAL" log -n 1 --pretty=format:"%s")"
echo "$COMMIT_MSG" | grep -qE "^chore: sync taste-skill \([a-f0-9]{7}\)" && pass "git commit subject carries short sha" || fail "commit msg format unexpected: $COMMIT_MSG"

# --- Run 2: idempotent re-run ---
OUT2="$( cd "$LOCAL" && ./sync-taste-skill.sh 2>&1 )"
echo "$OUT2" | grep -q "already up-to-date" && pass "no-op run reports up-to-date" || fail "no-op failed"

# --- Run 3: NO_COMMIT=1 ---
printf 'upstream v2\n' > "$WORK/taste-repo/skills/taste-skill/SKILL.md"
git_q -C "$WORK/taste-repo" add -A && git_q -C "$WORK/taste-repo" commit -q -m "v2"
OUT3="$( cd "$LOCAL" && NO_COMMIT=1 ./sync-taste-skill.sh 2>&1 )"
[ "$(cat "$LOCAL/taste-skill/SKILL.md")" = "upstream v2" ] && pass "NO_COMMIT=1 updates file" || fail "file not updated with NO_COMMIT"
DIFF="$(git_q -C "$LOCAL" status --porcelain)"
[ -n "$DIFF" ] && pass "NO_COMMIT=1 leaves working tree dirty without commit" || fail "commit unexpectedly made with NO_COMMIT"

# --- Run 4: tag provenance ---
git_q -C "$WORK/taste-repo" tag v2.0.0-exp
git_q -C "$LOCAL" reset --hard HEAD -q
OUT4="$( cd "$LOCAL" && ./sync-taste-skill.sh 2>&1 )"
COMMIT_MSG4="$(git_q -C "$LOCAL" log -n 1 --pretty=format:"%s")"
echo "$COMMIT_MSG4" | grep -q "chore: sync taste-skill v2.0.0-exp" && pass "git commit subject carries exact tag" || fail "tag provenance missing: $COMMIT_MSG4"

if [ "$FAILS" -eq 0 ]; then
  echo "ALL TASTE-SKILL TESTS PASSED"
  exit 0
else
  echo "FAILED: $FAILS test(s)" >&2
  exit 1
fi
