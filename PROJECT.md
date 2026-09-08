# PROJECT

## 목표

파일 구조와 관리 객체를 중심으로, 사용자가 진행 방식을 이해하고 통제할 수 있는 AI 프로젝트 프레임워크를 제작한다.

## 현재 상태

- 현재 단계: `0.1.0` 최소 프로젝트 틀 완성
- 진행률: 100%
- 완료: 파일 구조, Plan, Task, Audit, 최소 실행, 사용자 검토, Telegram 알림
- 진행 중: 없음

## 활성 task

- 없음

## 차단 사항

- 없음

## 최근 결정

- 2026-09-08: `PROJECT.md`, Plan, Task, Audit 중심 구조를 확정함
- 2026-09-08: `docs/`, `ref/`, `src/`의 목적과 AI 접근 권한을 확정함
- 2026-09-08: Knowledge와 영구 Session 객체를 사용하지 않기로 함
- 2026-09-08: 자동 계획과 자동 심사 없이 사용자 승인 기반 순차 실행을 확정함
- 2026-09-08: 최소 프로젝트 틀의 버전을 `0.1.0`으로 확정함

## 검토 결과

- 핵심 lifecycle 테스트 6개 통과
- `approve`, `revise`, `retry`, `cancel` 사용자 검토 경로 통과
- Telegram 성공, 미설정, 실패 격리 테스트 통과
- Python 문법 검사와 CLI help smoke test 통과

## 산출물

- `AGENTS.md`, `SKILLS.md`, `MEMORY_MAP.md`
- `docs/PROJECT_DIRECTION.md`
- Plan, Task, Audit 기반 `src/aipf/` 최소 실행 틀
- 새 프로젝트용 안내 문서 template

## 다음 체크포인트

Git commit과 `origin/main` push 후 실제 프로젝트에서 시행착오 진행

## Telegram 알림 설정

- 전송 조건: task_completed, plan_completed, blocked
