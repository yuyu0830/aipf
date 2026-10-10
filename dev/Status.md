# 현재 개선 중

## Dev/AIPF 분리 결과의 main·release 반영

- 대상: Dev. 개발 기록은 `dev/`, 사용자에게 제공할 틀은 `template/`로 분리한다. Dev에서 AIPF의 운영 절차를 실행하지 않는다.
- 브랜치: `change/dev-template-separation`. 실제 커밋·push 상태는 Git을 확인하고 이어간다.
- 합의한 범위: 최소 개발 문서, `Dev`/`AIPF` 명령 구분과 모호할 때 재질문, 중요한 체크포인트에서만 커밋·push, template-only release.
- 현재 위치: 개발 브랜치의 폴더·문서 정리는 끝났다. 완료한 개선은 [History.md](History.md)에 기록했고, main·release 반영이 남았다.
- 확인: 문서 경로와 링크를 확인했다. 이번 Dev 정리에서 `template/` 내용은 변경하지 않았다.
- 남은 일: 사용자 최종 완료 확인 후 main 병합과 release 게시. 현재 release는 이전 Python CLI 배포본이다. Git 작업 시에만 [DEV.md](DEV.md)의 절차를 읽는다.
- 완료할 때: main·release 반영 결과를 History에 짧게 추가하고 이 항목을 제거한다.
