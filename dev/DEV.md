# Dev

AIPF는 Markdown 문서와 Git으로 AI 프로젝트를 이어갈 수 있게 하는 틀이다. 사용자는 준비된 `release`를 clone해서 사용한다. 별도 AIPF 설치나 배포 스크립트 실행은 필요 없다.

## 두 작업의 구분

| 명령 구분 | 대상 | 예시 |
|---|---|---|
| `Dev` | 이 저장소의 개발 환경·메모·아카이브·Git 운영 | 개발 문서 정리, 배포 방식 변경 |
| `AIPF` | 사용자 프로젝트에 제공할 `template/`의 내용·동작 | 계획 지침 수정, 사용자용 문서 개선 |

구분이 없더라도 문맥이 분명하면 이어서 작업한다. 어느 쪽인지 헷갈리면 반드시 사용자에게 다시 묻는다. Dev에서 AIPF의 프로젝트 운영 절차를 그대로 수행하지 않는다.

## 남겨둘 문서와 기록

- 루트 `AGENTS.md`: 에이전트가 작업 대상을 구분하는 짧은 안내.
- 이 문서: 개발 목적, 영역 구분, Git 배포 방식.
- [STATUS.md](STATUS.md): 현재 작업과 다음 행동. 별도 계획·인계 문서는 필요할 때만 만든다.
- `dev/archive/YYYY-MM-DD-주제/`: 교체한 문서와 중요한 자료. 출처·보관 이유·현재 대체 문서를 짧게 적고, 과거 기록을 현재 요구사항으로 사용하지 않는다.

혼자 로컬에서 필요한 최소 작업부터 한다. 무결성 검사, 과한 오류 감지, 상시 검증 도구나 일괄 검토 절차는 미리 만들지 않는다. 이후 실제 필요에 맞춰 늘린다.

## Git과 배포

`main`은 Dev와 AIPF 원본을 함께 보관한다. 작업은 별도 브랜치에서 커밋·push하고, 사용자가 최종 완료를 확인한 뒤 main에 병합한다. `release`는 승인된 main의 `template/`만 루트에 담는 사용자용 브랜치이며 직접 편집하지 않는다.

main 반영 후 에이전트가 아래 Git 명령을 직접 수행한다. 현재 저장소의 기존 로컬 release를 부모로 이어 이전 배포 이력을 보존한다. 별도 배포 스크립트는 두지 않는다.

```bash
git fetch origin
source_commit=$(git rev-parse main)
template_tree=$(git rev-parse "$source_commit:template")
release_commit=$(git commit-tree "$template_tree" -p release -m "release: publish template from $source_commit")
git update-ref refs/heads/release "$release_commit"
git push origin release
```

로컬 release가 origin/release보다 뒤처졌다면 먼저 동기화한다. 분기되거나 충돌하면 상태를 보고하고 해결 방향을 묻는다. 강제 push나 기존 이력 덮어쓰기는 하지 않는다. 개발 문서·자료는 release에 포함하지 않는다.
