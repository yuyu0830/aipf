# AI Project Framework

파일 기반 handoff로 오케스트레이터와 여러 서브 에이전트를 연결하는 프로젝트 수행 프레임워크다.

현재 저장소는 합의된 요구사항, 구현 기준, 검증 가능한 최소 CLI 골격을 제공한다.

상태: `0.0.0.dev0` 개발 단계. `P_0001` 구현 체크포인트 승인 완료 (2026-09-08)

## 핵심 원칙

- 사용자는 CLI와 오케스트레이터가 관리하는 `PROJECT.md`만 사용한다.
- 서브 에이전트는 자기 handoff만 읽고 쓴다.
- 대화 세션이 아니라 구조화된 YAML handoff가 실행 상태의 기준이다.
- 충돌 가능 작업은 직렬 실행하고, 나머지는 병렬 실행할 수 있다.
- 고위험 결과는 2명의 적대적 검토자, 2명의 변호자, 1명의 심사자가 검토한다.
- 컨텍스트 사용률 70%에서 handoff를 저장하고 새 세션으로 재개한다.

## 문서

- [프레임워크 명세](docs/FRAMEWORK_SPEC.md)
- [handoff 프로토콜](docs/HANDOFF_PROTOCOL.md)
- [법정 검토 모델](docs/COURT_REVIEW.md)
- [보안 및 운영](docs/SECURITY_OPERATIONS.md)
- [결정 기록](docs/DECISIONS.md)
- [구현 계획 P_0001](docs/IMPLEMENTATION_PLAN.md)
- [운영 및 장애 복구](docs/OPERATIONS.md)
- [새 세션 handoff](docs/NEXT_SESSION_HANDOFF.md)

## 목표 CLI

```text
aipf init
aipf run
aipf resume
aipf status
aipf inspect
aipf answer
aipf approve
aipf cancel
aipf validate
```

## 개발 실행

```bash
python -m pip install -e .
aipf --directory /tmp/my-project init --goal "프로젝트 목표"
aipf --directory /tmp/my-project validate
aipf --directory /tmp/my-project status
```

전체 테스트:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

현재 기준은 Python 3.12에서 54개 테스트 통과다. Handoff, runtime, config는 `src/aipf/schemas/`의 JSON Schema로 검증한다.

기본 config에는 mock 모델이 등록된다. `routing.models`에 provider, model, 점수, 로컬 실행 여부, context 크기를 선언하면 라우터가 비용 가중치와 보안 정책을 적용해 결정적으로 모델을 선택한다.

현재 `run`과 `resume`은 worker subprocess 실행, heartbeat, 예산 제한, 1회 재시도, stale session 복구, 70% context rollover를 지원한다. 고위험 결과는 독립된 2명의 검토자, 2명의 변호자, 1명의 심사자가 검토하며 3회 제한과 사용자 체크포인트를 적용한다.

Task가 `completed`로 전환되면 Telegram 설정이 있는 경우 완료 결과, 다음 task, 다음 수행 항목, 사용자 행동을 전송한다. 미설정 또는 전송 실패는 task 상태를 변경하지 않는다.
