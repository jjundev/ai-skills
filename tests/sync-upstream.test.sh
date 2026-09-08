#!/usr/bin/env bash
# Tests sync-upstream.sh against fake local upstream repos.
# Run: ./tests/sync-upstream.test.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "ok: $*"; }

git_q() { git -c user.name=t -c user.email=t@t -c commit.gpgsign=false "$@"; }

# Build a fake upstream repo with the given skill dirs / files under skills/.
make_upstream() {
  local dir="$1"; shift
  mkdir -p "$dir/skills"
  local entry
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

make_upstream "$WORK/superpowers" brainstorming/ writing-plans/ lean-build/ compile.mjs
make_upstream "$WORK/caveman" caveman/ cavecrew/ registry.json

# Fake local skills repo containing the script under test.
LOCAL="$WORK/local"
mkdir -p "$LOCAL/brainstorming" "$LOCAL/lean-build"
cp "$HERE/sync-upstream.sh" "$LOCAL/sync-upstream.sh"
printf 'old\n' > "$LOCAL/brainstorming/SKILL.md"
printf 'stale\n' > "$LOCAL/brainstorming/stale.md"        # must disappear
printf 'local only\n' > "$LOCAL/lean-build/SKILL.md"      # not allowlisted: must be left alone
git_q -C "$LOCAL" init -q
git_q -C "$LOCAL" add -A
git_q -C "$LOCAL" commit -q -m init
printf 'mine\n' > "$LOCAL/mine.txt"                        # unrelated, uncommitted: must stay untracked

export SUPERPOWERS_REPO="file://$WORK/superpowers"
export CAVEMAN_REPO="file://$WORK/caveman"

# --- Run 1: real sync with commit ---
OUT1="$( cd "$LOCAL" && ./sync-upstream.sh 2>&1 )" || { echo "$OUT1"; fail "run 1 exited non-zero"; }

[ "$(cat "$LOCAL/brainstorming/SKILL.md")" = "upstream brainstorming/" ] && pass "allowlisted skill copied" || fail "brainstorming not updated"
[ ! -e "$LOCAL/brainstorming/stale.md" ] && pass "stale file removed by delete-then-copy" || fail "stale.md survived"
[ "$(cat "$LOCAL/caveman/SKILL.md")" = "upstream caveman/" ] && pass "caveman copied" || fail "caveman not copied"
[ ! -e "$LOCAL/compile.mjs" ] && [ ! -e "$LOCAL/registry.json" ] && pass "build files not copied" || fail "build file leaked"
[ ! -e "$LOCAL/cavecrew" ] && pass "non-allowlisted upstream skill not copied" || fail "cavecrew leaked"
[ "$(cat "$LOCAL/lean-build/SKILL.md")" = "local only" ] && pass "non-allowlisted local dir untouched" || fail "lean-build was modified"
echo "$OUT1" | grep -q "WARN:.*writing-skills" && pass "missing upstream skill warns" || fail "no WARN for missing writing-skills"
[ "$(git -C "$LOCAL" status --short mine.txt)" = "?? mine.txt" ] && pass "unrelated file left untracked" || fail "mine.txt was staged or committed"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "one sync commit created" || fail "expected 2 commits, got $(git -C "$LOCAL" rev-list --count HEAD)"
CHANGED="$(git -C "$LOCAL" show --name-only --pretty=format: HEAD | cut -d/ -f1 | sort -u | tr '\n' ' ')"
[ "$CHANGED" = "brainstorming caveman writing-plans " ] && pass "commit touches only synced dirs" || fail "commit touched: $CHANGED"

# --- Run 2: nothing changed upstream ---
OUT2="$( cd "$LOCAL" && ./sync-upstream.sh 2>&1 )" || fail "run 2 exited non-zero"
echo "$OUT2" | grep -q "already up-to-date" && pass "no-op run reports up-to-date" || fail "run 2 output: $OUT2"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "no-op run makes no commit" || fail "run 2 created a commit"

# --- Run 3: NO_COMMIT=1 leaves changes uncommitted ---
printf 'upstream v2\n' > "$WORK/superpowers/skills/brainstorming/SKILL.md"
git_q -C "$WORK/superpowers" commit -q -am v2
OUT3="$( cd "$LOCAL" && NO_COMMIT=1 ./sync-upstream.sh 2>&1 )" || fail "run 3 exited non-zero"
[ "$(cat "$LOCAL/brainstorming/SKILL.md")" = "upstream v2" ] && pass "NO_COMMIT still copies" || fail "NO_COMMIT did not copy"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "NO_COMMIT makes no commit" || fail "NO_COMMIT committed"

if [ "$FAILS" -eq 0 ]; then echo "ALL PASSED"; else echo "$FAILS FAILED"; exit 1; fi
