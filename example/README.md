# AI Project Framework

AIPF는 사용자와 AI가 합의한 프로젝트 계획을 파일로 저장하고, Plan 에이전트가 Task 결과를 검증하며, 필요한 경우에만 사용자 검토를 거쳐 진행하는 최소 프레임워크다.

버전: `0.2.1`

## 핵심 원칙

- 대화 내용이 사라져도 파일만 읽으면 프로젝트를 이어갈 수 있다.
- AI가 목표를 자동으로 작업으로 분해하지 않는다. 사용자와 AI가 대화로 Plan과 Task를 합의한다.
- 하나의 Task 에이전트는 하나의 Task를 수행하며, 독립적인 Task는 Plan 에이전트 판단으로 병렬 수행할 수 있다.
- 초기 설계 세션은 프로젝트 명세와 전체 Roadmap만 담당한다.
- 이후 세션은 Plan 하나를 제안부터 완료까지 담당하고, 다음 Plan은 새 세션에서 시작한다.
- Plan 승인 전에는 선택한 단계와 수행 방식을 보고한다. Task 결과는 먼저 Plan 에이전트가 검토하고, 예외가 있을 때만 실제 결과와 검증 근거를 사용자에게 검토 요청한다.
- 모든 Task 결과가 수용된 뒤 Plan 완료는 사용자가 최종 확인한다.
- 프로젝트 상태와 생성물은 사람이 직접 읽을 수 있는 파일로 관리한다.
- `PROJECT_FLOW.md`는 Plan 실행 흐름을 빠르게 파악하기 위한 읽기 전용 투영이다. Task와 Evidence는 표시하지 않는다.

## 진행 흐름

```text
초기 설계 세션에서 PROJECT_SPEC과 Roadmap 합의
                ↓
새 Plan 세션에서 이전 Plan 결과와 다음 Roadmap 단계 확인
                ↓
사용자와 AI가 해당 Plan의 목표·범위·Task 합의
                ↓
          Plan과 Task 저장
                ↓
            사용자 Plan 승인
                ↓
      독립 Task 병렬 또는 순차 시작
                ↓
       Task 에이전트가 생성물 제작·검증·결과 반환
                ↓
          Plan 에이전트 결과 검토
                ↓
   일반 결과 수용 / 예외만 사용자 검토
                ↓
      Plan 완료 사용자 최종 확인
```

AIPF는 AI 모델을 직접 선택하거나 호출하지 않는다. Codex, Claude Code 또는 다른 AI가 프로젝트 파일을 읽고 작업하는 실행 주체가 된다. 이 프로젝트의 Task 서브 에이전트 호출은 `gpt-5.6-luna`와 `xhigh`를 명시하며, CLI는 상태와 사용자 검토 지점을 관리한다.

## 프로젝트 구조

`aipf init`은 다음 구조를 만든다.

```text
project-root/
├── AGENTS.md
├── SKILLS.md
├── PROJECT.md
├── PROJECT_FLOW.md
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
    ├── evidence/E_000.yaml
    ├── audits/A_000.yaml
    ├── runtime.yaml
    └── config.yaml
```

각 파일과 디렉터리의 역할:

- `PROJECT.md`: 사용자가 읽는 한국어 현재 상태와 다음 행동
- `PROJECT_FLOW.md`: Plan, checkpoint, 중요한 Audit, runtime 위치를 보여 주는 CLI 생성 읽기 전용 흐름 투영
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
- `.aipf/`: Plan, Task, Evidence, Audit와 현재 실행 상태

`PROJECT_FLOW.md`는 관리 객체의 원본이 아니다. Plan, checkpoint, material Audit, runtime만 요약하며 Task와 Evidence 상세는 의도적으로 제외한다. AIPF CLI가 마커 사이의 생성 영역을 갱신하고 마커 밖의 안내와 범례는 보존한다. 사용자와 AI는 생성 영역을 직접 수정하지 않는다.

## 파일 생성 위치 규약

파일을 만들거나 수정하기 전에는 `MEMORY_MAP.md`와 활성 Task의 `outputs`를 먼저 확인한다. Task 실행 전에 예상 산출물의 경로를 선언하며, 적절한 위치가 명확하지 않으면 새 경로나 디렉터리를 만들기 전에 사용자에게 확인한다.

- 사용자가 제공한 원본은 `inputs/`에 둔다. AI는 기본적으로 읽기만 한다.
- 외부에서 가져온 원본은 `ref/`에 두며, 기존 원본을 덮어쓰지 않는다.
- AI가 생성하는 구현물과 프로젝트 산출물은 `src/`에 둔다.
- Plan·Task·Evidence·Audit·실행 상태와 설정은 `.aipf/`의 전용 위치에 둔다.
- `PROJECT_FLOW.md`는 프로젝트 루트에 두며 CLI를 통해서만 갱신한다. 이 파일은 읽기 전용 투영이고 관리 객체가 원본이다.
- 임시 파일은 작업 완료 후 삭제하고, 루트에 임의의 파일이나 디렉터리를 남기지 않는다. 루트에는 canonical layout에 정의된 관리 문서와 디렉터리만 둔다.

파일 배치를 추가·삭제·이동할 때는 같은 작업에서 `AGENTS.md`, `MEMORY_MAP.md`, `README.md`, `SKILLS.md`, `PROJECT_FLOW.md` 생성 규칙, `inputs/PROJECT_SPEC.md`, 영향을 받는 Plan·Task·Evidence·Audit 경로, 관련 코드와 테스트를 함께 갱신한다. 변경된 배치와 안내가 일치하는지 검증해야 변경이 완료된다.

`inputs/`는 사용자 전용 수정 영역이다. AI는 기본적으로 읽기만 한다. AI는 사용자가 명시적으로 요청할 때만 `inputs/PROJECT_SPEC.md`를 수정할 수 있다. 프로젝트 명세서는 하나만 둔다. `ref/`의 외부 원본은 덮어쓰지 않고 새 버전을 별도 파일로 저장한다. AI가 만든 결과는 `src/`에 둔다.

## Project flow projection

`PROJECT_FLOW.md`는 다음 원본을 사람이 빠르게 읽을 수 있도록 투영한다.

- Plan과 Plan 사이의 흐름
- Plan에 연결된 checkpoint
- 장기 보존이 필요한 material Audit
- 현재 `runtime.yaml` 위치와 상태

Task와 Evidence는 흐름 문서의 크기를 제한하기 위해 표시하지 않는다. `.aipf/` 관리 객체가 원본이며, `PROJECT_FLOW.md`를 수정해 상태를 바꾸지 않는다. CLI는 파일의 생성 마커 안쪽만 갱신하고 마커 바깥의 사용자 안내·범례는 보존한다. 상태를 갱신할 때는 직접 편집하지 말고 AIPF 명령을 사용한다.

## 관리 객체

### Plan

`.aipf/plans/P_000.yaml`에 프로젝트 목표, 범위, 완료 조건, Task 순서와 승인 상태를 저장한다.

Plan의 `checkpoints`는 실행 종료 시 생성되는 Git checkpoint의 중앙 색인이다. 한 실행에 여러 Task가 포함될 수 있고 하나의 Task가 여러 실행에 걸칠 수 있다. 각 항목은 실제 commit hash 대신 commit 메시지와 공유하는 안정적인 ID를 사용한다.

```yaml
checkpoints:
  - id: P_000-C_001
    task_ids:
      - T_000
      - T_001
```

checkpoint ID는 Plan에 hash 대신 저장하고 Git commit 메시지에도 동일하게 기록한다. 선택한 Task의 선언된 outputs와 관련 관리 객체는 자동 포함한다. 그 밖의 실행 파일은 `--path`로 명시하며, 소유가 확인되지 않은 변경이나 기존 staged 변경이 있으면 생성을 중단한다.

### Task

`.aipf/tasks/T_000.yaml`에 한 번에 실행할 작업 하나를 저장한다. 주요 항목은 목표, 참조 파일, 출력 파일, 제약, 완료 조건, 검증 방법, 결과와 상태다.

Task는 Plan의 `task_ids`와 의존성을 기준으로 실행된다. 활성 Plan에 속하지 않는 Task는 실행하지 않는다. 결과 의존성이 없고 선언된 output 경로가 겹치지 않는 Task는 병렬 실행할 수 있으며, 병렬 실행 중인 Task ID는 durable Plan 객체가 아니라 `.aipf/runtime.yaml`의 `active_task_ids`에 저장한다.

Plan 에이전트는 작은 Task를 직접 수행하거나 Task 에이전트를 호출할 수 있다. Task 에이전트 생성 권한은 Plan 에이전트에게만 있으며 Task 에이전트가 다른 Task 에이전트를 생성하는 것은 금지한다. 모든 호출은 `gpt-5.6-luna`, reasoning `xhigh`를 명시한다. Plan 에이전트는 병렬 결과를 통합하고 검증할 책임이 있다.

Task는 최신 `remaining`, `decisions`와 모든 제출의 `evidence_ids`를 보존한다. Task 에이전트는 선언된 산출물만 변경하고 `summary`, `changes`, `outputs`, `verification`, `remaining`, `decisions`를 구조화해 Plan 에이전트에게 반환한다. Task 에이전트는 Task·Evidence·Audit·Plan·runtime을 직접 수정하지 않는다. Plan 에이전트는 모든 결과를 먼저 검증하고 관리 객체를 순차 기록한다. 승인된 범위·완료 조건·검증을 충족한 일반 결과는 Plan 에이전트가 수용하며 사용자 검토나 Audit을 만들지 않는다. 승인 내용과 다르거나 검증 실패·미완료·결정 필요·산출물 누락·범위 변경·중요 위험 또는 외부 영향·검증 불확실성이 있으면 사용자 검토를 요청한다. 기록 전에 세션이 중단되면 다음 Plan 세션은 산출물과 Git 변경을 검사하고 검증을 다시 실행한 뒤 확인된 사실만 복구한다.

### Evidence

`.aipf/evidence/E_000.yaml`에 Task 제출 시점의 실제 요약, 변경, 산출물, 검증 결과, 미완료 사항과 사용자 결정 필요 사항을 저장한다. 제출할 때마다 새 Evidence를 만들며 이전 Evidence는 수정하지 않는다. `revise`나 `retry` 후 재제출하면 같은 Task가 여러 Evidence ID를 순서대로 참조한다.

### Audit

`.aipf/audits/A_000.yaml`에는 다음 작업이 알아야 하는 중요한 프로젝트 판단만 저장한다. 일반적인 Task 시작·승인·수정·재시도와 Evidence에 이미 기록된 결과에는 Audit을 만들지 않는다. Plan 에이전트가 목표·범위의 중요한 변경, 산출물 생략 승인, 위험 수용, 규약 예외, 복원, 프로젝트 중단·완료처럼 장기 보존이 필요한 결정을 선별한다.

별도 TODO, Handoff, Knowledge나 영구 Session 객체는 사용하지 않는다. Task가 `inputs/`, `ref/`, `src/`의 원본 파일을 직접 참조하고 후속 작업은 `remaining`으로 보존한다. 실행 중 필요한 최소 정보만 `.aipf/runtime.yaml`에 저장한다.

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

초기 상태는 `awaiting_plan`이다. 초기 설계 세션에서는 생성된 안내 파일을 확인하고 `inputs/PROJECT_SPEC.md`와 전체 Roadmap을 사용자와 합의한다. 이 세션에서는 개별 Plan을 실행하지 않는다.

## 2. 새 세션에서 Plan 합의

Plan 세션은 Plan 하나를 제안부터 완료까지 담당한다. 먼저 `PROJECT_SPEC.md`의 전체 목표·완료 기준·제약·Roadmap, `PROJECT.md`의 현재 상태, 가장 최근에 완료된 `P_XXX`의 목표·범위·Task 결과를 읽는다. 필요하면 관련 Audit도 확인한다. 첫 Plan 세션에는 이전 Plan이 없다.

AI는 이전 Plan의 실제 결과를 전제로 자연어 Roadmap에서 다음 단계를 선택해 Plan을 제안한다. 명세와 이전 결과가 충돌하면 임의로 해석하지 않고 사용자에게 알린다. Roadmap 항목 하나가 Plan 하나의 기본 후보다. 사용자가 승인하면 항목을 합치거나 나눌 수 있다. 명세서가 없거나 `진행 계획`에 단계 목록이 없으면 `plan apply`가 실행되지 않는다.

사용자는 AI와 다음 내용을 대화로 합의한다.

- 이번 Plan이 담당할 Roadmap 단계와 직전 Plan 결과와의 연결
- 프로젝트 목표와 포함·제외 범위
- 수행 방법과 예상 위험·주의점
- 완료 조건
- Task 목록과 실행 순서
- 각 Task가 읽을 `references`
- `src/`에 생성할 `outputs`
- 제약과 검증 방법

사용자는 YAML을 직접 작성할 필요가 없다. AI가 합의된 내용을 구조화된 payload로 만들고 저수준 writer 명령에 전달한다.

예시 payload:

```yaml
plan:
  roadmap_stage: "2. 핵심 기능 구현"
  goal: Create a project report
  approach:
    - Draft the report from the requirements and original source.
    - Verify the structure against the agreed acceptance criteria.
  risks:
    - The source material may not cover every requested conclusion.
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

`prior_plan_id`는 CLI가 현재 상태의 직전 Plan을 기준으로 자동 기록한다. `plan apply`는 저장한 Plan의 승인 전 보고를 출력한다. 이 보고에는 Roadmap 단계, 직전 Plan, 목표, 수행 방법, 포함·제외 범위, Task 순서와 각 Task의 참조·산출물·검증, 위험·주의점, 완료 조건 및 다음 승인 명령이 포함된다. 사용자는 이 보고를 검토한 뒤 승인하거나 수정을 요청한다.

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

Plan 에이전트는 활성 Plan에서 실행 가능한 미완료 Task를 선택한다. 독립적인 Task는 여러 Task 에이전트에 병렬 위임할 수 있으며, 각 Task 에이전트는 하나의 Task만 수행한다. 다음 내용을 각 Task에 대해 확인한다.

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
  --plan-review \
  --summary "보고서 초안 작성 완료" \
  --change "요구사항과 원본을 바탕으로 보고서 초안을 작성" \
  --evidence "문서 구조와 요구사항 대조 완료" \
  --output src/report.md
```

`task submit`은 `--summary`와 하나 이상의 `--change`를 요구한다. `--change`, `--output`, `--evidence`, `--remaining`, `--decision-needed`는 필요한 만큼 반복할 수 있다. 검증 항목이 선언된 Task는 `--evidence` 없이 제출할 수 없다. 선언된 output 일부를 제출하지 않아도 저장은 가능하지만 경고가 표시된다. 누락을 받아들일지는 사용자가 결정한다.

제출할 때마다 새 Evidence 객체가 생성되고 Task의 `evidence_ids`에 연결된다. Task의 `remaining`과 `decisions`도 최신 제출 내용으로 갱신된다. 제출 직후 CLI는 이 Evidence를 바탕으로 Task 완료 보고를 출력한다. 보고에는 목표, 결과 요약, 실제 수행·변경, 제출 산출물, 검증 결과, 미완료 사항·알려진 문제, 사용자 결정 필요 사항, 선언했지만 제출하지 않은 산출물 및 다음 검토 행동이 포함된다. 결과에는 계획이 아니라 실제 수행한 사실만 기록한다. 검증하지 않은 항목을 성공으로 보고하면 안 되며, 계획과 실제가 다르면 `remaining` 또는 `decisions`에 명시한다.

제출 후 Plan 에이전트가 결과를 검토한다. 일반 결과가 승인된 범위·완료 조건·검증을 모두 충족하면 Plan 에이전트가 수용하고 다음 Task로 진행한다. 이 수용은 사용자 검토나 Audit을 자동으로 만들지 않는다.

```bash
aipf --directory /path/to/project task accept --target T_000
```

사용자 판단 조건이 있으면 Plan 검토 후 사용자 검토로 전환한다.

```bash
aipf --directory /path/to/project task accept --target T_000 --user-review
```

## 6. 예외적인 Task 결과 검토

Plan 에이전트는 다음 경우에만 사용자 검토를 요청한다.

- 승인된 Plan 또는 Task 범위와 실제 결과가 다름
- 완료 조건이나 검증을 충족하지 못함
- `remaining` 또는 `decisions`가 남음
- 선언된 산출물이 누락됨
- 범위가 변경되거나 중요한 위험·외부 영향이 발생함
- Plan 에이전트가 결과를 확신 있게 검증할 수 없음

예외 결과 승인:

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

예외 결과에 대한 사용자 선택은 상태와 Task의 `feedback`에 반영하며 자동으로 Audit을 만들지 않는다. 장기 보존할 중요한 판단이면 Plan 에이전트가 `--audit-summary`를 함께 제공한다.

```bash
aipf --directory /path/to/project review approve \
  --target T_000 \
  --audit-summary "필수 산출물 일부를 후속 Plan으로 이관하기로 승인"
```

`approve`이면 해당 예외 결과를 수용하고 다음 Task로 진행한다. 모든 Task 결과가 Plan 에이전트에 의해 수용되면 Plan 완료 보고를 사용자에게 제시하고 최종 확인을 받는다. 사용자가 확인한 뒤 Plan은 `completed`가 되고 프로젝트는 다음 Plan을 기다리는 `awaiting_plan`으로 돌아간다. 현재 세션은 다음 Plan을 만들지 않고 종료한다.

## 7. 실행 checkpoint와 복원

Plan 에이전트가 구분한 한 번의 실행이 끝나면 참여한 Task를 묶어 하나의 checkpoint를 생성한다. 하나의 실행에 여러 병렬 Task를 포함할 수 있고, 하나의 Task가 여러 실행에 포함될 수도 있다. 실행 중인 병렬 Task ID는 `.aipf/runtime.yaml`의 `active_task_ids`로 추적하고, 결과를 관리 객체에 반영한 뒤 제거한다.

```bash
aipf --directory /path/to/project checkpoint create \
  --plan P_000 \
  --task T_000 \
  --task T_001 \
  --path src/additional-output.md
```

Git 저장소에는 먼저 기준 commit이 있어야 한다. 선택 Task의 선언된 outputs, 관련 Plan·Task·Evidence·Audit, runtime, `PROJECT.md`, `PROJECT_FLOW.md`가 Plan의 checkpoint 색인과 같은 commit에 기록된다. `--path`는 선언된 outputs 밖에서 이번 실행이 소유한 경로에만 사용한다.

확인된 checkpoint 상태로 돌아갈 때는 깨끗한 working tree에서 복원 사유를 함께 지정한다.

```bash
aipf --directory /path/to/project checkpoint restore \
  --target P_000-C_001 \
  --reason "후속 실행의 검증 실패로 확인된 상태로 복원"
```

복원은 기존 commit을 삭제하지 않는다. 대상 checkpoint의 상태를 새 restore commit으로 재현하고, 기존 checkpoint 색인과 append-only Evidence·Audit을 보존하며 복원 대상과 사유를 Audit에 추가한다.

다음 Plan은 새 세션에서 같은 절차로 제안하고 수행한다. 모든 Roadmap 단계가 끝났다고 판단되면 사용자가 프로젝트 완료를 명시적으로 확정한다.

```bash
aipf --directory /path/to/project project complete
```

실행 또는 검토 중인 Plan이나 Task가 있으면 프로젝트 완료가 차단된다. 완료 결정은 Audit에 기록된다.

## 상태 확인과 검증

현재 상태 확인:

```bash
aipf --directory /path/to/project status
```

파일 구조와 관리 객체 검증:

```bash
aipf --directory /path/to/project validate
```

`status`는 `PROJECT.md`와 `PROJECT_FLOW.md`를 현재 상태로 다시 생성한다. 사용자가 수정한 Telegram 전송 조건과 flow 마커 밖의 내용은 보존한다.

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

## Telegram 알림과 사용자 검토

Telegram token, 허용 chat ID, 허용 user ID는 파일에 저장하지 않는다. 환경 변수만 사용한다.

Bash:

```bash
export AIPF_TELEGRAM_BOT_TOKEN="..."
export AIPF_TELEGRAM_CHAT_ID="..."
export AIPF_TELEGRAM_USER_ID="..."
```

C shell:

```csh
setenv AIPF_TELEGRAM_BOT_TOKEN "..."
setenv AIPF_TELEGRAM_CHAT_ID "..."
setenv AIPF_TELEGRAM_USER_ID "..."
```

`PROJECT.md`에서 알림 조건을 설정한다.

```text
## Telegram 알림 설정

- 전송 조건: plan_review_required, task_review_required, task_completed, plan_completed, blocked
```

지원 조건:

- `plan_review_required`: Plan 승인 요청을 보내고 답변을 기다림
- `task_review_required`: Plan 에이전트가 예외로 분류한 Task 결과의 검토 요청을 보내고 답변을 기다림
- `task_completed`
- `plan_completed`
- `blocked`
- `never`

이 한 줄이 프로젝트별 Telegram 동작 설정의 원본이다. 사용자는 직접 쉼표 구분 목록을 수정하거나 에이전트에게 “Task 검토 때만 보내줘”처럼 요청할 수 있다. 에이전트는 이를 `task_review_required`만 남기는 식으로 반영한다. `never`는 반드시 단독으로 사용한다. `status` 등으로 `PROJECT.md`를 다시 생성해도 이 줄은 보존된다.

검토가 필요한 Plan 또는 Task를 알릴 때는 설정된 개인 사용자 한 명에게만 `approve`, `revise`, `retry`, `cancel`, `defer` 버튼을 제공한다. `revise`를 선택하면 텍스트 피드백을 함께 받아 기존 검토 피드백으로 저장한다. `defer`는 현재 대기를 즉시 끝내지만 Plan·Task·프로젝트 상태를 바꾸지 않으며, 나중에 같은 명령으로 검토 대기를 다시 시작할 수 있다.

응답 대기는 다음 명령으로 한 번만 실행한다.

```bash
aipf --directory /path/to/project telegram wait
```

기본 전체 대기 시간은 600초(10분)다. `--timeout`으로 초 단위 시간을 지정할 수 있다. 응답이 없으면 timeout으로 종료하며 Plan·Task·프로젝트 상태를 변경하지 않는다. 네트워크 오류나 `Ctrl+C`도 상태를 변경하지 않는다. 필요하면 같은 명령을 다시 실행한다.

환경 변수가 없으면 일반 알림은 건너뛰고, 검토 대기는 오류로 종료한다. Telegram 실패는 Task 또는 프로젝트 상태를 변경하지 않는다. 현재 범위에는 webhook, 상시 실행 daemon, 다중 사용자, 자유 대화형 Telegram 인터페이스가 포함되지 않는다.

## 현재 범위

버전 `0.2.1`은 다음 기능을 의도적으로 포함하지 않는다.

- 목표의 자동 Task 분해
- AI 모델 자동 선택과 직접 API 호출
- 자동 심사와 AI 법정 검토
- 영구 Session과 Knowledge 객체
- Telegram webhook, 상시 실행 daemon, 다중 사용자, 자유 대화형 인터페이스

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
