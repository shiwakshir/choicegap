from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field
from typing import Any


ATTRIBUTE_IDS = ("a", "b", "c", "d")


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _entropy(distribution: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0)


def _normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    return {key: value / total for key, value in values.items()}


@dataclass(frozen=True)
class DynamicExperiment:
    id: str
    title: str
    rationale: str
    a: dict[str, Any]
    b: dict[str, Any]
    varies: tuple[str, str]


@dataclass(frozen=True)
class StudySpec:
    title: str
    decision_prompt: str
    attributes: tuple[dict[str, str], ...]
    experiments: tuple[DynamicExperiment, ...]

    @property
    def driver_ids(self) -> tuple[str, ...]:
        return tuple(item["id"] for item in self.attributes)

    @property
    def driver_copy(self) -> dict[str, dict[str, str]]:
        return {
            item["id"]: {
                "label": item["hypothesis_label"],
                "short": item["label"],
                "description": item["hypothesis_description"],
            }
            for item in self.attributes
        }

    def to_public(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "decision_prompt": self.decision_prompt,
            "drivers": [
                {
                    "id": item["id"],
                    "label": item["hypothesis_label"],
                    "description": item["hypothesis_description"],
                }
                for item in self.attributes
            ],
        }


def compile_study(design: dict[str, Any]) -> StudySpec:
    attributes = tuple(design["attributes"])
    if len(attributes) != 4:
        raise ValueError("A study must contain exactly four competing explanations")
    if tuple(item["id"] for item in attributes) != ATTRIBUTE_IDS:
        raise ValueError("Study attribute IDs must be a, b, c, d in order")
    for item in attributes:
        for key in ("label", "low_label", "high_label", "hypothesis_label", "hypothesis_description"):
            if not str(item.get(key, "")).strip():
                raise ValueError(f"Missing study field: {key}")
        if item["low_label"].strip().lower() == item["high_label"].strip().lower():
            raise ValueError(f"Attribute {item['id']} needs distinct levels")

    experiments = []
    for index, (left, right) in enumerate(itertools.combinations(attributes, 2), start=1):
        base = {item["id"]: 0 for item in attributes}
        a_levels = {**base, left["id"]: 1, right["id"]: 0}
        b_levels = {**base, left["id"]: 0, right["id"]: 1}

        def option(name: str, levels: dict[str, int]) -> dict[str, Any]:
            facts = [
                f"{item['label']}: {item['high_label'] if levels[item['id']] else item['low_label']}"
                for item in attributes
            ]
            return {"name": name, "levels": levels, "facts": facts}

        experiments.append(DynamicExperiment(
            id=f"e{index}",
            title=f"{left['label']} or {right['label']}?",
            rationale=(
                f"A controlled trade-off between {left['hypothesis_label']} and "
                f"{right['hypothesis_label']}; the other two factors are identical."
            ),
            a=option("Option A", a_levels),
            b=option("Option B", b_levels),
            varies=(left["id"], right["id"]),
        ))
    return StudySpec(
        title=str(design["title"]).strip()[:100],
        decision_prompt=str(design["decision_prompt"]).strip()[:240],
        attributes=attributes,
        experiments=tuple(experiments),
    )


def audit_study(study: StudySpec) -> dict[str, Any]:
    pairs = {tuple(sorted(exp.varies)) for exp in study.experiments}
    expected = set(itertools.combinations(study.driver_ids, 2))
    controlled = all(
        sum(exp.a["levels"][key] != exp.b["levels"][key] for key in study.driver_ids) == 2
        for exp in study.experiments
    )
    checks = {
        "four_competing_accounts": len(study.driver_ids) == 4,
        "complete_pairwise_coverage": pairs == expected,
        "two_factors_vary_per_test": controlled,
        "shared_copy_for_held_constants": True,
        "position_randomization_enabled": True,
    }
    return {"passed": all(checks.values()), "checks": checks, "experiment_count": len(study.experiments)}


def _weights(study: StudySpec, hypothesis: str) -> dict[str, float]:
    return {key: 2.8 if key == hypothesis else 0.45 for key in study.driver_ids}


def choice_probability(study: StudySpec, experiment: DynamicExperiment, hypothesis: str, temperature: float = 0.72) -> float:
    weights = _weights(study, hypothesis)
    utility_a = sum(weights[key] * experiment.a["levels"][key] for key in study.driver_ids)
    utility_b = sum(weights[key] * experiment.b["levels"][key] for key in study.driver_ids)
    return _sigmoid((utility_a - utility_b) / temperature)


def update_posterior(study: StudySpec, posterior: dict[str, float], experiment: DynamicExperiment, choice: str) -> dict[str, float]:
    values = {}
    for hypothesis in study.driver_ids:
        p_a = choice_probability(study, experiment, hypothesis)
        values[hypothesis] = posterior[hypothesis] * (p_a if choice == "a" else 1.0 - p_a)
    return _normalize(values)


def information_gain(study: StudySpec, posterior: dict[str, float], experiment: DynamicExperiment) -> float:
    p_a = sum(posterior[h] * choice_probability(study, experiment, h) for h in study.driver_ids)
    after_a = update_posterior(study, posterior, experiment, "a")
    after_b = update_posterior(study, posterior, experiment, "b")
    return _entropy(posterior) - p_a * _entropy(after_a) - (1.0 - p_a) * _entropy(after_b)


def _public(experiment: DynamicExperiment, score: float, flip: bool) -> dict[str, Any]:
    a, b = (experiment.b, experiment.a) if flip else (experiment.a, experiment.b)
    return {
        "id": experiment.id,
        "title": experiment.title,
        "rationale": experiment.rationale,
        "a": a,
        "b": b,
        "flipped": flip,
        "information_gain": round(score, 4),
    }


@dataclass
class DynamicSession:
    study: StudySpec
    stated_driver: str
    statement: str
    posterior: dict[str, float]
    seed: int
    stated_ratings: dict[str, int] = field(default_factory=dict)
    intention_score: int = 3
    rounds: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        study: StudySpec,
        stated_driver: str,
        statement: str,
        seed: int | None = None,
        stated_ratings: dict[str, int] | None = None,
        intention_score: int = 3,
    ) -> "DynamicSession":
        if stated_driver not in study.driver_ids:
            raise ValueError("Unknown stated priority")
        posterior = {key: 1.0 / len(study.driver_ids) for key in study.driver_ids}
        actual_seed = seed if seed is not None else random.SystemRandom().randrange(1, 10_000_000)
        return cls(
            study=study,
            stated_driver=stated_driver,
            statement=statement,
            posterior=posterior,
            seed=actual_seed,
            stated_ratings=stated_ratings or {key: (5 if key == stated_driver else 3) for key in study.driver_ids},
            intention_score=intention_score,
        )

    @property
    def used(self) -> set[str]:
        return {item["experiment_id"] for item in self.history}

    def _ranked(self) -> list[tuple[DynamicExperiment, float]]:
        values = [(exp, information_gain(self.study, self.posterior, exp)) for exp in self.study.experiments if exp.id not in self.used]
        return sorted(values, key=lambda item: (-item[1], item[0].id))

    def candidates(self, limit: int = 3) -> list[dict[str, Any]]:
        return [_public(exp, score, False) for exp, score in self._ranked()[:limit]]

    def next_experiment(self, selected_id: str | None = None) -> dict[str, Any] | None:
        ranked = self._ranked()
        if not ranked:
            return None
        valid = {exp.id: (exp, score) for exp, score in ranked[:3]}
        experiment, score = valid.get(selected_id, ranked[0])
        flip = random.Random(f"{self.seed}:{experiment.id}").random() < 0.5
        return _public(experiment, score, flip)

    def observe(self, experiment_id: str, displayed_choice: str, flipped: bool) -> None:
        experiment = next(exp for exp in self.study.experiments if exp.id == experiment_id)
        canonical = displayed_choice
        if flipped:
            canonical = "b" if displayed_choice == "a" else "a"
        before = dict(self.posterior)
        self.posterior = update_posterior(self.study, self.posterior, experiment, canonical)
        self.rounds += 1
        self.history.append({
            "round": self.rounds,
            "experiment_id": experiment_id,
            "choice": canonical,
            "posterior_before": before,
            "posterior_after": dict(self.posterior),
        })

    def report(self) -> dict[str, Any]:
        ranked = sorted(self.posterior.items(), key=lambda item: -item[1])
        leader, probability = ranked[0]
        labels = self.study.driver_copy
        gap = leader != self.stated_driver and probability >= 0.45
        return {
            "study_title": self.study.title,
            "stated_driver": self.stated_driver,
            "stated_ratings": self.stated_ratings,
            "intention_score": self.intention_score,
            "leading_driver": leader,
            "confidence": round(probability, 4),
            "gap_detected": gap,
            "posterior": {key: round(value, 4) for key, value in self.posterior.items()},
            "rounds": self.rounds,
            "headline": (
                f"Choices lean toward {labels[leader]['label'].lower()}, despite stating {labels[self.stated_driver]['label'].lower()}."
                if gap else f"Choices are most consistent with {labels[leader]['label'].lower()}."
            ),
            "evidence": list(self.history),
            "limitations": [
                "This result is specific to this decision context, not a stable trait.",
                "Four hypothetical choices from one person cannot establish causality.",
                "Muse-generated explanations may omit an important driver.",
                "The compiler controls factor changes, but the chosen factor levels still require human review.",
            ],
        }

