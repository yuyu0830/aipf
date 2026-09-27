# AIPF

AIPF는 설치 없이 사용하는 Markdown 중심 AI 프로젝트 틀이다. 별도 Python 패키지나 AIPF CLI가 필요하지 않다.

## 시작

1. 저장소를 clone한다.
2. `project/PROJECT_SPEC.md`를 작성한다.
3. 에이전트에게 `현황 파악` 또는 Change 계획 작성을 요청한다.
4. 계획을 검토한 뒤 구현 시작을 명시한다.

첫 Change에서 프로젝트 기술에 맞는 단일 실행 진입점을 만든다. 기본 틀은 언어나 빌드 도구를 미리 선택하지 않는다.

Obsidian은 Markdown과 Mermaid 프로젝트 흐름을 보기 위한 기본 도구지만 설치는 선택 사항이다.

## 주요 위치

| 경로 | 용도 |
|---|---|
| `project/` | 프로젝트 목표, 현재 상태, 로컬 흐름, 이전 명세 |
| `change/` | 현재 진행 중인 변경 |
| `archive/` | 완료된 Change |
| `instructions/` | 에이전트 동작 규칙 |
| `inputs/` | 사용자가 제공한 최신 참고 자료와 이전본 |
| `knowledge/` | 재사용할 검증 정보와 출처 |
| `src/` | 버전별 구현과 실행 결과 |

## 중요 제한

- 이 버전은 새 프로젝트용 틀이다. 이전 Python CLI 프로젝트를 자동 변환하지 않는다.
- 자동 동작은 상주 프로그램이 아니라 현재 에이전트가 Markdown 지침에 따라 수행한다.
- 일반 Markdown과 Git이 기준이다. Obsidian은 화면만 보완한다.

## Telegram 완료 알림

자동 알림을 사용하려면 환경 변수 `AIPF_TELEGRAM_BOT_TOKEN`과 `AIPF_TELEGRAM_CHAT_ID`를 설정한다. 비밀값은 프로젝트 파일에 저장하지 않는다. 환경 변수가 없으면 알림만 건너뛰며 Change 완료는 유지한다.
