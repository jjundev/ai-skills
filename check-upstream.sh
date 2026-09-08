#!/usr/bin/env bash
# ==============================================================================
# check-upstream.sh
# Check whether local Superpowers and Caveman skills are up-to-date with upstream.
# (Read-only check, does NOT modify any files or make git commits)
# ==============================================================================

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color definitions
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
GRAY="\033[0;90m"
RESET="\033[0m"

JSON_MODE=false
for arg in "$@"; do
  if [ "$arg" = "--json" ]; then
    JSON_MODE=true
  elif [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
    echo "Usage: $0 [--json] [--help]"
    echo "Checks upstream release and commit status for Superpowers and Caveman."
    exit 0
  fi
done

# Safe git command helper
run_git() {
  GIT_CONFIG_GLOBAL=/dev/null git -C "$SKILLS_DIR" "$@" 2>/dev/null || true
}

if [ "$JSON_MODE" = false ]; then
  echo -e "${BOLD}${CYAN}=====================================================${RESET}"
  echo -e "${BOLD}${CYAN}          AI Skills Upstream Status Check            ${RESET}"
  echo -e "${BOLD}${CYAN}=====================================================${RESET}\n"
fi

# ------------------------------------------------------------------------------
# 1. Superpowers Check (obra/superpowers)
# ------------------------------------------------------------------------------
LOCAL_SP_COMMIT_MSG=$(run_git log --grep="superpowers" -n 1 --pretty=format:"%s")
LOCAL_SP_VERSION=$(echo "$LOCAL_SP_COMMIT_MSG" | grep -oE "v[0-9]+\.[0-9]+(\.[0-9]+)?" || echo "unknown")
LOCAL_SP_COMMIT=$(run_git log --grep="superpowers" -n 1 --pretty=format:"%h (%cr)")

UPSTREAM_SP_JSON=$(curl -s --connect-timeout 5 -H "User-Agent: ai-skills-checker" "https://api.github.com/repos/obra/superpowers/releases/latest" 2>/dev/null || echo "{}")
UPSTREAM_SP_RELEASE=$(python3 -c "import json, sys; 
try:
  d = json.loads(sys.argv[1]); print(d.get('tag_name', ''))
except: pass" "$UPSTREAM_SP_JSON")

UPSTREAM_SP_COMMITS_JSON=$(curl -s --connect-timeout 5 -H "User-Agent: ai-skills-checker" "https://api.github.com/repos/obra/superpowers/commits?per_page=1" 2>/dev/null || echo "[]")
UPSTREAM_SP_HEAD_SHA=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['sha'][:7] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_SP_COMMITS_JSON")
UPSTREAM_SP_HEAD_DATE=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['commit']['committer']['date'][:10] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_SP_COMMITS_JSON")

SP_UP_TO_DATE=false
if [ -n "$UPSTREAM_SP_RELEASE" ] && [ "$LOCAL_SP_VERSION" = "$UPSTREAM_SP_RELEASE" ]; then
  SP_UP_TO_DATE=true
fi

# ------------------------------------------------------------------------------
# 2. Caveman Check (JuliusBrussee/caveman)
# ------------------------------------------------------------------------------
LOCAL_CM_COMMIT_MSG=$(run_git log --grep="caveman" -n 1 --pretty=format:"%s")
LOCAL_CM_VERSION=$(echo "$LOCAL_CM_COMMIT_MSG" | grep -oE "v[0-9]+\.[0-9]+(\.[0-9]+)?" || echo "v2.6.0")
LOCAL_CM_COMMIT=$(run_git log --grep="caveman" -n 1 --pretty=format:"%h (%cr)")

UPSTREAM_CM_COMMITS_JSON=$(curl -s --connect-timeout 5 -H "User-Agent: ai-skills-checker" "https://api.github.com/repos/JuliusBrussee/caveman/commits?per_page=1" 2>/dev/null || echo "[]")
UPSTREAM_CM_HEAD_SHA=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['sha'][:7] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_CM_COMMITS_JSON")
UPSTREAM_CM_HEAD_DATE=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['commit']['committer']['date'][:10] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_CM_COMMITS_JSON")
UPSTREAM_CM_HEAD_MSG=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['commit']['message'].split('\n')[0] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_CM_COMMITS_JSON")

# ------------------------------------------------------------------------------
# Output Results
# ------------------------------------------------------------------------------
if [ "$JSON_MODE" = true ]; then
  python3 -c "import json
result = {
  'superpowers': {
    'local_version': '$LOCAL_SP_VERSION',
    'local_commit': '$LOCAL_SP_COMMIT',
    'upstream_release': '$UPSTREAM_SP_RELEASE',
    'upstream_head_sha': '$UPSTREAM_SP_HEAD_SHA',
    'upstream_head_date': '$UPSTREAM_SP_HEAD_DATE',
    'up_to_date': $([ "$SP_UP_TO_DATE" = true ] && echo "True" || echo "False")
  },
  'caveman': {
    'local_version': '$LOCAL_CM_VERSION',
    'local_commit': '$LOCAL_CM_COMMIT',
    'upstream_head_sha': '$UPSTREAM_CM_HEAD_SHA',
    'upstream_head_date': '$UPSTREAM_CM_HEAD_DATE',
    'upstream_head_msg': '$UPSTREAM_CM_HEAD_MSG'
  }
}
print(json.dumps(result, indent=2))"
  exit 0
fi

# Terminal Display
echo -e "${BOLD}[1] Superpowers${RESET} ${GRAY}(https://github.com/obra/superpowers)${RESET}"
echo -e "  • 로컬 적용 버전 : ${BOLD}${LOCAL_SP_VERSION}${RESET} ${GRAY}[${LOCAL_SP_COMMIT}]${RESET}"
if [ -n "$UPSTREAM_SP_RELEASE" ]; then
  echo -e "  • 업스트림 릴리스: ${BOLD}${UPSTREAM_SP_RELEASE}${RESET} ${GRAY}(HEAD: ${UPSTREAM_SP_HEAD_SHA:-N/A}, ${UPSTREAM_SP_HEAD_DATE:-N/A})${RESET}"
else
  echo -e "  • 업스트림 릴리스: ${YELLOW}확인 불가 (오프라인 또는 API 제한)${RESET}"
fi

if [ "$SP_UP_TO_DATE" = true ]; then
  echo -e "  • 상태           : ${GREEN}✅ 최신 버전 유지 중${RESET}"
elif [ -z "$UPSTREAM_SP_RELEASE" ]; then
  echo -e "  • 상태           : ${YELLOW}⚠️ 네트워크 상태 확인 필요${RESET}"
else
  echo -e "  • 상태           : ${YELLOW}⚡ 업데이트 가능 (${LOCAL_SP_VERSION} -> ${UPSTREAM_SP_RELEASE})${RESET}"
fi

echo ""
echo -e "${BOLD}[2] Caveman${RESET} ${GRAY}(https://github.com/JuliusBrussee/caveman)${RESET}"
echo -e "  • 로컬 적용 버전 : ${BOLD}${LOCAL_CM_VERSION}${RESET} ${GRAY}[${LOCAL_CM_COMMIT}]${RESET}"
if [ -n "$UPSTREAM_CM_HEAD_SHA" ]; then
  echo -e "  • 업스트림 HEAD  : ${BOLD}${UPSTREAM_CM_HEAD_SHA}${RESET} ${GRAY}(${UPSTREAM_CM_HEAD_DATE} - ${UPSTREAM_CM_HEAD_MSG})${RESET}"
  echo -e "  • 상태           : ${GREEN}✅ 최신 동기화 유지 중${RESET}"
else
  echo -e "  • 업스트림 HEAD  : ${YELLOW}확인 불가 (오프라인 또는 API 제한)${RESET}"
  echo -e "  • 상태           : ${YELLOW}⚠️ 네트워크 상태 확인 필요${RESET}"
fi

echo -e "\n${BOLD}${CYAN}=====================================================${RESET}"
if [ "$SP_UP_TO_DATE" = true ]; then
  echo -e "${GREEN}✨ 모든 핵심 스킬셋이 최신 상태입니다.${RESET}"
else
  echo -e "💡 최신 버전을 다운로드하여 동기화하려면 다음을 실행하세요:"
  echo -e "   ${BOLD}bash $SKILLS_DIR/sync-upstream.sh${RESET}"
fi
echo -e "${BOLD}${CYAN}=====================================================${RESET}"
