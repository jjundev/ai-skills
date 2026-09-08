#!/usr/bin/env bash
# Structural check for grill-yourself/SKILL.md.
# Exit 0 = all constraints hold. Exit 1 = at least one violation, printed per line.
set -u
here="$(cd "$(dirname "$0")/.." && pwd)"
f="$here/SKILL.md"
fail=0

say() { echo "FAIL: $1"; fail=1; }

[ -f "$f" ] || { echo "FAIL: $f missing"; exit 1; }

# Frontmatter
head -1 "$f" | grep -q '^---$'                       || say "frontmatter must start with ---"
grep -q '^name: grill-yourself$' "$f"                || say "frontmatter name must be grill-yourself"
grep -q '^disable-model-invocation: true$' "$f"      || say "must stay manual-only (disable-model-invocation: true)"
grep -q '/grill-yourself' "$f"                       || say "description must mention /grill-yourself"

# Required sections (headings)
for h in "## Read-only" "## Procedure" "## Output format" "## Needs-you round" "## Overrides"; do
  grep -qF "$h" "$f" || say "missing section: $h"
done

# Required template headings inside the output format
for h in "## Intent" "## Behavior when done" "## Not in this round" "## Approaches" "## Implementation spec" "## Decisions" "### Confident" "### Needs you"; do
  grep -qF "$h" "$f" || say "missing template heading: $h"
done

# Kept-by-name features
grep -qF '#<n>=<value>' "$f"                          || say "override syntax #<n>=<value> missing"
grep -qF '[confirmed]' "$f"                           || say "[confirmed] marker missing"
grep -qF '[confirmed by default]' "$f"                || say "[confirmed by default] marker missing"
grep -qF 'file:line' "$f"                             || say "file:line evidence rule missing"
grep -qiF 'bounded' "$f"                              || say "bounded classification missing"
grep -qiF 'architectural' "$f"                        || say "architectural classification missing"

# Removed features must be gone
for bad in "--viz" "safety cap" "Unresolved areas" "Self-check" "grill-viz" "20 decisions"; do
  grep -qF -- "$bad" "$f" && say "stale reference still present: $bad"
done

# Size budget
size=$(wc -c < "$f" | tr -d ' ')
[ "$size" -le 5000 ] || say "SKILL.md is $size bytes, budget is 5000"

[ "$fail" -eq 0 ] && echo "OK: grill-yourself/SKILL.md passes structural check ($size bytes)"
exit $fail
