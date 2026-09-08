---
name: wattly-run
description: >
  Build and launch the current worktree Debug build of Wattly after terminating any running instance.
  MUST USE when the user wants to run, test, or launch the current development build —
  e.g. "실행해줘", "앱 실행해줘", "현재 워크트리 빌드 실행", "디버그 빌드 실행", "/wattly-run", "wattly run".
  NOT for: installing or deploying to /Applications (use wattly-install).
---

# wattly-run

현재 실행 중인 Wattly 프로세스를 안전하게 종료하고, 현재 워크트리의 최신 소스코드를 Debug 모드로 빌드하여 격리된 임시 경로(`/tmp/WattlyDerivedData`)에서 즉시 실행 및 검증하는 개발 루프 스킬입니다. `/Applications/Wattly.app`을 건드리지 않고 로컬 워크트리의 변경 사항을 빠르게 테스트합니다.

## 원칙

1. **로컬 개발 격리 (No Touch /Applications)**: `/Applications/Wattly.app`을 삭제하거나 덮어쓰지 않습니다. 빌드 산출물은 `/tmp/WattlyDerivedData`에 격리 보관됩니다.
2. **엄격한 단계별 종료 조건 (Checkable Completion Criteria)**: 프로세스 종료 -> Debug 빌드 -> 실행 및 바이너리 검증의 각 단계가 판별 가능한 조건을 통과해야 다음 단계로 진행합니다.
3. **샌드박스 권한 준수**: 프로세스 시그널 전송(`killall`, `pkill`) 및 macOS GUI 앱 실행(`open`) 시 `BypassSandbox: true`를 적용합니다.

---

## 실행 단계 (Step-by-Step)

### Step 1: 실행 중인 Wattly 프로세스 종료
현재 실행 중인 기존 Wattly 인스턴스를 안전하게 종료합니다.
```bash
killall Wattly 2>/dev/null || true
```
* **Completion Criterion**: `test -z "$(pgrep -x Wattly)"` 명령이 exit code 0을 반환해야 합니다. (정리되지 않을 경우 `pkill -9 -x Wattly` 후 재확인)

### Step 2: 현재 워크트리 Debug 빌드
현재 작업 디렉토리의 워크트리 코드로 Debug 빌드를 수행합니다.
```bash
xcodebuild -scheme Wattly -configuration Debug -derivedDataPath /tmp/WattlyDerivedData build
```
* **Completion Criterion**:
  - `xcodebuild` 명령이 exit code 0으로 완료되어야 합니다.
  - `test -d /tmp/WattlyDerivedData/Build/Products/Debug/Wattly.app` 명령이 exit code 0을 반환해야 합니다.

### Step 3: 앱 실행 및 바이너리 경로 검증
빌드된 Debug 앱 번들을 실행하고, 현재 실행된 프로세스가 해당 바이너리인지 확인합니다.
```bash
open /tmp/WattlyDerivedData/Build/Products/Debug/Wattly.app
```
실행 직후 프로세스를 검증합니다:
```bash
pgrep -fl Wattly
```
* **Completion Criterion**:
  - `pgrep -x Wattly` 결과 PID가 1개 이상 존재해야 합니다.
  - `ps -p $(pgrep -x Wattly | head -n 1) -o command=` 또는 `lsof -p $(pgrep -x Wattly | head -n 1)` 출력에 `/tmp/WattlyDerivedData/Build/Products/Debug/Wattly.app/Contents/MacOS/Wattly` 경로가 포함되어야 합니다.
