# 운영 및 장애 복구 가이드

## 설치

Python 3.12 가상 환경에서 설치한다.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/aipf --help
```

## 프로젝트 시작

```bash
aipf --directory /path/to/project init --goal "프로젝트 목표"
aipf --directory /path/to/project validate
aipf --directory /path/to/project status
```

사용자는 생성된 `PROJECT.md`와 CLI만 사용한다. `.aipf/handoff/`와 `.aipf/runtime.yaml`은 오케스트레이터가 관리한다.

## 승인

Task 완료 후 다음 작업을 계속한다.

```bash
aipf --directory /path/to/project approve continue --target T_0000
```

네트워크, 외부 전송, 삭제 승인은 각각 대상 task에 기록한다.

```bash
aipf --directory /path/to/project approve network --target T_0000
aipf --directory /path/to/project approve external_transfer --target T_0000
aipf --directory /path/to/project approve delete --target T_0000
```

## 중단 복구

먼저 저장소 무결성을 확인한 뒤 재개한다.

```bash
aipf --directory /path/to/project validate
aipf --directory /path/to/project status
aipf --directory /path/to/project resume
```

`resume`은 만료된 heartbeat를 확인한다. 첫 timeout이면 새 session에서 재시도한다. 두 번째 실패면 task를 `blocked`로 유지하고 사용자 결정을 기다린다.

수동으로 YAML을 수정하지 않는다. 복구 불가능한 손상이 있으면 `.aipf/` 전체를 보존한 뒤 `aipf validate` 출력과 관련 handoff ID를 수집한다.

## Telegram

Bot token과 chat ID는 환경 변수에만 둔다.

```bash
export AIPF_TELEGRAM_BOT_TOKEN='...'
export AIPF_TELEGRAM_CHAT_ID='...'
```

Task가 `completed`가 되면 알림을 한 번 전송한다. 미설정, timeout, API 오류는 task 상태를 변경하지 않는다. Token이나 chat ID를 YAML, 로그, `PROJECT.md`에 기록하지 않는다.

`PROJECT.md`에서 전송 조건만 수정한다. 조건 충족 시 별도 승인 없이 전송한다.

```text
## Telegram 알림 설정

- 전송 조건: task_completed, plan_completed, blocked
```

모든 전송을 끄려면 `- 전송 조건: never`로 변경한다. 오케스트레이터가 `PROJECT.md`를 재생성해도 이 설정은 유지된다.

## 릴리스 검증

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/aipf --directory /tmp/aipf-smoke init --goal "smoke test"
.venv/bin/aipf --directory /tmp/aipf-smoke validate
```

릴리스 전 workspace 탈출, 비밀정보 마스킹, capability token, 재시도, rollover, 법정 검토, Telegram 오류 격리 테스트가 모두 통과해야 한다.
