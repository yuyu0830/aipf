from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import yaml

from aipf.providers.base import AgentRequest


SCORE_FIELDS = ("quality", "cost", "security", "context", "tools")


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    provider: str
    model: str
    quality: float
    cost: float
    security: float
    context: float
    tools: float
    local: bool = False
    context_tokens: int = 0
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("provider and model must not be empty")
        for field in SCORE_FIELDS:
            value = getattr(self, field)
            if not 0 <= value <= 1:
                raise ValueError(f"{field} score must be between 0 and 1")
        if self.context_tokens < 0:
            raise ValueError("context_tokens must not be negative")


@dataclass(frozen=True, slots=True)
class RoutingRequirements:
    external_allowed: bool = True
    sensitive: bool = False
    minimum_context_tokens: int = 0
    tools_required: bool = False


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    provider: str
    model: str
    score: float
    local: bool


class NoEligibleModelError(ValueError):
    pass


def candidates_from_config(config: Mapping[str, Any]) -> list[ModelCandidate]:
    models = config.get("routing", {}).get("models", [])
    if not isinstance(models, list):
        raise ValueError("routing.models must be a list")
    return [ModelCandidate(**item) for item in models]


def select_model(
    candidates: list[ModelCandidate],
    weights: Mapping[str, float],
    requirements: RoutingRequirements = RoutingRequirements(),
) -> RoutingDecision:
    missing = set(SCORE_FIELDS) - weights.keys()
    if missing:
        raise ValueError(f"missing routing weights: {', '.join(sorted(missing))}")
    if abs(sum(float(weights[field]) for field in SCORE_FIELDS) - 1.0) > 1e-9:
        raise ValueError("routing weights must sum to 1.0")

    eligible = []
    for candidate in candidates:
        if not candidate.enabled:
            continue
        if (requirements.sensitive or not requirements.external_allowed) and not candidate.local:
            continue
        if candidate.context_tokens < requirements.minimum_context_tokens:
            continue
        if requirements.tools_required and candidate.tools <= 0:
            continue
        score = sum(float(weights[field]) * getattr(candidate, field) for field in SCORE_FIELDS)
        eligible.append((score, candidate))
    if not eligible:
        raise NoEligibleModelError("no model satisfies routing and security requirements")
    score, selected = sorted(eligible, key=lambda item: (-item[0], item[1].provider, item[1].model))[0]
    return RoutingDecision(selected.provider, selected.model, round(score, 12), selected.local)


def build_agent_request(
    task: dict[str, Any],
    decision: RoutingDecision,
    *,
    system_prompt: str,
    prompt_version: str,
) -> AgentRequest:
    if task.get("kind") != "task":
        raise ValueError("agent request requires a task handoff")
    budget = task.get("budget", {})
    max_output_tokens = int(budget["max_output_tokens"])
    payload = {
        "task_id": task["id"],
        "goal": task["goal"],
        "scope": task["scope"],
        "inputs": task["inputs"],
        "outputs": task["outputs"],
        "constraints": task["constraints"],
        "acceptance_criteria": task["acceptance_criteria"],
        "verification": task["verification"],
        "progress": task["progress"],
    }
    return AgentRequest(
        model=decision.model,
        system=system_prompt,
        input=yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        max_output_tokens=max_output_tokens,
        metadata={
            "task_id": task["id"], "provider": decision.provider,
            "routing_score": decision.score, "prompt_version": prompt_version,
        },
    )
