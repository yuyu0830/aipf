# 합의된 결정

1. Python 3.12, Linux, CLI 중심으로 시작한다.
2. OpenAI-compatible API, Ollama, mock 실행기를 지원하는 제공자 독립 구조를 사용한다.
3. 병렬 작업과 고정·동적 역할을 모두 지원한다.
4. 상태는 에이전트별, 용도별 YAML handoff 파일에 저장한다.
5. 사용자는 CLI와 `PROJECT.md`로 진행 상황을 확인한다.
6. `PROJECT.md`는 오케스트레이터만 수정한다.
7. 서브 에이전트는 자신의 handoff만 수정한다.
8. 컨텍스트 사용률 70%에서 handoff 저장 후 새 세션으로 재개한다.
9. 실행 실패 또는 heartbeat timeout은 1회 재시도 후 사용자에게 질문한다.
10. 비용 가중치를 높인 모델 라우팅을 사용한다.
11. 충돌 가능 작업은 선언된 읽기·쓰기·자원 집합으로 찾아 직렬화한다.
12. 고위험 검토에는 적대적 검토자 2명, 변호자 2명, 심사자 1명을 사용한다.
13. 심사 거절은 개선과 재심사를 최대 3회 반복한다.
14. task 종료는 알림형, plan 종료는 사용자 확인이 필요한 중단형 체크포인트다.
15. 비밀정보는 환경 변수 또는 OS secret store에만 보관하고 기록에서 마스킹한다.
16. 에이전트는 기본적으로 task 하나를 수행하고 공용 완료 스크립트로 결과를 제출한다.
17. 완료 스크립트는 일회용 capability token을 검증하고 task를 `review`로 전환한다.
18. 검토 승인으로 `completed`가 되면 사용자 승인 전까지 다음 task를 시작하지 않는다.
19. 모든 수행 시도는 결과와 실패 원인 분석을 task handoff에 기록한다.
20. Telegram 완료 알림은 `completed` 전환 후 실행하며 실패를 기록하거나 재시도하지 않는다.
21. Telegram 전송은 사용자에게 매번 묻지 않으며 `PROJECT.md`의 `task_completed`, `plan_completed`, `blocked`, `never` 조건으로 제어한다.
22. 프로젝트와 CLI 이름은 `aipf`로 확정한다. 필수 기능 완료 전에는 `0.0.0.dev0`를 사용하고 Git tag와 정식 release를 만들지 않는다.
