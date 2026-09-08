# Basic example

```bash
python -m aipf.cli --directory /tmp/aipf-demo init --goal "작은 CLI 도구 제작"
python -m aipf.cli --directory /tmp/aipf-demo validate
python -m aipf.cli --directory /tmp/aipf-demo status
```

초기화 후 `/tmp/aipf-demo/PROJECT.md`가 사용자 인터페이스다. 세부 상태는 `/tmp/aipf-demo/.aipf/handoff/`에 저장된다.
