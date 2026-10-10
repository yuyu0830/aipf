# Change: Markdown 중심 구조 개편

## 사용자 의도

저장소를 clone한 뒤 별도 설치 없이 `project/PROJECT_SPEC.md`만 작성해 사용할 수 있는 Markdown 중심 프로젝트로 AIPF를 재구성한다.

## 전체 목표와의 연결

대화가 없어도 파일과 Git 기록으로 프로젝트를 이해하고 이어갈 수 있게 하되, 기존 관리 객체와 CLI의 운영 부담을 제거한다.

## 포함 범위

- Python CLI와 Plan·Task·Evidence·Audit·runtime 제거
- Project, Change, Archive, Instructions, Inputs, Knowledge, versioned source 구조 생성
- Git branch 기반 분기·복귀와 로컬 Project Flow 규칙 정의
- 적대적 검토·변호 검증, 자동 commit·push, 최종 Telegram 알림 규칙 정의
- 기존 `PROJECT_SPEC.md` 템플릿을 새 용어와 경로에 맞게 유지

## 제외 범위

- 기존 CLI 프로젝트 자동 변환
- 상주 서비스나 별도 실행 프로그램
- Telegram 응답·승인·polling
- 프로젝트별 실제 실행 진입점 구현

## 예상 상태 변경

- 저장소 기본 브랜치 자체가 clone-ready 템플릿이 된다.
- `dev/`, `example/`, Python 패키지와 관리 객체를 제거한다.
- 에이전트가 Markdown 지침에 따라 Git과 외부 알림을 직접 수행한다.

## Plan

### 1. 기준 구조

- 대상: 루트 문서와 canonical 폴더
- 작업: clone-ready Markdown 구조를 만든다.
- 결과물: `AGENTS.md`, `MEMORY_MAP.md`, `README.md`, `project/`, `instructions/`, `change/`, `archive/`, `inputs/`, `knowledge/`, `src/`
- 제외: 프로젝트별 실제 구현과 실행 진입점
- 검증: 필수 경로 존재와 ownership 문서 일치 확인

### 2. 동작 지침

- 대상: `instructions/`와 라우팅 문서
- 작업: 합의된 계획·코드·자료·검증·보고·Git·종료·Handoff 규칙을 작성한다.
- 결과물: Instructions 9개와 `AGENTS.md` 라우팅
- 제외: 상주 runner, CLI, 자동화 프로그램
- 검증: 각 사용자 동작이 정확히 한 지침 경로로 연결되는지 확인

### 3. 기존 구조 제거

- 대상: `dev/`, `example/`, Python 패키지, 생성·배포 스크립트
- 작업: 설치형 구현과 기존 관리 객체를 제거한다.
- 결과물: Git 삭제 내역과 clean-slate 제한 문서
- 제외: 기존 프로젝트 자동 변환
- 검증: 제거 대상 추적 파일이 남지 않았는지 확인

### 4. 구조 검증

- 대상: 새 추적 파일과 경로 참조
- 작업: 필수 파일, ignored Flow, Markdown 링크, Git diff, 오래된 구현 경로를 검사한다.
- 결과물: 검증 결과 기록
- 제외: 의도적으로 과거 구조를 설명하는 현재 Change 문구
- 검증: 정적 검사 명령 통과

### 5. 독립 검토

- 대상: 전체 Git diff와 새 문서
- 작업: 공격 검토, 변호, 주 에이전트 판정을 수행한다.
- 결과물: finding별 판정과 수정 내역
- 제외: 검토 에이전트의 파일 수정
- 검증: 모든 blocker와 important finding이 해결되거나 사용자 판단 대상으로 기록됨

## 검증 방법

- 추적 파일 목록과 canonical tree 비교
- Markdown 링크와 경로 존재 검사
- 추적 대상에서 `.aipf/`, `dev/`, `example/`, `pyproject.toml`, Python package, runtime/config 객체 경로가 제거됐는지 검사
- 현재 Change에서 과거 구조를 설명하는 문구는 허용
- Git diff와 변경 범위 검토

## 진행 상태

- 상태: `completed`
- 기준 commit: `0729a721227e815954a11056a527b90cffbdfa1b`

## 검증 결과

### Plan 적대적 검토

- 실행 경계·상태 기준·Git 실패 복구·검증 역할·Flow ref 범위가 불명확하다는 지적을 수용했다.
- `README.md`, `MEMORY_MAP.md`, `VERIFICATION.md`, `GIT.md`, `END_CHANGE.md`에 해당 규칙을 추가했다.
- 이전 CLI 프로젝트 자동 변환은 지원하지 않는 clean-slate 개편으로 명시했다.

### 구조 검사

- 필수 문서·폴더 존재: 통과
- `PROJECT_FLOW.md`와 `.obsidian/` Git 제외: 통과
- 제거된 구현 경로 잔존 참조: 통과
- `git diff --check`: 통과

### Change 공격 검토

| 위치 | 공격 주장·영향 | 근거·권고 | 방어 | 최종 판정 |
|---|---|---|---|---|
| `CHANGE.md`, `HANDOFF.md` | 검토 증거가 없어 완료 검토를 감사할 수 없음 | `VERIFICATION.md` 형식으로 판정 기록 | 기록은 생겼지만 상세 근거는 부족하므로 일부 수용 | 수용. 이 표에 위치·영향·근거·처리를 남김 |
| `PROJECT_STATUS.md` | 활성 Change와 상태가 달라 새 에이전트가 작업을 놓침 | 현재 Change와 검토 위치 기록 | 수정본은 현재 Change와 일치하므로 기각 | 초기 지적 수용·수정 완료 |
| `HANDOFF.md` | HEAD·파일 상태·명령 결과가 없어 재개가 불안정함 | 정확한 Git 상태와 검사 결과 기록 | 현재 설명은 맞지만 필수 Git 정보가 부족해 일부 수용 | 수용. HEAD, 파일 상태, 명령과 결과 추가 |
| `PROJECT_FLOW.md` | release ref가 빠져 전체 흐름이 아님 | local·remote release ref 포함 | 수정본에 모든 release ref가 있어 기각 | 초기 지적 수용·수정 완료 |
| `CHANGE.md` Plan | 항목별 범위와 합격 조건을 확인할 수 없음 | 대상·작업·결과물·제외·검증 명시 | 수정본은 5개 필드를 모두 충족하므로 기각 | 초기 지적 수용·수정 완료 |
| 검증 문구 | 단어 검색은 의도적 과거 설명까지 실패시킴 | 구현 경로 중심 검사와 설명 예외 명시 | 수정본은 추적 경로 중심이며 예외가 있어 기각 | 초기 지적 수용·수정 완료 |
| 로컬 `__pycache__` | 폴더 검사에서 과거 구조가 남은 것처럼 보임 | 삭제하거나 추적 파일만 검사 | Git에서 무시되며 clone에 포함되지 않아 기각 | 기각. 배포 결과와 무관하며 검사는 이를 제외함 |

### 주 에이전트 결정

- 공격 검토에서 확인한 6개 문서 문제는 수정했다. 로컬 cache 지적은 결과물과 무관해 기각했다.
- 방어 검토에서 추가로 확인한 빈 `change/` 소실 문제는 `change/.gitkeep`으로 막았다.
- 완료 시 현재 Change는 규칙대로 archive하고, `PROJECT_STATUS.md`는 활성 Change 없음과 `PROJECT_SPEC.md` 작성이라는 초기 다음 행동을 표시해야 한다.
- 현재 구현 범위에는 blocker와 미해결 사용자 판단 사항이 없다.

### 최종 정적 검사

- 필수 경로, 현재 버전, Git 제외 규칙: 통과
- 제거 대상 추적 파일과 과거 구현 파일: 통과
- 상대 Markdown 링크와 비밀값 저장 검사: 통과
- `git diff --check`: 통과

## 최종 결과

- 구현 commit: `51ea5b2`
- 검토 기록 commit: `38d39e2`
- 사용자 최종 확인: 완료
- 결과: 설치 없는 Markdown 중심 clone-ready 프로젝트 틀 완성
