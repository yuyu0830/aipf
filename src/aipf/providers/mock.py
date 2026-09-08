from __future__ import annotations

from collections.abc import Callable

from aipf.providers.base import AgentRequest, AgentResponse


class MockProvider:
    def __init__(self, handler: Callable[[AgentRequest], str] | None = None):
        self.handler = handler or (lambda request: request.input)

    def run(self, request: AgentRequest) -> AgentResponse:
        output = self.handler(request)
        return AgentResponse(output=output)
