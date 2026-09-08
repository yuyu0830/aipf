from __future__ import annotations

from aipf.providers.base import AgentRequest, AgentResponse
from aipf.providers.http import post_json


class OllamaProvider:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def run(self, request: AgentRequest) -> AgentResponse:
        value = post_json(
            f"{self.base_url}/api/chat",
            {
                "model": request.model,
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.input},
                ],
                "stream": False,
                "options": {"num_predict": request.max_output_tokens},
            },
            {},
            self.timeout,
        )
        return AgentResponse(
            output=value["message"]["content"],
            input_tokens=int(value.get("prompt_eval_count", 0)),
            output_tokens=int(value.get("eval_count", 0)),
            raw=value,
        )
