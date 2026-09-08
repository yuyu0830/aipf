# 새 세션 Handoff

작성 시각: 2026-09-08 (Asia/Seoul)

## 1. 프로젝트 상태

- 프로젝트명과 CLI명: `aipf`
- 개발 버전: `0.0.0.dev0`
- Git branch: `main`
- Git remote: `git@github.com:yuyu0830/aipf.git`
- 현재 구현 체크포인트: `P_0001` 완료
- 검증 결과: 단위·통합 테스트 54개 통과
- 정식 Git tag와 GitHub Release: 아직 생성하지 않음
- `.venv`, cache, build 산출물: 템플릿에서 제거됨

## 2. 확정된 제품 방향

첫 프로젝트 세션에서 오케스트레이터가 사용자와 충분히 대화해 목표, 범위, 완료 조건, 제약, plan, task를 직접 합의한다.

목표를 자동으로 task로 분해하는 기능은 만들지 않는다. 자동 분해보다 모호함 제거와 사용자 의도 반영을 우선한다.

합의가 끝난 뒤 오케스트레이터가 구조화된 handoff에 plan과 task를 저장하고 사용자 승인을 받아 실행한다. 사용자가 YAML을 직접 편집하게 하지 않는다.

## 3. 최소 프레임워크에 남은 필수 작업

### A. 대화 결과의 안전한 저장

- 오케스트레이터가 합의된 plan을 생성·수정하는 API 또는 CLI 추가
- task 목표, 범위, 완료 조건, 제약, 입출력, 의존성, 자원, 위험도, 예산, 검증 방법 저장
- 저장 전 JSON Schema와 graph 검증
- 사용자 승인 전 task 실행 금지
- plan과 task 수정 이력을 decision과 audit에 기록

이 기능은 자동 계획기가 아니다. 대화에서 이미 합의된 내용을 영속화하는 writer다.

### B. 의존성 및 실행 준비 상태

- 모든 dependency가 `completed`인 `pending` task만 `ready`로 전환
- 존재하지 않는 dependency와 순환 dependency 거부
- 완료 task 이후 후속 task 승격
- plan 전체 완료 조건과 실제 task 상태 대조

현재 scheduler는 `ready` task의 충돌 batch만 계산하며 dependency 승격을 수행하지 않는다.

### C. 실제 provider 실행 완성

- OpenAI-compatible API와 Ollama 실제 환경 smoke test
- provider별 구조화 응답 검증
- timeout, 인증 실패, rate limit, 잘못된 응답 처리
- 실제 token과 비용 기록 검증
- 사용자 승인과 데이터 분류에 따른 network 및 external transfer 정책 확인

현재 mock end-to-end는 동작하지만 실제 모델을 사용한 전체 프로젝트 수행은 검증되지 않았다.

### D. 실제 AI 법정 검토

- 검토자 2명, 변호자 2명, 심사자 1명을 provider session으로 실행
- 역할별 system prompt와 prompt version 고정
- 구조화된 주장, 변호, 판결 응답 검증
- 서로 다른 session과 가능한 경우 다른 모델 또는 seed 사용
- 재심사 task 결과를 원래 case와 다시 연결

현재 법정 lifecycle과 독립 session 구조는 있으나 CLI court evaluator는 전달받은 verdict를 구조화하는 단계다.

### E. 다중 프로세스 안전성과 템플릿 실사용 검증

- `.aipf/locks`를 이용한 task 및 자원 lock 구현
- 동시에 실행된 두 `aipf run`의 중복 dispatch 차단
- stale lock 복구
- 복사한 깨끗한 템플릿에서 첫 대화, plan 저장, task 실행, review, resume, 완료까지 수행
- 설치와 복사 절차에서 원본 절대 경로나 개발 환경이 남지 않는지 확인

## 4. `0.1.0` 진입 조건

다음 조건을 모두 충족한 뒤 버전을 `0.1.0`으로 변경하고 `v0.1.0` tag를 만든다.

1. 사용자가 첫 세션에서 대화로 합의한 plan과 task를 YAML 직접 편집 없이 저장할 수 있다.
2. dependency graph가 task를 정확히 승격하고 순환을 거부한다.
3. 실제 OpenAI-compatible 또는 Ollama provider로 task 하나를 완료한다.
4. 고위험 task를 실제 provider 기반 2-2-1 법정 검토로 판정한다.
5. 복사된 템플릿에서 전체 프로젝트 lifecycle과 중단 복구가 통과한다.

## 5. Telegram 규칙

- `AIPF_TELEGRAM_BOT_TOKEN`, `AIPF_TELEGRAM_CHAT_ID`는 환경 변수로만 사용한다.
- 사용자 shell은 `csh` 기반이므로 필요하면 `setenv`를 안내한다.
- 알림 전송 때마다 사용자에게 묻지 않는다.
- `PROJECT.md`의 `Telegram 알림 설정`에 있는 조건만 따른다.
- 지원 조건: `task_completed`, `plan_completed`, `blocked`, `never`
- 완료 알림에는 다음 task, 다음 수행 항목, 사용자 행동도 포함한다.

## 6. 사용자 협업 방식

- 한국어로 답한다.
- ADHD 형식과 Caveman `full` 형식을 유지한다.
- 첫 줄에 다음 행동을 제시한다.
- 다단계 작업은 번호를 붙이고 현재 단계를 매 turn 다시 표시한다.
- 목록은 최대 5개로 제한한다.
- 구체적인 시간 추정을 제공한다.

## 7. 새 세션의 정확한 첫 행동

1. `PROJECT.md`, `docs/NEXT_SESSION_HANDOFF.md`, `docs/FRAMEWORK_SPEC.md`를 읽는다.
2. Git working tree와 `main`의 remote 동기화 상태를 확인한다.
3. 위 A~E를 기반으로 `P_0002` 초안을 작성한다.
4. `P_0002`를 구현하기 전에 사용자에게 범위와 순서를 확인받는다.

첫 구현 task는 A의 “대화에서 합의된 plan과 task를 안전하게 저장하는 writer”로 제안한다.

## 8. 주의사항

- 자동 task 분해 기능을 다시 제안하지 않는다.
- 사용자 확인 없이 정식 버전, Git tag, GitHub Release를 만들지 않는다.
- Telegram token이나 chat ID 값을 출력하거나 파일에 저장하지 않는다.
- `.venv`와 cache를 템플릿에 commit하지 않는다.
