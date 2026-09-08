---
name: wattly-install
description: >
  Clean existing installations and install the latest Wattly release build to /Applications.
  MUST USE when the user wants to clean-install, reinstall, or deploy Wattly to /Applications —
  e.g. "wattly 설치", "최신 빌드로 설치", "기존 wattly 지우고 새로 설치", "wattly 배포", "/wattly-install".
  NOT for: running or testing the current worktree debug build locally — use wattly-run instead.
---

# wattly-install

기존 실행 중인 Wattly 프로세스와 구버전 설치본을 완전히 정리하고, 최신 `main` 브랜치 코드로 Release 빌드를 생성하여 `/Applications/Wattly.app`에 단일 설치 및 검증하는 스킬입니다.

## 원칙

1. **단일 설치 대상 (Single Target of Truth)**: 모든 Wattly 설치본은 `/Applications/Wattly.app` 하나만 유지합니다. Spotlight, Raycast, LaunchServices 등 시스템 전반에서도 개발/임시 빌드본이 중복 탐지되지 않도록 완전히 단일화(Deduplication)합니다.
2. **순차 실행 (Deterministic Order)**: 프로세스 종료 -> 기존 파일 제거 -> Release 빌드 -> 복사 -> 중복 빌드본 및 캐시 정리(LaunchServices/Spotlight) -> 검증 및 실행 순서를 엄격히 준수합니다. 이전 단계의 **종료 조건(Completion Criterion)**이 만족되지 않으면 다음 단계로 넘어가지 않습니다.
3. **샌드박스 권한 준수**: 프로세스 시그널 전송, Xcode 빌드 도구 체인 접근, `/Applications` 파일 수정, GUI 앱 실행(`open`), LaunchServices 및 Spotlight 관리 작업 시 `BypassSandbox: true`를 적용합니다.

---

## 실행 단계 (Step-by-Step)

### Step 1: 실행 중인 Wattly 프로세스 종료
실행 중인 기존 Wattly UI 프로세스를 안전하게 종료합니다.
```bash
killall Wattly || true
```
* **Completion Criterion**: `pgrep -x Wattly`의 출력이 비어 있어야 합니다.

### Step 2: 기존 설치본 제거
`/Applications` 내의 기존 구버전 앱 번들을 삭제합니다.
```bash
rm -rf /Applications/Wattly.app
```
* **Completion Criterion**: `test ! -e /Applications/Wattly.app` 명령이 exit code 0을 반환해야 합니다.

### Step 3: 최신 Release 빌드 수행
프로젝트 루트에서 제공되는 릴리스 빌드 스크립트를 실행합니다. 스크립트 내부에서 xcodebuild 및 임베디드 헬퍼(`WattlyFanDaemon`) 바이너리 포함 여부를 자동 검증합니다.
```bash
bash scripts/build_release.sh
```
* **Completion Criterion**:
  - `.build/DerivedData/Build/Products/Release/Wattly.app` 디렉토리가 존재해야 합니다.
  - `.build/DerivedData/Build/Products/Release/Wattly.app/Contents/Helpers/WattlyFanDaemon` 파일이 존재하고 실행 권한(`-x`)이 있어야 합니다.
  - `build/Release/Wattly.zip` 파일이 생성되어야 합니다.

### Step 4: `/Applications/`에 최신 빌드 배포
새로 빌드된 Release 앱 번들을 `/Applications` 디렉토리로 복사합니다.
```bash
cp -R .build/DerivedData/Build/Products/Release/Wattly.app /Applications/Wattly.app
```
* **Completion Criterion**: `test -d /Applications/Wattly.app` 명령이 exit code 0을 반환해야 합니다.

### Step 5: 중복 빌드본 제거 및 시스템 캐시 정리 (LaunchServices & Spotlight)
Xcode 빌드 도중 등록된 중간 산출물과 과거 개발/워크트리/DerivedData의 잔여 `Wattly.app` 번들을 시스템 등록 데이터베이스(LaunchServices)와 Spotlight 인덱스에서 정리합니다.

1. `/Applications/Wattly.app`을 제외한 모든 잔여 번들을 LaunchServices에서 등록 해제하고 디렉토리를 정리합니다:
```bash
python3 -c '
import subprocess, os, shutil

lsreg = "/System/Library/Frameworks/CoreServices.framework/Versions/Current/Frameworks/LaunchServices.framework/Versions/Current/Support/lsregister"
try:
    output = subprocess.check_output([lsreg, "-dump"]).decode("utf-8", errors="ignore")
    paths = set()
    for line in output.splitlines():
        if "path:" in line and "Wattly.app" in line:
            path = line.split("path:")[1].split("(")[0].strip()
            paths.add(path)
    for p in paths:
        if p != "/Applications/Wattly.app":
            subprocess.run([lsreg, "-u", p], check=False)
            if os.path.exists(p):
                shutil.rmtree(p, ignore_errors=True)
except Exception:
    pass
'
```

2. Xcode DerivedData 및 로컬 `.build` 내 번들을 제거합니다:
```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/Wattly-* 2>/dev/null || true
rm -rf .build/DerivedData/Build/Products/Release/Wattly.app 2>/dev/null || true
```

3. LaunchServices DB 가비지 컬렉션을 실행하고 `/Applications/Wattly.app`을 정식 재등록합니다:
```bash
/System/Library/Frameworks/CoreServices.framework/Versions/Current/Frameworks/LaunchServices.framework/Versions/Current/Support/lsregister -gc
/System/Library/Frameworks/CoreServices.framework/Versions/Current/Frameworks/LaunchServices.framework/Versions/Current/Support/lsregister -f -R -trusted /Applications/Wattly.app
```

4. Spotlight 캐시를 갱신합니다:
```bash
mdimport /Applications/Wattly.app
killall Spotlight 2>/dev/null || true
```
* **Completion Criterion**:
  - `mdfind "kMDItemFSName == 'Wattly.app'"`의 출력이 `/Applications/Wattly.app` 단 1개여야 합니다.
  - `/System/Library/Frameworks/CoreServices.framework/Versions/Current/Frameworks/LaunchServices.framework/Versions/Current/Support/lsregister -dump | grep -i "path:.*Wattly\.app"` 결과에 `/Applications/Wattly.app`만 존재해야 합니다.

### Step 6: 코드 서명 검증 및 실행 확인
1. 코드 서명을 검증합니다:
   ```bash
   codesign --verify --deep --strict /Applications/Wattly.app
   ```
2. 버전 정보를 확인합니다:
   ```bash
   plutil -p /Applications/Wattly.app/Contents/Info.plist | grep -E "CFBundleShortVersionString|CFBundleVersion"
   ```
3. 앱을 실행합니다:
   ```bash
   open /Applications/Wattly.app
   ```
4. 실행 중인 바이너리 경로를 확인합니다:
   ```bash
   lsof -p $(pgrep -x Wattly) | grep -i "/Applications/Wattly.app/Contents/MacOS/Wattly"
   ```
* **Completion Criterion**: Wattly 프로세스가 정상 실행 중이어야 하며, 해당 프로세스의 실행 바이너리 경로가 `/Applications/Wattly.app/Contents/MacOS/Wattly`여야 합니다.

---

## 문제 해결 (Troubleshooting)

- **Helper Daemon 권한 에러**: 앱 실행 후 팬/배터리 제어 권한 문제가 발생할 경우, 내장된 헬퍼 스크립트로 권한을 재설정합니다:
  ```bash
  sudo bash scripts/install-fan-helper.sh
  ```
- **기존 프로세스 강제 종료 실패 시**:
  ```bash
  pkill -9 -x Wattly || true
  ```
- **Spotlight/런처 중복 지속 시**:
  LaunchServices 캐시와 Spotlight 메타데이터를 강제로 재구축합니다:
  ```bash
  /System/Library/Frameworks/CoreServices.framework/Versions/Current/Frameworks/LaunchServices.framework/Versions/Current/Support/lsregister -kill -r -domain local -domain user
  killall Spotlight
  ```
