from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .engine import DRIVER_COPY, DRIVERS


META_BASE_URL = "https://api.meta.ai/v1"


class MetaClient:
    """Small dependency-free client for Meta Model API structured outputs."""

    def __init__(self) -> None:
        self.api_key = os.getenv("MODEL_API_KEY", "").strip()
        self.model = os.getenv("META_MODEL", "muse-spark-1.3").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def fallback_plan(candidates: list[dict[str, Any]], posterior: dict[str, float]) -> dict[str, Any]:
        ranked_accounts = sorted(posterior, key=posterior.get, reverse=True)
        leader, rival = ranked_accounts[:2]
        return {
            "experiment_id": candidates[0]["id"],
            "objective": "separate_leaders",
            "leading_account": leader,
            "rival_account": rival,
            "predicted_split": f"A controlled trade-off should make {leader} and {rival} predict different choices.",
            "falsification_rule": f"A choice favored by {rival} would count against the current {leader} account.",
            "reason": "Maximum expected information gain.",
            "source": "local",
        }

    def _structured(self, messages: list[dict[str, str]], name: str, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": schema},
            },
        }
        request = urllib.request.Request(
            f"{META_BASE_URL}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return json.loads(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Meta Model API request failed: {exc}") from exc

    def parse_statement(self, statement: str, fallback: str) -> dict[str, Any]:
        if not self.enabled:
            return {"driver": fallback, "reason": "Selected directly by the respondent.", "source": "local"}
        schema = {
            "type": "object",
            "properties": {
                "driver": {"type": "string", "enum": list(DRIVERS)},
                "reason": {"type": "string"},
            },
            "required": ["driver", "reason"],
            "additionalProperties": False,
        }
        result = self._structured([
            {"role": "system", "content": (
                "You are the intake planner for a careful UX research agent. Map only the respondent's stated "
                "priority to one candidate driver: trust=proof/reputation, control=approval/settings, "
                "price=cost/value, risk=data exposure/retention. Do not infer actual behaviour."
            )},
            {"role": "user", "content": f"Explicit selection: {fallback}\nStatement: {statement}"},
        ], "stated_preference", schema)
        result["source"] = self.model
        return result

    def choose_experiment(self, candidates: list[dict[str, Any]], posterior: dict[str, float]) -> dict[str, Any]:
        ranked_accounts = sorted(posterior, key=posterior.get, reverse=True)
        leader, rival = ranked_accounts[:2]
        if not self.enabled:
            return self.fallback_plan(candidates, posterior)
        ids = [item["id"] for item in candidates]
        schema = {
            "type": "object",
            "properties": {
                "experiment_id": {"type": "string", "enum": ids},
                "objective": {"type": "string", "enum": ["separate_leaders", "challenge_leader", "resolve_stated_gap"]},
                "leading_account": {"type": "string", "enum": list(DRIVERS)},
                "rival_account": {"type": "string", "enum": list(DRIVERS)},
                "predicted_split": {"type": "string"},
                "falsification_rule": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["experiment_id", "objective", "leading_account", "rival_account", "predicted_split", "falsification_rule", "reason"],
            "additionalProperties": False,
        }
        result = self._structured([
            {"role": "system", "content": (
                "You are a falsification agent for an adaptive UX study. Treat the two strongest accounts as rivals, "
                "then select exactly one validated candidate that makes them predict meaningfully different choices. "
                "Prefer expected information gain. State the predicted disagreement and, before observing the answer, "
                "the result that would count against the current leader. Never invent an experiment, diagnose a person, "
                "or claim causality. Keep each explanation under 30 words."
            )},
            {"role": "user", "content": json.dumps({
                "posterior": posterior,
                "current_leader": leader,
                "strongest_rival": rival,
                "account_meanings": {key: DRIVER_COPY[key]["description"] for key in DRIVERS},
                "validated_candidates": candidates,
            })},
        ], "falsification_plan", schema)
        result["source"] = self.model
        return result

    def narrate_report(self, report: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"summary": report["headline"], "next_step": "Repeat with more respondents and one preregistered manipulation.", "source": "local"}
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "next_step": {"type": "string"},
            },
            "required": ["summary", "next_step"],
            "additionalProperties": False,
        }
        result = self._structured([
            {"role": "system", "content": (
                "Write a cautious UX research synthesis from supplied computed evidence. Use probabilistic language. "
                "Do not add facts, omit limitations, diagnose a person, or claim causal proof. Summary max 55 words; "
                "next step max 25 words."
            )},
            {"role": "user", "content": json.dumps(report)},
        ], "research_synthesis", schema)
        result["source"] = self.model
        return result

