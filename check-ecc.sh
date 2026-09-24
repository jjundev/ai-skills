#!/usr/bin/env bash
# ==============================================================================
# check-ecc.sh
# Check whether local ECC skills are up-to-date with upstream (affaan-m/ECC).
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
    echo "Checks upstream commit status for curated ECC skills."
    exit 0
  fi
done

# Safe git command helper
run_git() {
  GIT_CONFIG_GLOBAL=/dev/null git -C "$SKILLS_DIR" "$@" 2>/dev/null || true
}

if [ "$JSON_MODE" = false ]; then
  echo -e "${BOLD}${CYAN}=====================================================${RESET}"
  echo -e "${BOLD}${CYAN}            ECC Skills Status Check                  ${RESET}"
  echo -e "${BOLD}${CYAN}=====================================================${RESET}\n"
fi

# ------------------------------------------------------------------------------
# ECC Upstream Check (affaan-m/ECC)
# ------------------------------------------------------------------------------
LOCAL_ECC_COMMIT_MSG=$(run_git log --grep="sync ecc" -n 1 --pretty=format:"%s")
LOCAL_ECC_SHA=$(echo "$LOCAL_ECC_COMMIT_MSG" | grep -oE "\([a-f0-9]{7}\)" | tr -d "()" || echo "unknown")
LOCAL_ECC_COMMIT=$(run_git log --grep="sync ecc" -n 1 --pretty=format:"%h (%cr)")

UPSTREAM_ECC_COMMITS_JSON=$(curl -s --connect-timeout 5 -H "User-Agent: ai-skills-checker" "https://api.github.com/repos/affaan-m/ECC/commits?per_page=1" 2>/dev/null || echo "[]")
UPSTREAM_ECC_HEAD_SHA=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['sha'][:7] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_ECC_COMMITS_JSON")
UPSTREAM_ECC_HEAD_DATE=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['commit']['committer']['date'][:10] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_ECC_COMMITS_JSON")
UPSTREAM_ECC_HEAD_MSG=$(python3 -c "import json, sys;
try:
  d = json.loads(sys.argv[1]); print(d[0]['commit']['message'].split('\n')[0] if isinstance(d, list) and d else '')
except: pass" "$UPSTREAM_ECC_COMMITS_JSON")

ECC_UP_TO_DATE=false
if [ -n "$UPSTREAM_ECC_HEAD_SHA" ] && [ "$LOCAL_ECC_SHA" = "$UPSTREAM_ECC_HEAD_SHA" ]; then
  ECC_UP_TO_DATE=true
fi

# ------------------------------------------------------------------------------
# Output Results
# ------------------------------------------------------------------------------
if [ "$JSON_MODE" = true ]; then
  python3 -c "import json
result = {
  'ecc': {
    'local_synced_sha': '$LOCAL_ECC_SHA',
    'local_commit': '$LOCAL_ECC_COMMIT',
    'upstream_head_sha': '$UPSTREAM_ECC_HEAD_SHA',
    'upstream_head_date': '$UPSTREAM_ECC_HEAD_DATE',
    'upstream_head_msg': '$UPSTREAM_ECC_HEAD_MSG',
    'up_to_date': $([ "$ECC_UP_TO_DATE" = true ] && echo "True" || echo "False")
  }
}
print(json.dumps(result, indent=2))"
  exit 0
fi

# Terminal Display
echo -e "${BOLD}[ECC Skills]${RESET} ${GRAY}(https://github.com/affaan-m/ECC)${RESET}"
echo -e "  • 로컬 적용 커밋 : ${BOLD}${LOCAL_ECC_SHA}${RESET} ${GRAY}[${LOCAL_ECC_COMMIT:-최초 동기화 필요}]${RESET}"
if [ -n "$UPSTREAM_ECC_HEAD_SHA" ]; then
  echo -e "  • 업스트림 HEAD  : ${BOLD}${UPSTREAM_ECC_HEAD_SHA}${RESET} ${GRAY}(${UPSTREAM_ECC_HEAD_DATE} - ${UPSTREAM_ECC_HEAD_MSG})${RESET}"
else
  echo -e "  • 업스트림 HEAD  : ${YELLOW}확인 불가 (오프라인 또는 API 제한)${RESET}"
fi

if [ "$ECC_UP_TO_DATE" = true ]; then
  echo -e "  • 상태           : ${GREEN}✅ 최신 버전 동기화 상태${RESET}"
elif [ -z "$UPSTREAM_ECC_HEAD_SHA" ]; then
  echo -e "  • 상태           : ${YELLOW}⚠️ 네트워크 상태 확인 필요${RESET}"
elif [ "$LOCAL_ECC_SHA" = "unknown" ]; then
  echo -e "  • 상태           : ${YELLOW}⚡ 최초 동기화 필요 (아직 가져오지 않음)${RESET}"
else
  echo -e "  • 상태           : ${YELLOW}⚡ 업데이트 가능 (${LOCAL_ECC_SHA} -> ${UPSTREAM_ECC_HEAD_SHA})${RESET}"
fi

echo -e "\n${BOLD}${CYAN}=====================================================${RESET}"
if [ "$ECC_UP_TO_DATE" = true ]; then
  echo -e "${GREEN}✨ ECC 선별 스킬셋이 최신 상태입니다.${RESET}"
else
  echo -e "💡 최신 버전을 다운로드하여 동기화하려면 다음을 실행하세요:"
  echo -e "   ${BOLD}bash $SKILLS_DIR/sync-ecc.sh${RESET}"
fi
echo -e "${BOLD}${CYAN}=====================================================${RESET}"
