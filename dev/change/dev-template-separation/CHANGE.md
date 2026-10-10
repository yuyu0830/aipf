# Change: AIPF 개발과 적용 템플릿 분리

## 사용자 의도

AIPF 자체 개발과 AIPF로 다른 프로젝트를 개발하는 작업을 명확히 구분한다. 개발 자료는 `dev/`, 배포할 틀은 `template/`로 관리한다. 루트 README는 제거하고 `template/README.md`만 둔다. 배포는 `template/`의 추적 파일만 `release` 루트로 내보내며 규칙과 실행 절차를 문서화한다.

## 전체 목표와의 연결

대화 없이 문서와 Git으로 작업을 이어가는 AIPF의 목적을 유지하면서, 개발자가 빈 사용자 명세를 AIPF 자체 목표로 오인하는 문제를 해결한다.

## 포함 범위

- 루트 개발용 라우팅과 메모리 맵, `dev/` 개발 명세·상태·지침·기록·자료 공간
- 독립된 `template/`의 사용 지침·빈 명세·초기 상태·버전별 소스 공간
- `template/README.md`의 release clone 사용법과 개발 영역 구분
- `dev/scripts/update_release_branch.sh`, 배포 규칙과 격리된 Git 저장소 테스트
- 상대 링크, ignored Flow, 기존 기록 보존, 사용자 의도에 대한 독립 검토

## 제외 범위

- 기존 사용자 프로젝트의 자동 변환이나 덮어쓰기
- 이전 Python CLI 복원, 추가 기능 또는 개발용 README
- 사용자 최종 완료 확인 전 main 병합·태그·실제 release 갱신

## 예상 상태 변경

루트에서는 AIPF 자체 개발 문서를 읽고, 배포본에서는 적용 프로젝트 문서를 읽는다. AIPF 개발 기록은 배포본에 포함되지 않는다. 기존 release 이력을 보존하며 다음 배포부터 Markdown 템플릿을 배포한다.

### 경로 대응과 불변 조건

| 기존 경로 | 개발용 경로 | 배포용 경로 |
|---|---|---|
| `AGENTS.md`, `MEMORY_MAP.md` | 루트에서 dev 문서로 라우팅하도록 수정 | 독립된 `template/AGENTS.md`, `template/MEMORY_MAP.md` |
| `README.md` | 제거; 개발용 README 없음 | `template/README.md`만 유지 |
| `instructions/` | `dev/instructions/`로 이동하고 dev 경로로 수정 | 기존 사용자 프로젝트 규칙을 `template/instructions/`로 복사 |
| `project/PROJECT_SPEC.md` | 현재 Markdown 목적과 이번 지시로 dev 명세 신설 | 기존 빈 명세를 `template/project/`로 이동 |
| `project/PROJECT_STATUS.md` | 기존 완료 내역을 `dev/project/`에 보존·수정 | `template/project/`에는 구현 미착수 초기 상태 |
| `archive/` | `dev/archive/`로 이동; 과거 본문 유지 | `template/archive/`는 빈 초기 공간 |
| `change/` | 활성 Change는 `dev/change/` | `template/change/`는 빈 초기 공간 |
| `inputs/`, `knowledge/` | dev 전용 빈 공간·색인 생성 | 기존 빈 공간·색인은 `template/`로 이동 |
| `src/` | 현재 실제 개발 코드가 없으므로 이전하지 않음; 배포 도구는 `dev/scripts/` | 기존 빈 버전 구조는 `template/src/`로 이동 |
| `.gitignore`, 로컬 Flow | dev와 template의 Flow를 제외하도록 루트 규칙 수정 | `template/.gitignore`는 배포 루트 기준 규칙 |

- 루트에는 개발용 라우팅 두 문서와 Git 설정만 남기며 프로젝트 관리 폴더는 남기지 않는다.
- 개발 지침은 template 내부를 수정할 때도 적용한다. template의 지침은 배포할 문서이며 이 저장소에서 현재 작업을 지휘하지 않는다.
- archive 이동 후 상대 링크를 검사한다. 과거 시점의 경로·명령·결과를 기록한 본문은 당시 사실로 보존한다.
- 배포 tree ID는 source commit의 `template` tree ID와 정확히 같아야 한다. dotfile을 포함하며 개발 기록은 포함하지 않는다.

## Plan

| 단계 | 대상 | 작업 | 결과물 | 제외 | 검증 |
|---|---|---|---|---|---|
| 1 | 문서·폴더 | 기존 지침과 빈 템플릿을 분리하고 개발 기록 보존 | 루트 라우팅, `dev/`, `template/`, 루트 README 제거 | 과거 archive 본문 재작성 | 필수 경로·범위·링크·템플릿 초기 상태 확인 |
| 2 | 개발 명세·상태 | 기존 방향과 이번 사용자 지시를 근거로 AIPF 목표 및 진행 위치 명시 | `dev/project/PROJECT_SPEC.md`, `PROJECT_STATUS.md` | 과거 CLI 동작의 요구사항 재도입 | 개발/사용 목표 및 다음 행동 대조 |
| 3 | 배포 | main의 커밋된 template 트리를 release로 내보내는 스크립트와 규칙 작성 | 배포 스크립트, `dev/instructions/RELEASE.md` | 자동 강제 push·실제 배포 | Bash 문법과 격리 Git 시나리오 검사 |
| 4 | 검증·인계 | 공격/방어 검토, 변경 커밋·브랜치 push, 인계 | 검증 기록, HANDOFF | 최종 확인 이전 완료 처리 | 독립 검토와 구조 검사 통과 |

배포 스크립트는 쉘 함수 없이 작성한다. 입력은 `--check` 또는 `--push`(생략 시 로컬 갱신), 출력은 검사 결과 또는 release commit이다.

- clean main만 허용한다. origin이 있으면 기본/--push 모드는 fetch 후 main==origin/main을 확인하고, --check는 ls-remote로 참조만 읽으며 어떤 로컬 파일·ref·객체도 쓰지 않는다. origin이 없으면 로컬 검사/생성만 허용한다.
- 기존 release가 없으면 template만 담은 root commit을 만든다. 있으면 최신 release를 부모로 보존한다. 로컬/원격 release가 서로 갈라졌으면 중단한다.
- template tree가 같으면 새 commit을 만들지 않는다. 로컬 ref 갱신은 기존 값 조건부 update-ref로 동시 변경을 거부한다.
- --push는 main 게시 확인 후 일반 fast-forward push만 사용한다. 원격 race로 실패하면 로컬 commit을 유지하고 재확인 후 재시도한다. 충돌은 사용자 판단 없이 해결하지 않는다.
- 다른 worktree에서 release를 사용 중이면 중단한다. 작업 중 main 전환이나 작업 파일 재작성은 하지 않는다.
- 루트 AGENTS.md와 dev/instructions/GIT.md에서 RELEASE.md를 연결한다. Change 검토 → 최종 확인 → archive/main 병합·태그·push → release 생성·push → Change 브랜치 정리 순서를 문서화한다.

## 검증 방법

- Plan 공격/방어 검토 후 근거별 주 에이전트 판정
- 필수 구조, 상대 Markdown 링크, 과거 경로, 빈 사용자 상태, Git 제외 규칙 확인
- `bash -n dev/scripts/update_release_branch.sh`
- 격리 저장소에서 최초 배포, 기존 이력 보존, 재실행, 변경 반영, 잘못된 브랜치·dirty 상태·원격 분기·release checkout 거부, push 검증
- release tree ID와 `source:template` tree ID 일치 및 manifest/content hashes 일치, dotfile 포함, dev 미포함, README 단일 위치 검증
- Git diff 검사와 Change 완료 준비 검토

## 진행 상태

- 상태: `review`
- 기준 commit: `9511de694104bd8cc31eaf9815d90828d7651a54`
- 브랜치: `change/dev-template-separation`
- 승인 근거: 사용자가 제안한 분리를 승인하고 문서 수정·README 정리·release 배포 방식 구현을 명시적으로 지시했다.

## 검증 결과

- 작업 전 Git: clean main, origin/main과 동일. 기존 release와 origin/release 동일.
- Plan 검토: `plan_attack`, `plan_defend` 독립 검토 완료. 수정 Plan 판정 `pass`.

| finding | 공격 | 방어 | 주 에이전트 판정 |
|---|---|---|---|
| 경로 대응 누락 | 기존 canonical 경로의 이동과 라우팅을 명시해야 함 | 수정 표로 해결; 빈 src를 dev로 옮기라는 제안은 부정확 | 일부 수용. 대응 표·역할·archive 보존 추가, src는 template에 유지 |
| 배포 결과의 정확성 | tracked files만이라는 문구로 내용·dotfile·개발 자료 배제를 검증할 수 없음 | tree ID와 manifest/hash 비교 추가로 해결 | 수용. 정확한 tree 일치와 README·개발 자료 배제 검사 추가 |
| 배포 모드·동시성 | 초기 배포·재실행·실패 후 상태가 불명확 | 모드별 쓰기 경계·부모·원격 분기·조건부 갱신으로 해결 | 수용. 순수 검사 모드와 조건부 ref 갱신·일반 push·복구 조건 명시 |
| 배포 절차 발견성 | 루트에서 배포 지침과 순서가 드러나지 않음 | 라우팅 및 최종 확인 이후 순서 추가로 해결 | 수용. 루트 AGENTS/GIT에서 RELEASE 연결, Change commit/push와 최종 확인 경계를 문서화 |

### 구현 및 검사

- 개발 라우팅·목표·상태·지침은 루트 및 dev에, 사용자용 빈 틀은 template에 분리했다. 과거 archive 본문은 byte 단위로 보존했다.
- 루트 README를 제거했고 README는 template에만 존재한다. 배포 후 사용자 main 생성과 자기 origin 설정을 안내한다.
- 배포 도구는 template Git tree를 직접 commit하므로 숨김 파일·파일 모드·내용을 동일하게 유지한다. 기존 release를 부모로 두며 ref를 조건부 갱신한다.
- `bash -n dev/scripts/update_release_branch.sh dev/tests/test_release.sh`: 통과.
- `bash dev/tests/test_release.sh`: 구조, 링크, 초기 상태, 검사 모드 무변경, tree/manifest 일치, 최초 배포, 과거 이력, 재실행, dirty/브랜치/worktree/누락 파일 거부, 미게시 main 거부, 원격 게시, push 실패 재시도, 원격 race/분기, 로컬 ref 동시 변경 거부 통과.
- 별도 구조 검사: 이전 archive 본문과 현재 dev/archive 파일의 byte 일치, ignored Flow 및 상대 링크 통과.
- 실제 release는 변경하지 않았다. main 병합과 release 배포는 최종 확인 후 수행한다.

### Change 완료 준비 검토

- 검토자: `change_attack`, `change_defend` (읽기 전용 독립 검토).
- 최초 공격 결과: `revision_required`. 수정 후 방어 검토와 재검사 결과를 주 에이전트가 직접 대조해 최종 `pass` 판정했다.

| 위치 | 공격 주장·근거 | 방어 | 주 에이전트 판정·처리 |
|---|---|---|---|
| `dev/scripts/update_release_branch.sh` product 경로 검사 | `template/dev/private.txt`를 넣으면 release/dev로 배포되는 재현 확인 | 원래 결함 수용, 예약 경로와 추가 README 차단 및 mutation 검사로 해결 | 수용. dev/nested template/추가 README를 거부하며 기존 release ref가 유지됨을 검사 |
| 배포 도구의 required-file 검사 | 기존 존재 검사만으로 README 디렉터리나 symlink를 허용 | 원래 결함 수용, regular blob 모드와 회귀 검사로 해결 | 수용. 필수 경로는 blob+100644/100755만 허용하고 디렉터리·symlink 거부 확인 |
| `template/AGENTS.md`, `template/README.md`, 루트 경계 문구 | 배포 문서의 개발 checkout·내부 경로 설명이 역할 혼동을 유발 | 일부 수용. 내부 라우팅은 제거하되 제품 목적 설명까지 금지할 필요는 없음 | 일부 수용. 제품 문서는 사용자 프로젝트만 안내하고 루트 금지는 개발 기록·참고 자료로 명확히 함 |

- 최종 검사: Bash 문법, 전체 배포 회귀·구조 검사, staged diff 공백 검사, 단일 README와 tracked Flow 없음, 이전 archive byte 보존 모두 통과.
- 미해결 검토 finding 없음. main 병합·태그·release 게시를 위한 사용자 최종 완료 확인은 아직 받지 않았다.

## 최종 결과

- 구현과 독립 검토 완료. 검증된 Change 브랜치를 커밋·push한 뒤 최종 완료 확인을 받는다.
- 최종 완료 확인 전 main 병합과 실제 release 배포는 수행하지 않는다.
