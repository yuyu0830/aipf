# AIPF

AIPF는 Markdown 문서와 Git으로 AI 프로젝트를 이어가는 틀이다. 별도 Python 패키지나 AIPF CLI를 설치하지 않는다.

## 새 프로젝트 시작

배포용 `release` 브랜치를 새 프로젝트 이름으로 clone한다.

```bash
git clone --branch release --single-branch git@github.com:yuyu0830/aipf.git my-project
cd my-project
git switch -c main
git remote remove origin
```

기존 origin은 AIPF 배포 저장소를 가리키므로 제거한다. 프로젝트를 저장할 자기 Git 저장소를 만든 뒤 그 주소로 origin을 설정한다.

```bash
git remote add origin <내-프로젝트-저장소-주소>
```

1. `project/PROJECT_SPEC.md`에 만들 프로젝트의 목표와 범위를 작성한다.
2. 에이전트에게 `현황 파악` 또는 Change 계획 작성을 요청한다.
3. 계획을 검토한 뒤 구현 시작을 명시한다.

첫 Change에서 프로젝트 기술에 맞는 단일 실행 진입점을 만든다. 기본 틀은 언어나 빌드 도구를 미리 선택하지 않는다. Git은 프로젝트 이력 관리에 필요하며, Obsidian은 Markdown과 Mermaid를 보는 선택 도구다.

## 파일 위치

| 경로 | 용도 |
|---|---|
| `AGENTS.md`, `MEMORY_MAP.md` | 에이전트 진입점과 파일 관리 기준 |
| `project/` | 내 프로젝트 목표, 현재 상태, 로컬 흐름, 이전 명세 |
| `change/` | 현재 진행 중인 변경 |
| `archive/` | 완료된 Change |
| `instructions/` | 에이전트 동작 규칙 |
| `inputs/` | 사용자가 제공한 참고 자료와 이전본 |
| `knowledge/` | 재사용할 검증 정보와 출처 |
| `src/` | 버전별 구현과 실행 결과 |

## 내 프로젝트 자료

`project/PROJECT_SPEC.md`, `inputs/`, `src/`에는 사용자가 만들 프로젝트의 목표·자료·코드를 넣는다. 이 초기 틀에는 AIPF 자체 개발 기록이 포함되지 않는다.

AIPF 배포 업데이트를 진행 중인 프로젝트에 그대로 덮어쓰지 않는다. 이전 Python CLI 프로젝트의 자동 변환은 지원하지 않는다.

## 작업 방식

에이전트가 현재 문서와 Git을 읽고 Change를 계획한다. 계획 승인과 구현 시작을 구분하며, 검증한 변경은 Git에 기록한다. 최종 완료는 사용자 확인 후 처리한다. 상주 프로그램이나 별도 AIPF 자동화 서비스는 없다.

`project/PROJECT_FLOW.md`는 Git에서 생성하는 로컬 보기이며 커밋하지 않는다.

## Telegram 완료 알림

자동 알림을 사용하려면 환경 변수 `AIPF_TELEGRAM_BOT_TOKEN`과 `AIPF_TELEGRAM_CHAT_ID`를 설정한다. 비밀값은 프로젝트 파일에 저장하지 않는다. 환경 변수가 없으면 알림만 건너뛰며 Change 완료는 유지한다.
