# 지난 개선

필요한 내용만 검색해서 읽는다. 원본 문서는 `git show <커밋>:<당시 경로>`로 확인한다. 과거 지침은 현재 작업 규칙으로 적용하지 않는다.

## 2026-09-27 — Markdown 중심 틀 전환

- 결과: Python CLI를 제거하고 별도 설치 없이 clone해서 사용하는 Markdown 틀로 전환했다.
- 이유: 문서와 Git으로 프로젝트를 이어가면서 설치 부담을 줄인다.
- 관련 커밋: `9511de6`에 완료 상태가 기록돼 있다.
- 원본 기록: `9511de6:archive/2026-09-27-markdown-redesign/CHANGE.md`.

## 2026-10-10 — Dev와 AIPF 분리 및 개발 운영 단순화

- 결과: 개발 기록은 `dev/`, 사용자용 틀은 `template/`로 분리했다. README는 `template/README.md`만 남겼다.
- 이유: AIPF 자체 개발과 AIPF로 수행하는 프로젝트의 목표·절차가 섞이지 않게 한다.
- Dev 운영: 새 요청은 Requests, 진행 중 작업은 Status, 완료한 개선은 History로 관리한다. 평소에는 Requests와 Status만 읽고, 명령 대상이 모호하면 사용자에게 묻는다.
- 최소 구현: 복잡한 개발 지침과 배포 스크립트를 제거했다. 중요한 체크포인트에서만 커밋·push하며, release는 승인된 main의 template을 Git 명령으로 내보낸다.
- 원본 보존: 별도 Dev archive 폴더를 제거했다. 이전 구조 원본은 `3993be0:dev/archive/2026-10-10-dev-simplification/`에 남아 있다. 이후 문서 정리 커밋은 `git log -- dev/History.md`로 찾는다.
- 확인: 운영 문서 링크와 변경 범위를 확인했다. 사용자용 template 내용은 이번 Dev 정리에서 변경하지 않았다.
- 반영 상태: 개발 브랜치의 정리 결과다. main 병합과 실제 release 갱신은 [Status.md](Status.md)에 남겨뒀다.
