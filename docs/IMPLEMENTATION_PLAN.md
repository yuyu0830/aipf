# P_0001 AI 프로젝트 프레임워크 구현 계획

## 현재 상태

- `P_0001`: 구현 체크포인트 승인 완료 (2026-09-08)
- `T_0001`: 완료
- `T_0002`: 완료
- `T_0003`: 완료
- `T_0004`: 완료
- `T_0005`: 완료
- `T_0006`: 완료
- `T_0007`: 완료
- 다음 행동: 필수 기능 완성을 위한 후속 개발 plan 수립

## 1. 목표

현재의 명세와 최소 CLI 골격을 실제로 작업을 실행하고, 중단 후 복구하며, 위험 기반 검토를 수행할 수 있는 첫 번째 완성 버전으로 확장한다.

완료 시 사용자는 `aipf init`으로 프로젝트를 만들고, plan을 승인한 뒤 `aipf run`과 `aipf resume`으로 여러 에이전트 작업을 안전하게 수행할 수 있어야 한다.

## 2. 범위

### 포함

- YAML handoff schema와 상태 전환의 완전한 검증
- provider 독립 실행기와 subprocess 생명주기 관리
- 충돌 기반 병렬 스케줄링과 task별 자원 잠금
- heartbeat, 재시도, 예산, 70% context rollover
- 위험 기반 법정 검토와 최대 3회 재심사
- `PROJECT.md` 상태 투영과 사용자 체크포인트
- Telegram 완료 알림 훅
- 보안 경계, 감사 기록, 통합 및 장애 복구 테스트

### 제외

- 웹 UI와 모바일 UI
- 분산 실행 클러스터
- 자체 모델 학습과 fine-tuning
- Telegram을 통한 프로젝트 제어
- Windows와 macOS 정식 지원

## 3. 완료 조건

다음 조건을 모두 충족하면 P_0001을 완료한다.

1. `docs/FRAMEWORK_SPEC.md`에 명시된 CLI 명령이 실제 상태를 변경한다.
2. mock provider로 task 병렬 실행, 충돌 직렬화, 실패 재시도, 중단 후 재개를 재현한다.
3. context 사용률 70%에서 handoff를 저장하고 새 세션을 시작한다.
4. `high`와 `critical` task에 2명의 검토자, 2명의 변호자, 1명의 심사자를 실행한다.
5. Telegram 완료 알림은 설정된 경우에만 최소 정보를 보내며 실패가 task 결과를 변경하지 않는다.
6. workspace 탈출, 비밀정보 기록, 잘못된 capability token을 차단한다.
7. 전체 자동 테스트와 CLI end-to-end 테스트가 Python 3.12에서 통과한다.

## 4. 구현 순서

### T_0001 기준선 고정과 schema 강화

상태: 완료

현재 코드와 문서의 차이를 제거하고 이후 작업의 검증 기준을 고정한다.

- 모든 handoff 종류에 JSON Schema 추가
- schema version, 상태별 필수값, ID와 UUID 형식 검증
- config와 runtime schema 검증
- 현재 테스트 개수와 실행 방법을 `README.md`에 명시
- `PROJECT.md`가 실제 handoff에서만 생성되도록 fixture 구성

완료 증거:

- 잘못된 plan, task, decision, audit, knowledge fixture가 모두 거부됨
- `.venv/bin/python -m unittest discover -s tests -v` 통과

### T_0002 실행 계약과 모델 라우터

상태: 완료

provider 선택부터 에이전트 요청 생성까지 하나의 실행 계약으로 묶는다.

- provider registry와 공통 오류 모델 추가
- 품질, 비용, 보안, context, 도구 점수 기반 모델 선택
- 민감 작업의 원격 provider 제외 정책 적용
- task handoff에서 `AgentRequest` 생성
- 모델, prompt version, 예산을 session과 audit에 기록

완료 증거:

- 동일 입력에 결정적인 provider 선택 테스트 통과
- 외부 전송 금지 task가 Ollama 또는 허용된 로컬 provider만 선택

### T_0003 실행기와 스케줄러 연결

상태: 완료

`aipf run`이 batch 출력에서 끝나지 않고 실제 task를 실행하도록 만든다.

- task별 session과 일회용 capability token 발급
- shell 없이 인자 배열로 worker subprocess 실행
- 최대 동시 실행 수와 자원 잠금 적용
- stdout, stderr의 마스킹된 요약과 종료 코드를 audit에 기록
- 완료 제출을 `review`, 실패 제출을 `blocked` 또는 `failed`로 전환

완료 증거:

- 독립 task는 병렬 실행
- 충돌 task는 직렬 실행
- 잘못된 token과 다른 task의 session은 제출 거부

### T_0004 heartbeat, 예산, 재시도, resume

상태: 완료

프로세스 중단과 context 한계를 handoff만으로 복구한다.

- heartbeat writer와 timeout 감시기 추가
- 시간, 입력 토큰, 출력 토큰, 비용 한도 적용
- 일반 실패와 heartbeat timeout 각각 1회 재시도
- 70% 도달 시 원자적 checkpoint와 새 session 생성
- `resume`에서 runtime, session, handoff 불일치 복구

완료 증거:

- 강제 종료된 mock worker가 1회 복구됨
- 두 번째 실패는 사용자 질문과 `blocked` 상태 생성
- 새 session이 원본 대화 없이 남은 작업을 완료

### T_0005 검토와 사용자 체크포인트

상태: 완료

위험도에 따라 단일 검토 또는 법정 검토를 실행한다.

- 위험도 산정과 상향 전용 정책 추가
- case manifest와 증거 snapshot 고정
- 2명의 검토자, 2명의 변호자, 1명의 심사자 독립 실행
- 판결과 재심사 task 생성
- task 완료 후 `awaiting_task_confirmation` 중단
- plan 완료 후 사용자 확인 중단

완료 증거:

- 승인, 수정 요구, 거절, 사용자 결정 필요 경로 재현
- 3회 제한 이후 자동 진행하지 않음

### T_0006 상태 투영과 Telegram 알림

상태: 완료

사용자 인터페이스와 선택적 완료 알림을 연결한다.

- handoff와 runtime에서 `PROJECT.md` 원자적 재생성
- 최근 결정, 검토 결과, 산출물, 다음 체크포인트 투영
- `AIPF_TELEGRAM_BOT_TOKEN`, `AIPF_TELEGRAM_CHAT_ID` 환경 변수 사용
- `completed` 전환 후 프로젝트명, task ID, 요약, 검토 결과, 다음 체크포인트 전송
- 미설정 시 무시하고 전송 실패는 상태를 변경하지 않음

완료 증거:

- Telegram API mock의 성공, 미설정, timeout, HTTP 오류 테스트 통과
- 실제 Bot API 송수신 smoke test 통과

### T_0007 보안 강화와 end-to-end 검증

상태: 완료

첫 버전 완료 조건을 전체 흐름으로 검증한다.

- symlink와 `..` workspace 탈출 테스트
- 명령 허용 목록, 네트워크, 삭제, 외부 전송 승인 테스트
- 로그, audit, handoff의 token 및 API key 마스킹 검사
- init부터 plan 승인, 실행, 검토, 사용자 승인까지 end-to-end fixture 추가
- 설치, 운영, 장애 복구 절차 문서화

완료 증거:

- 전체 단위 및 통합 테스트 통과
- mock 프로젝트 end-to-end 실행 성공
- `aipf validate`가 손상된 상태와 정상 상태를 정확히 구분

## 5. 의존성

```text
T_0001
  ├─ T_0002
  │    └─ T_0003
  │         └─ T_0004
  └─ T_0005 ─┐
             ├─ T_0006
T_0004 ──────┘
       └─────── T_0007
T_0005 ──────── T_0007
T_0006 ──────── T_0007
```

`T_0002`와 `T_0005`의 정책 및 자료 구조 작업은 `T_0001` 이후 병렬로 진행할 수 있다. 같은 파일을 수정하는 세부 작업은 `write_set`으로 직렬화한다.

## 6. 체크포인트

| 체크포인트 | 포함 task | 사용자 확인 항목 |
|---|---|---|
| CP1 기반 계약 | T_0001, T_0002 | schema와 실행 계약 승인 |
| CP2 실제 실행 | T_0003, T_0004 | subprocess 방식과 복구 결과 승인 |
| CP3 검토와 알림 | T_0005, T_0006 | 법정 검토와 Telegram 동작 승인 |
| CP4 첫 버전 | T_0007 | end-to-end 결과와 릴리스 승인 |

## 7. 예상 기간

한 명이 순차 구현하면 약 8~12 작업일이다. 독립 작업을 병렬화하면 약 5~8 작업일이다. 외부 provider별 실제 통합 검증 시간은 별도다.

## 8. 첫 실행 항목

P_0001 승인 후 `T_0001 기준선 고정과 schema 강화`를 시작한다. 첫 체크포인트는 JSON Schema, fixture, 전체 테스트 명령이 안정적으로 동작하는 상태다.
