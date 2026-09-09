# AI Project Framework

AIPF는 사용자와 AI가 합의한 프로젝트 계획을 파일로 저장하고, 작업을 하나씩 수행하며, 사용자 검토를 거쳐 다음 작업으로 진행하는 최소 프레임워크다.

버전: `0.2.0`

## 핵심 원칙

- 대화 내용이 사라져도 파일만 읽으면 프로젝트를 이어갈 수 있다.
- AI가 목표를 자동으로 작업으로 분해하지 않는다. 사용자와 AI가 대화로 Plan과 Task를 합의한다.
- 한 번에 활성 Task 하나만 수행한다.
- Task 결과의 최종 판단은 사용자가 한다.
- 프로젝트 상태와 생성물은 사람이 직접 읽을 수 있는 파일로 관리한다.

## 진행 흐름

```text
사용자와 AI가 목표·범위·Task 합의
                ↓
          Plan과 Task 저장
                ↓
            사용자 Plan 승인
                ↓
             Task 하나 시작
                ↓
       AI가 생성물 제작·검증·제출
                ↓
      사용자 approve/revise/retry/cancel
                ↓
           Audit 기록 후 계속
```

AIPF는 AI 모델을 직접 선택하거나 호출하지 않는다. Codex, Claude Code 또는 다른 AI가 프로젝트 파일을 읽고 작업하는 실행 주체가 된다. CLI는 상태와 사용자 검토 지점을 관리한다.

## 프로젝트 구조

`aipf init`은 다음 구조를 만든다.

```text
project-root/
├── AGENTS.md
├── SKILLS.md
├── PROJECT.md
├── MEMORY_MAP.md
├── inputs/
│   ├── PROJECT_SPEC.md
│   ├── docs/
│   ├── codes/
│   ├── data/
│   └── media/
├── ref/
├── src/
└── .aipf/
    ├── plans/P_000.yaml
    ├── tasks/T_000.yaml
    ├── audits/A_000.yaml
    ├── runtime.yaml
    └── config.yaml
```

각 파일과 디렉터리의 역할:

- `PROJECT.md`: 사용자가 읽는 한국어 현재 상태와 다음 행동
- `AGENTS.md`: AI가 항상 따라야 하는 행동 규칙
- `SKILLS.md`: 프로젝트에서 반복 사용하는 작업 절차
- `MEMORY_MAP.md`: 파일 위치, 목적, 사용자·AI 접근 권한
- `inputs/PROJECT_SPEC.md`: 프로젝트 전체 목표, 명세, 자연어 Roadmap을 담는 단일 기준 문서
- `inputs/docs/`: 사용자가 제공한 문서
- `inputs/codes/`: 사용자가 제공한 소스 코드
- `inputs/data/`: 사용자가 제공한 정형 데이터
- `inputs/media/`: 사용자가 제공한 이미지, 오디오, 비디오
- `ref/`: AI가 관리하는 외부 원본과 출처 metadata
- `src/`: AI가 만드는 프로젝트 구현물과 생성물
- `.aipf/`: Plan, Task, Audit와 현재 실행 상태

`inputs/`는 사용자 전용 수정 영역이다. AI는 기본적으로 읽기만 한다. AI는 사용자가 명시적으로 요청할 때만 `inputs/PROJECT_SPEC.md`를 수정할 수 있다. 프로젝트 명세서는 하나만 둔다. `ref/`의 외부 원본은 덮어쓰지 않고 새 버전을 별도 파일로 저장한다. AI가 만든 결과는 `src/`에 둔다.

## 관리 객체

### Plan

`.aipf/plans/P_000.yaml`에 프로젝트 목표, 범위, 완료 조건, Task 순서와 승인 상태를 저장한다.

### Task

`.aipf/tasks/T_000.yaml`에 한 번에 실행할 작업 하나를 저장한다. 주요 항목은 목표, 참조 파일, 출력 파일, 제약, 완료 조건, 검증 방법, 결과와 상태다.

Task는 Plan의 `task_ids` 순서대로 실행된다. 활성 Plan에 속하지 않는 Task는 실행하지 않는다.

### Audit

`.aipf/audits/A_000.yaml`에 사용자 검토 결과를 저장한다. 현재 선택지는 `approve`, `revise`, `retry`, `cancel`이다.

별도 Knowledge나 영구 Session 객체는 사용하지 않는다. Task가 `inputs/`, `ref/`, `src/`의 원본 파일을 직접 참조한다. 실행 중 필요한 최소 정보만 `.aipf/runtime.yaml`에 저장한다.

## 설치

Python 3.12 이상이 필요하다.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
```

설치 확인:

```bash
.venv/bin/aipf --help
```

## 1. 프로젝트 초기화

```bash
aipf --directory /path/to/project init --goal "프로젝트 목표"
```

초기 상태는 `awaiting_plan`이다. 생성된 `PROJECT.md`, `AGENTS.md`, `SKILLS.md`, `MEMORY_MAP.md`를 먼저 확인하고 `inputs/PROJECT_SPEC.md`를 작성한다.

## 2. 사용자와 Plan 합의

AI는 `inputs/PROJECT_SPEC.md`의 자연어 Roadmap에서 다음 단계를 선택해 Plan을 제안한다. Roadmap 항목 하나가 Plan 하나의 기본 후보다. 사용자가 승인하면 항목을 합치거나 나눌 수 있다. 명세서가 없거나 `진행 계획`에 단계 목록이 없으면 `plan apply`가 실행되지 않는다.

사용자는 AI와 다음 내용을 대화로 합의한다.

- 프로젝트 목표와 포함·제외 범위
- 완료 조건
- Task 목록과 실행 순서
- 각 Task가 읽을 `references`
- `src/`에 생성할 `outputs`
- 제약과 검증 방법

사용자는 YAML을 직접 작성할 필요가 없다. AI가 합의된 내용을 구조화된 payload로 만들고 저수준 writer 명령에 전달한다.

예시 payload:

```yaml
plan:
  goal: Create a project report
  scope:
    includes:
      - final report
    excludes:
      - presentation slides
  acceptance_criteria:
    - The user approves the final report

tasks:
  - goal: Write the report
    references:
      - inputs/docs/requirements.md
      - ref/source-paper.pdf
    outputs:
      - src/report.md
    constraints:
      - Do not modify source originals
    acceptance_criteria:
      - src/report.md exists
    verification:
      commands: []
      evidence:
        - src/report.md
```

AI가 내부적으로 실행하는 명령:

```bash
aipf --directory /path/to/project plan apply --file agreed-plan.yaml
```

표준 입력도 사용할 수 있다.

```bash
aipf --directory /path/to/project plan apply --file - < agreed-plan.yaml
```

저장 후 상태는 `awaiting_plan_confirmation`이 된다. 승인 전 `aipf run`은 Task를 시작하지 않는다.

## 3. Plan 검토

승인:

```bash
aipf --directory /path/to/project review approve --target P_000
```

수정 요청:

```bash
aipf --directory /path/to/project review revise \
  --target P_000 --feedback "Task 순서를 변경해줘"
```

AI가 사용자 피드백을 반영한 payload를 다시 저장하고 승인을 요청한다.

## 4. Task 시작

```bash
aipf --directory /path/to/project run
```

CLI는 활성 Plan에서 아직 완료되지 않은 첫 Task를 선택한다. 다음 내용을 출력한다.

- Task ID와 목표
- 참조할 파일
- 생성할 출력 파일
- 실행할 검증 명령
- 제출해야 할 evidence

참조 파일이 없으면 Task를 `blocked`로 변경한다. 이 경우 Telegram의 `blocked` 조건이 활성화되어 있으면 알림을 보낸다.

## 5. AI 작업과 결과 제출

AI는 `AGENTS.md`와 활성 Task를 읽고 작업한다. `inputs/`를 수정하지 않으며, 생성물은 Task에 선언된 `src/` 경로에 저장한다.

작업 후 검증 명령을 실행하고 결과를 제출한다.

```bash
aipf --directory /path/to/project task submit \
  --target T_000 \
  --summary "보고서 초안 작성 완료" \
  --evidence "문서 구조와 요구사항 대조 완료" \
  --output src/report.md
```

검증 항목이 선언된 Task는 `--evidence` 없이 제출할 수 없다. 선언된 output 일부를 제출하지 않아도 저장은 가능하지만 경고가 표시된다. 누락을 받아들일지는 사용자가 결정한다.

제출 후 상태는 `awaiting_task_confirmation`이 된다.

## 6. 사용자 Task 검토

결과 승인:

```bash
aipf --directory /path/to/project review approve --target T_000
```

수정 후 다시 수행:

```bash
aipf --directory /path/to/project review revise \
  --target T_000 --feedback "결론에 근거를 추가해줘"
```

동일 조건으로 재시도:

```bash
aipf --directory /path/to/project review retry --target T_000
```

Task와 프로젝트 취소:

```bash
aipf --directory /path/to/project review cancel --target T_000
```

사용자 선택은 Audit에 기록된다. `approve`이면 다음 Task로 진행한다. 마지막 Task를 승인하면 Plan과 프로젝트가 `completed`가 된다.

## 상태 확인과 검증

현재 상태 확인:

```bash
aipf --directory /path/to/project status
```

파일 구조와 관리 객체 검증:

```bash
aipf --directory /path/to/project validate
```

`status`는 `PROJECT.md`를 현재 상태로 다시 생성한다. 사용자가 수정한 Telegram 전송 조건은 보존한다.

## 외부 자료 관리

외부 원본은 `ref/`에 저장한다.

```text
ref/
├── source-paper.pdf
└── source-paper.pdf.source.yaml
```

권장 source metadata:

```yaml
source: https://example.com/source-paper.pdf
retrieved_at: 2026-09-08T00:00:00Z
title: Source Paper
license: unknown
sha256: "..."
used_by:
  - T_000
```

원본을 가공한 결과는 `ref/`가 아니라 `src/`에 저장한다.

## Telegram 알림

Telegram token과 chat ID는 파일에 저장하지 않는다. 환경 변수만 사용한다.

Bash:

```bash
export AIPF_TELEGRAM_BOT_TOKEN="..."
export AIPF_TELEGRAM_CHAT_ID="..."
```

C shell:

```csh
setenv AIPF_TELEGRAM_BOT_TOKEN "..."
setenv AIPF_TELEGRAM_CHAT_ID "..."
```

`PROJECT.md`에서 알림 조건을 설정한다.

```text
## Telegram 알림 설정

- 전송 조건: task_completed, plan_completed, blocked
```

지원 조건:

- `task_completed`
- `plan_completed`
- `blocked`
- `never`

환경 변수가 없으면 알림을 건너뛴다. Telegram 실패는 Task 또는 프로젝트 상태를 변경하지 않는다.

## 현재 범위

버전 `0.2.0`은 다음 기능을 의도적으로 포함하지 않는다.

- 목표의 자동 Task 분해
- AI 모델 자동 선택과 직접 API 호출
- 다중 agent 병렬 실행
- 자동 심사와 AI 법정 검토
- 영구 Session과 Knowledge 객체

실제 프로젝트를 진행하며 필요성이 확인된 기능만 이후 버전에 추가한다.

## 개발 및 테스트

```bash
.venv/bin/python -m unittest discover -s tests -v
```

현재 핵심 테스트는 다음을 검증한다.

- 프로젝트 구조 생성과 상태 검증
- Plan 승인, Task 실행, 결과 제출, 사용자 승인 lifecycle
- 활성 Plan의 Task 범위와 선언 순서
- `approve`, `revise`, `retry`, `cancel`
- 검증 evidence 요구와 output 누락 경고
- Telegram 성공, 미설정, 실패 격리
