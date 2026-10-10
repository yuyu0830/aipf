# Dev 현재 상태

- 작업 브랜치: `change/dev-template-separation`.
- AIPF 자체 개발 자료와 사용자에게 제공할 `template/`를 분리했다. README는 `template/README.md`만 둔다.
- Dev는 루트 `AGENTS.md`, [DEV.md](DEV.md), 이 상태 문서로 줄였다. 기존 지침·명세·Change·Handoff·자료 공간과 배포 스크립트는 [구조 변경 아카이브](archive/2026-10-10-dev-simplification/SNAPSHOT.md)에 보존했다.
- 앞으로 사용자 명령은 `Dev`와 `AIPF`로 구분한다. 표기가 없고 대상이 헷갈리면 반드시 다시 묻는다.
- 이번 Dev 정리에서 `template/` 내용은 변경하지 않았다. 실제 필요가 생길 때만 Dev 문서나 도구를 추가한다.
- main과 release에는 아직 이번 작업을 반영하지 않았다. 현재 release는 이전 Python CLI 배포본이다.
- 다음 행동: 사용자 최종 완료 확인 후 main 병합과 template-only release 게시. 이번 아카이브는 옛 Dev 구조의 보존이며 작업의 최종 완료 처리가 아니다.
