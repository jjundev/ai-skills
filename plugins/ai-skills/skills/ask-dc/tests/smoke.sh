#!/usr/bin/env bash
# Live checks against gall.dcinside.com. Run manually; needs network.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DC=(node "${DIR}/scripts/dc.mjs")
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }
count() { node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).length))'; }
field() { node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s)[Number(process.argv[1])][process.argv[2]]))' "$1" "$2"; }

n=$("${DC[@]}" list shaving --search 브라운 --recommend --limit 5 | count); [ "$n" -ge 1 ] && pass "general search+recommend ($n rows)" || fail "general search"
url=$("${DC[@]}" list laptop --limit 3 | field 0 url); [[ "$url" == *"/mgallery/board/view/"* ]] && pass "minor auto-detect ($url)" || fail "minor auto-detect: $url"
url=$("${DC[@]}" list soopstreaming --limit 3 | field 0 url); [[ "$url" == *"/mini/board/view/"* ]] && pass "mini auto-detect" || fail "mini auto-detect: $url"
n=$("${DC[@]}" read "https://gall.dcinside.com/board/view/?id=shaving&no=39837" --comment-limit 5 | count); [ "$n" -ge 2 ] && pass "read general with comments ($n rows)" || fail "read general"
big=$("${DC[@]}" list dcbest --limit 30 | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).sort((a,b)=>b.commentCount-a.commentCount)[0];console.log(r.url)})')
n=$("${DC[@]}" read "$big" --comment-limit 50 | count); [ "$n" -ge 40 ] && pass "comment paging ($n rows from $big)" || fail "comment paging: $n rows"
set +e; "${DC[@]}" read "https://gall.dcinside.com/board/view/?id=shaving&no=99999999" >/dev/null 2>&1; code=$?; set -e
[ "$code" -eq 4 ] && pass "missing post exits 4" || fail "missing post exit $code"
set +e; "${DC[@]}" list shaving --search 존재하지않는검색어zzqx >/dev/null 2>&1; code=$?; set -e
[ "$code" -eq 3 ] && pass "zero results exits 3" || fail "zero results exit $code"
if command -v opencli >/dev/null 2>&1; then
  opencli dcinside list shaving --limit 2 -f yaml >/dev/null && pass "opencli dcinside list (browserless)" || fail "opencli list"
fi
echo "All smoke checks passed."
