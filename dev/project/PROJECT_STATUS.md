# AIPF 개발 현재 상태

## 현재 버전

- Markdown 템플릿 `v1`

## 현재 요약

- Markdown 중심 틀 개편은 완료했다.
- AIPF 자체 개발 자료와 사용자용 템플릿을 분리하는 Change를 진행 중이다.
- 사용자 프로젝트의 초기 상태는 `template/project/PROJECT_STATUS.md`에 별도로 둔다.

## 완료 내역

| Change | 한 줄 결과 | 버전 | 상세 |
|---|---|---|---|
| Markdown 중심 구조 개편 | Python CLI를 제거하고 clone-ready Markdown 구조로 전환 | v1 | [기록](../archive/2026-09-27-markdown-redesign/CHANGE.md) |

## 진행 중

- 현재 Change: [AIPF 개발과 적용 템플릿 분리](../change/dev-template-separation/CHANGE.md)
- 현재 위치: 구현·격리 검증·독립 Change 검토 통과, 최종 완료 확인 준비
- 문제: 기존 release는 아직 이전 Python CLI 배포본이며 이번 Change 완료 후 갱신한다.

## 앞으로 할 일

- 검증된 Change 브랜치를 커밋·push하고 최종 결과를 확인받는다.
- 사용자 최종 완료 확인 후 main 병합·태그·게시 및 template-only release 배포를 수행한다.

## 다음 행동

- 행동: 사용자 최종 완료 확인을 받는다.
- 이유: 검토된 변경을 main과 release에 반영하기 전 완료 경계를 확인한다.
- 변경: 확인 후 개발 상태·archive·Git refs 및 release

## 알려진 문제

- 실제 release는 최종 완료 확인 전까지 이전 배포본을 유지한다.

## 관련 소스

- `template/`: 사용자에게 배포할 틀
- `dev/scripts/`: 개발·배포 도구
- `dev/tests/`: 배포 검증
