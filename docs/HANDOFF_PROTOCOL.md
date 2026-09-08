# Handoff 프로토콜

## 1. 저장 단위

handoff는 에이전트와 용도별 디렉터리에 독립 YAML 파일로 저장한다.

| 종류 | 접두사 | 의미 |
|---|---|---|
| plan | `P_` | 목표 분해와 체크포인트 |
| task | `T_` | 실행 가능한 작업 계약 |
| decision | `D_` | 선택, 질문, 답변, 판결 |
| audit | `A_` | 상태 변화와 외부 효과 증거 |
| knowledge | `K_` | 재사용 가능한 사실과 근거 |

ID는 종류별 4자리 증가 번호로 시작한다. 파일 내부에는 충돌 방지를 위한 전역 UUID도 둔다. 번호가 9999를 넘으면 자릿수를 확장한다.

## 2. 공통 필드

```yaml
schema_version: "1.0"
id: T_0000
uid: "uuid"
kind: task
agent_id: worker-01
project_id: "uuid"
created_at: "RFC3339 UTC"
updated_at: "RFC3339 UTC"
revision: 1
status: pending
parent_ids: []
tags: []
```

모든 쓰기는 임시 파일 생성, 스키마 검증, `fsync`, 원자적 rename 순서로 수행한다. 완료된 handoff는 잠근다. 잠금 이후 변경은 새 파일과 이를 연결하는 audit으로 표현한다.

## 3. Task 필수 구조

```yaml
goal: "단일 검증 가능한 목표"
scope:
  includes: []
  excludes: []
inputs: []
outputs: []
constraints: []
acceptance_criteria: []
verification:
  commands: []
  evidence: []
dependencies: []
read_set: []
write_set: []
resources: []
risk: low
budget:
  timeout_seconds: 900
  max_input_tokens: 50000
  max_output_tokens: 10000
  max_cost_usd: 2.00
attempt: 0
max_retries: 1
progress:
  summary: ""
  completed: []
  remaining: []
  next_action: ""
result:
  outcome: null
  artifacts: []
  evidence: []
blocker: null
```

## 4. Plan 필수 구조

Plan은 목표, 범위, task ID 목록, task 의존성, 완료 조건, 제약, 현재 체크포인트를 저장한다. Plan 완료 전 오케스트레이터가 전체 task의 완료 조건과 검증 증거를 확인한다.

## 5. Decision 필수 구조

Decision은 질문 또는 결정의 주체, 선택지, 선택값, 근거, 영향 범위, 결정 시각을 저장한다. 사용자 답변이 필요한 동안 상태는 `blocked`다.

## 6. Audit 필수 구조

Audit은 사건 종류, 행위자, 대상 ID, 이전 상태, 이후 상태, 실행 명령의 안전한 요약, 결과 코드, 증거 참조, 마스킹 여부를 저장한다. 비밀정보와 원문 프롬프트 전체를 저장하지 않는다.

## 7. Knowledge 필수 구조

Knowledge는 주장, 출처, 신뢰도, 적용 범위, 유효 기간, 마지막 검증 시각을 저장한다. 추측은 사실과 구분한다. 만료되거나 출처가 사라진 지식은 모델 입력에서 제외한다.

## 8. 소유권

- 서브 에이전트는 자신의 디렉터리에만 handoff를 생성·수정한다.
- 오케스트레이터는 배정용 handoff를 생성하고 상태를 집계한다.
- 에이전트 작업 종료 후 오케스트레이터가 제출본을 잠근다.
- 다른 에이전트는 원본을 수정하지 않고 새 handoff로 반론하거나 보완한다.

## 9. 70% rollover 계약

rollover 직전에 활성 task에는 다음 값이 반드시 최신이어야 한다.

- 완료된 세부 작업
- 남은 세부 작업
- 생성하거나 수정한 산출물
- 검증 결과
- 결정과 가정
- 차단 원인
- 정확히 하나의 다음 행동

새 세션은 원본 대화에 의존하면 안 된다.

## 10. Task 종료 계약

에이전트는 일반적으로 한 번에 task 하나만 수행한다. 오케스트레이터가 session ID와 일회용 capability token을 subprocess 환경에 넣는다.

성공 시 에이전트는 공용 스크립트를 실행한다.

```bash
.aipf/bin/complete-task \
  --task T_0007 \
  --session S_ab12cd34ef56 \
  --summary "완료 내용" \
  --evidence "검증 결과" \
  --artifact "산출물 경로"
```

스크립트는 task 소유권, session, token, handoff 필수값, 남은 작업, 검증 증거를 확인한다. 성공하면 실행 시도와 결과를 해당 task handoff에 기록하고 `running`을 `review`로 바꾼다. Token은 한 번 사용한 뒤 폐기한다.

실패나 차단 시 `.aipf/bin/report-task`를 실행한다. 요약과 원인 분석은 필수다. 검증 오류가 나면 상태를 바꾸지 않으므로 handoff를 고친 뒤 다시 호출할 수 있다.

오케스트레이터 검토 승인 후 상태는 `completed`가 된다. Telegram 훅은 이 시점에 완료 결과, 다음 task, 다음 수행 항목, 사용자 행동을 전달한다. 알림 실패는 task 상태에 영향을 주지 않는다.

각 task가 완료되면 프로젝트는 `awaiting_task_confirmation`에서 멈춘다. 사용자가 다음 명령을 실행해야 다음 task를 시작할 수 있다.

```bash
aipf approve continue --target T_0007
```
