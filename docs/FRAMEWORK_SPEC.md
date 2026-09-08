# 프레임워크 명세

## 1. 목적

사용자는 하나의 오케스트레이터와 상호작용한다. 오케스트레이터는 작업을 계획하고 서브 에이전트에 배정하며 결과를 검토한다. 서브 에이전트는 원격 또는 로컬 LLM일 수 있다. 모든 작업은 대화 기록 없이도 YAML handoff에서 재개할 수 있어야 한다.

## 2. 신뢰 경계와 쓰기 권한

| 주체 | 읽기 | 쓰기 |
|---|---|---|
| 사용자 | CLI 출력, `PROJECT.md`, 요청된 산출물 | CLI 답변과 승인, `PROJECT.md`의 Telegram 전송 조건 |
| 오케스트레이터 | 전체 프로젝트 상태와 모든 handoff | `PROJECT.md`, 오케스트레이터 handoff, 배정·검토 메타데이터 |
| 서브 에이전트 | 배정된 handoff와 허용된 작업 자료 | 자신의 handoff와 허용된 산출물 |
| 검토 에이전트 | 심사 대상과 허용된 증거 | 자신의 주장 handoff |
| 심사 에이전트 | 제출물과 양측 구조화 주장 | 판결 handoff |

`PROJECT.md`는 오케스트레이터가 재생성한다. 사용자는 `Telegram 알림 설정`의 전송 조건만 수정할 수 있으며 오케스트레이터는 이 값을 보존한다. 서브 에이전트는 `PROJECT.md`를 직접 수정하지 않는다.

## 3. 구성 요소

1. **CLI**: 사용자 질문, 승인, 상태 확인, 실행과 재개를 담당한다.
2. **오케스트레이터**: 계획 분해, 배정, 모델 선택, 스케줄링, 체크포인트, 상태 투영을 담당한다.
3. **handoff 저장소**: 계획, 작업, 결정, 감사, 지식을 에이전트별 YAML로 저장한다.
4. **스케줄러**: 의존성과 자원 충돌을 계산해 병렬 또는 직렬 실행한다.
5. **모델 라우터**: 품질, 비용, 보안, 컨텍스트, 도구 조건으로 모델을 선택한다.
6. **실행 어댑터**: OpenAI-compatible API, Ollama, mock 실행기를 공통 계약으로 감싼다.
7. **법정 검토기**: 위험 기반 다중 에이전트 검토와 재심사를 수행한다.
8. **정책 엔진**: 파일, 명령, 네트워크, 예산, 승인 정책을 적용한다.
9. **상태 투영기**: handoff에서 사용자용 `PROJECT.md`를 원자적으로 재생성한다.

## 4. 디렉터리 기준

```text
project-root/
├── PROJECT.md
├── .aipf/
│   ├── config.yaml
│   ├── runtime.yaml
│   ├── schemas/
│   ├── handoff/
│   │   └── <agent-id>/
│   │       ├── plan/P_0000.yaml
│   │       ├── task/T_0000.yaml
│   │       ├── decision/D_0000.yaml
│   │       ├── audit/A_0000.yaml
│   │       └── knowledge/K_0000.yaml
│   ├── court/<case-id>/
│   ├── locks/
│   ├── logs/
│   └── archive/
└── <project artifacts>
```

## 5. 작업 생명주기

상태는 `pending`, `ready`, `running`, `blocked`, `review`, `completed`, `failed`, `cancelled` 중 하나다.

허용 전환:

```text
pending -> ready -> running -> review -> completed
                    |          |
                    |          +-> running
                    +-> blocked -> ready
                    +-> failed
pending|ready|running|blocked|review -> cancelled
```

작업 생성 시 다음 항목이 필수다.

- 명확한 목표와 범위
- 완료 조건
- 필요한 제약 조건
- 입력과 예상 산출물
- 선행 작업 ID
- `read_set`, `write_set`, `resources`
- 위험도
- 시간, 토큰, 비용 상한
- 검증 방법

## 6. 스케줄링

선행 작업이 완료된 `pending` 작업은 `ready`가 된다. 두 작업은 다음 조건 중 하나면 동시에 실행하지 않는다.

- 한 작업의 `write_set`이 다른 작업의 `read_set` 또는 `write_set`과 겹친다.
- 배타적 `resources` 값이 겹친다.
- 정책 엔진이 직렬 실행을 요구한다.

경로 비교는 프로젝트 루트 기준 정규화 경로로 수행한다. 디렉터리는 하위 전체와 충돌한다. 불명확하거나 동적 범위는 안전하게 충돌로 판정한다.

## 7. 세션과 복구

- 각 세션은 고유 ID, 시작 시각, 모델, 예산, 부모 세션 ID를 갖는다.
- 컨텍스트 사용률이 70% 이상이면 현재 작업 handoff를 진행분까지 원자적으로 저장한다.
- 저장 검증 후 기존 세션을 종료하고 새 세션을 만든다.
- 새 세션은 활성 handoff와 필요한 산출물만 읽는다.
- 프로세스 중단 후 `resume`은 handoff와 runtime 상태를 대조한다.
- `running`인데 heartbeat가 만료된 작업은 중단 작업으로 표시하고 1회 재시도한다.
- 재시도 실패, 예산 초과, 복구 불가능한 불일치는 CLI 질문으로 전환한다.

## 8. 실패 정책

- 일반 실행 실패: 같은 배정으로 1회 재시도한다.
- heartbeat timeout: 세션을 종료하고 handoff 저장 여부를 검증한 뒤 1회 재시도한다.
- 재실패: 작업을 `blocked`로 바꾸고 사용자 질문을 생성한다.
- 법정 `rejected`: 개선 후 재심사하며 최대 3회 수행한다.
- 3회 이후: `user_decision_required`로 중단한다.

## 9. 모델 선택

후보 모델은 품질, 비용, 보안, 컨텍스트 용량, 도구 지원을 점수화한다. 비용 항목은 다른 일반 항목보다 높은 가중치를 갖는다. 보안 정책은 점수보다 우선한다. 민감 정보가 포함된 작업은 로컬 Ollama를 우선하며 외부 전송 금지 정책이 있으면 원격 모델을 후보에서 제외한다.

초기 권장 가중치:

```yaml
quality: 0.25
cost: 0.35
security: 0.20
context: 0.10
tools: 0.10
```

## 10. 사용자 체크포인트

- 개별 task 종료: 완료를 알린 뒤 사용자 승인 전까지 다음 task를 시작하지 않는다.
- plan 종료: `PROJECT.md` 갱신 후 사용자 확인을 기다린다.
- 위험한 외부 효과, 정책 예외, 법정 판단 불가: 즉시 중단하고 질문한다.
- 질문과 답변은 decision handoff와 audit에 기록한다.

Telegram 알림은 `PROJECT.md`의 전송 조건과 일치하면 별도 확인 없이 실행한다. 지원 조건은 `task_completed`, `plan_completed`, `blocked`, `never`다. Bot token과 chat ID가 없으면 실행하지 않는다. 실패는 프로젝트 상태에 영향을 주지 않는다.

## 11. 완료 정의

프레임워크의 첫 버전은 다음 조건을 만족해야 한다.

- 명시된 CLI 명령이 동작한다.
- YAML Schema 검증과 상태 전환 검증이 동작한다.
- 충돌 기반 직렬화 테스트가 통과한다.
- mock 에이전트로 중단·재개와 70% rollover를 재현한다.
- 법정 모델의 승인, 개선, 3회 제한을 재현한다.
- `PROJECT.md`가 handoff에서 재생성된다.
- 키 마스킹과 작업공간 경계 테스트가 통과한다.
