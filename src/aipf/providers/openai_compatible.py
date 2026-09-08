from __future__ import annotations

import os

from aipf.providers.base import AgentRequest, AgentResponse, ProviderError, ProviderErrorCode
from aipf.providers.http import post_json


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key_env: str = "OPENAI_API_KEY", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout = timeout

    def run(self, request: AgentRequest) -> AgentResponse:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(
                ProviderErrorCode.CONFIGURATION,
                f"missing environment variable: {self.api_key_env}",
            )
        value = post_json(
            f"{self.base_url}/chat/completions",
            {
                "model": request.model,
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.input},
                ],
                "max_tokens": request.max_output_tokens,
            },
            {"Authorization": f"Bearer {api_key}"},
            self.timeout,
        )
        usage = value.get("usage", {})
        return AgentResponse(
            output=value["choices"][0]["message"]["content"],
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw=value,
        )
