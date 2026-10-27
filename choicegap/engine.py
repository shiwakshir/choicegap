from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


DRIVERS = ("impact", "price", "convenience", "trust")
GAP_PROBABILITY_THRESHOLD = 0.45
MIN_INFORMATIVE_CHOICES = 3
EXPECTED_INFORMATIVE_CHOICES = 4

DRIVER_COPY = {
    "impact": {
        "label": "Environmental impact",
        "short": "impact",
        "description": "A materially lower estimated footprint drives the choice.",
    },
    "price": {
        "label": "Affordability",
        "short": "price",
        "description": "The respondent trades other benefits for a lower delivery fee.",
    },
    "convenience": {
        "label": "Convenience",
        "short": "convenience",
        "description": "A precise, faster delivery window dominates the decision.",
    },
    "trust": {
        "label": "Claim credibility",
        "short": "trust",
        "description": "Independent verification matters more than an unverified green claim.",
    },
}

# Utilities are deliberately distinct but not deterministic. Each row is a
# falsifiable, single-driver account of behaviour, not a personality label.
HYPOTHESES: dict[str, dict[str, float]] = {
    "impact": {"impact": 2.8, "price": 0.45, "convenience": 0.55, "trust": 0.7},
    "price": {"impact": 0.55, "price": 2.8, "convenience": 0.6, "trust": 0.5},
    "convenience": {"impact": 0.55, "price": 0.6, "convenience": 2.8, "trust": 0.45},
    "trust": {"impact": 0.7, "price": 0.45, "convenience": 0.45, "trust": 2.8},
}


@dataclass(frozen=True)
class Experiment:
    id: str
    title: str
    rationale: str
    a: dict[str, Any]
    b: dict[str, Any]


EXPERIMENTS = (
    Experiment(
        "impact-v-price",
        "Lower impact or free delivery?",
        "Trades a lower estimated footprint against the delivery fee while holding timing and evidence fixed.",
        {"name": "Lower-impact slot", "price": 3, "impact": 1, "convenience": 0, "trust": 0,
         "facts": ["£3 delivery fee", "Estimated delivery emissions: 60% lower", "Flexible delivery day", "Retailer calculation"]},
        {"name": "Free standard slot", "price": 0, "impact": 0, "convenience": 0, "trust": 0,
         "facts": ["Free delivery", "Standard delivery emissions", "Flexible delivery day", "Retailer calculation"]},
    ),
    Experiment(
        "convenience-v-price",
        "Precise timing or free delivery?",
        "Trades a two-hour delivery window against the fee while impact and evidence stay fixed.",
        {"name": "Timed slot", "price": 3, "impact": 0, "convenience": 1, "trust": 0,
         "facts": ["£3 delivery fee", "Standard delivery emissions", "Two-hour delivery window", "Retailer calculation"]},
        {"name": "Free flexible slot", "price": 0, "impact": 0, "convenience": 0, "trust": 0,
         "facts": ["Free delivery", "Standard delivery emissions", "Flexible delivery day", "Retailer calculation"]},
    ),
    Experiment(
        "trust-v-price",
        "Verified claim or free delivery?",
        "Trades independent verification against the fee while impact and timing stay fixed.",
        {"name": "Verified slot", "price": 3, "impact": 0, "convenience": 0, "trust": 1,
         "facts": ["£3 delivery fee", "Standard delivery emissions", "Flexible delivery day", "Method independently verified"]},
        {"name": "Free self-reported slot", "price": 0, "impact": 0, "convenience": 0, "trust": 0,
         "facts": ["Free delivery", "Standard delivery emissions", "Flexible delivery day", "Retailer calculation"]},
    ),
    Experiment(
        "impact-v-convenience",
        "Lower impact or precise timing?",
        "Separates environmental impact from convenience at the same fee and evidence level.",
        {"name": "Lower-impact slot", "price": 1.5, "impact": 1, "convenience": 0, "trust": 0,
         "facts": ["£1.50 delivery fee", "Estimated delivery emissions: 60% lower", "Flexible delivery day", "Retailer calculation"]},
        {"name": "Timed standard slot", "price": 1.5, "impact": 0, "convenience": 1, "trust": 0,
         "facts": ["£1.50 delivery fee", "Standard delivery emissions", "Two-hour delivery window", "Retailer calculation"]},
    ),
    Experiment(
        "impact-v-trust",
        "Impact magnitude or credible evidence?",
        "Separates a stronger self-reported reduction from independent verification at the same fee and timing.",
        {"name": "Bigger claimed reduction", "price": 1.5, "impact": 1, "convenience": 0, "trust": 0,
         "facts": ["£1.50 delivery fee", "Estimated delivery emissions: 60% lower", "Flexible delivery day", "Retailer calculation"]},
        {"name": "Verified standard footprint", "price": 1.5, "impact": 0, "convenience": 0, "trust": 1,
         "facts": ["£1.50 delivery fee", "Standard delivery emissions", "Flexible delivery day", "Method independently verified"]},
    ),
    Experiment(
        "convenience-v-trust",
        "Precise timing or credible evidence?",
        "Separates convenience from confidence in the environmental evidence at the same fee and footprint.",
        {"name": "Timed slot", "price": 1.5, "impact": 0, "convenience": 1, "trust": 0,
         "facts": ["£1.50 delivery fee", "Standard delivery emissions", "Two-hour delivery window", "Retailer calculation"]},
        {"name": "Verified flexible slot", "price": 1.5, "impact": 0, "convenience": 0, "trust": 1,
         "facts": ["£1.50 delivery fee", "Standard delivery emissions", "Flexible delivery day", "Method independently verified"]},
    ),
)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _entropy(distribution: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0)


def _utility(option: dict[str, Any], hypothesis: str) -> float:
    weights = HYPOTHESES[hypothesis]
    price_score = (3.0 - float(option["price"])) / 3.0
    return (
        weights["impact"] * float(option["impact"])
        + weights["convenience"] * float(option["convenience"])
        + weights["trust"] * float(option["trust"])
        + weights["price"] * price_score
    )


def choice_probability(experiment: Experiment, hypothesis: str, temperature: float = 0.72) -> float:
    """P(choose A | hypothesis) under a soft utility choice model."""
    delta = (_utility(experiment.a, hypothesis) - _utility(experiment.b, hypothesis)) / temperature
    return _sigmoid(delta)


def normalized(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total <= 0:
        return {key: 1.0 / len(values) for key in values}
    return {key: value / total for key, value in values.items()}


def update_posterior(
    posterior: dict[str, float], experiment: Experiment, choice: str
) -> dict[str, float]:
    likelihoods = {}
    for hypothesis in DRIVERS:
        p_a = choice_probability(experiment, hypothesis)
        likelihoods[hypothesis] = p_a if choice == "a" else 1.0 - p_a
    return normalized({key: posterior[key] * likelihoods[key] for key in DRIVERS})


def expected_information_gain(posterior: dict[str, float], experiment: Experiment) -> float:
    before = _entropy(posterior)
    p_a = sum(posterior[h] * choice_probability(experiment, h) for h in DRIVERS)
    after_a = update_posterior(posterior, experiment, "a")
    after_b = update_posterior(posterior, experiment, "b")
    expected_after = p_a * _entropy(after_a) + (1.0 - p_a) * _entropy(after_b)
    return before - expected_after


def ranked_experiments(posterior: dict[str, float], used: set[str]) -> list[tuple[Experiment, float]]:
    ranked = [
        (experiment, expected_information_gain(posterior, experiment))
        for experiment in EXPERIMENTS
        if experiment.id not in used
    ]
    return sorted(ranked, key=lambda item: (-item[1], item[0].id))


def experiment_public(experiment: Experiment, score: float | None = None, flip: bool = False) -> dict[str, Any]:
    a, b = (experiment.b, experiment.a) if flip else (experiment.a, experiment.b)
    payload = {
        "id": experiment.id,
        "title": experiment.title,
        "rationale": experiment.rationale,
        "a": a,
        "b": b,
        "flipped": flip,
    }
    if score is not None:
        payload["information_gain"] = round(score, 4)
    return payload


def find_experiment(experiment_id: str) -> Experiment:
    return next(item for item in EXPERIMENTS if item.id == experiment_id)


def assess_evidence_quality(informative_choices: int, holdout_consistent: bool | None) -> str:
    if informative_choices < MIN_INFORMATIVE_CHOICES or holdout_consistent is not True:
        return "low"
    if informative_choices >= EXPECTED_INFORMATIVE_CHOICES:
        return "high"
    return "moderate"


def report_headline(
    *,
    labels: dict[str, dict[str, str]],
    stated_driver: str,
    leading_driver: str,
    gap_detected: bool,
    evidence_quality: str,
    probability: float,
) -> str:
    if evidence_quality == "low":
        return "The evidence is inconclusive because the response-quality threshold was not met."
    if probability < GAP_PROBABILITY_THRESHOLD:
        return "The choices do not yet distinguish clearly between the candidate explanations."
    if gap_detected:
        return (
            f"Choices lean toward {labels[leading_driver]['label'].lower()}, despite stating "
            f"{labels[stated_driver]['label'].lower()}."
        )
    return f"Choices are most consistent with {labels[leading_driver]['label'].lower()}."


@dataclass
class Session:
    stated_driver: str
    statement: str
    posterior: dict[str, float]
    seed: int
    stated_ratings: dict[str, int] = field(default_factory=dict)
    intention_score: int = 3
    rounds: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    holdout_source: dict[str, Any] | None = None
    holdout_consistent: bool | None = None

    @classmethod
    def create(
        cls,
        stated_driver: str,
        statement: str,
        seed: int | None = None,
        stated_ratings: dict[str, int] | None = None,
        intention_score: int = 3,
    ) -> "Session":
        actual_seed = seed if seed is not None else random.SystemRandom().randrange(1, 10_000_000)
        # Stated attitudes and observed choices are deliberately kept separate.
        # A uniform behavioural prior prevents the survey answer from baking in alignment.
        posterior = {key: 1.0 / len(DRIVERS) for key in DRIVERS}
        return cls(
            stated_driver=stated_driver,
            statement=statement,
            posterior=posterior,
            seed=actual_seed,
            stated_ratings=stated_ratings or {key: (5 if key == stated_driver else 3) for key in DRIVERS},
            intention_score=intention_score,
        )

    @property
    def used(self) -> set[str]:
        return {item["experiment_id"] for item in self.history}

    def candidates(self, limit: int = 3) -> list[dict[str, Any]]:
        candidates = []
        for experiment, score in ranked_experiments(self.posterior, self.used)[:limit]:
            candidate = experiment_public(experiment, score)
            candidate["predictions"] = {
                driver: round(choice_probability(experiment, driver), 4) for driver in DRIVERS
            }
            candidates.append(candidate)
        return candidates

    def next_experiment(self, selected_id: str | None = None) -> dict[str, Any] | None:
        ranked = ranked_experiments(self.posterior, self.used)
        if not ranked:
            return None
        valid = {experiment.id: (experiment, score) for experiment, score in ranked[:3]}
        experiment, score = valid.get(selected_id, ranked[0])
        flip = random.Random(f"{self.seed}:{experiment.id}").random() < 0.5
        return experiment_public(experiment, score, flip)

    def observe(self, experiment_id: str, displayed_choice: str, flipped: bool) -> None:
        experiment = find_experiment(experiment_id)
        canonical_choice = displayed_choice
        if displayed_choice in ("a", "b") and flipped:
            canonical_choice = "b" if displayed_choice == "a" else "a"
        before = dict(self.posterior)
        if canonical_choice in ("a", "b"):
            self.posterior = update_posterior(self.posterior, experiment, canonical_choice)
        self.rounds += 1
        observation = {
            "round": self.rounds,
            "experiment_id": experiment_id,
            "choice": canonical_choice,
            "displayed_choice": displayed_choice,
            "flipped": flipped,
            "posterior_before": before,
            "posterior_after": dict(self.posterior),
        }
        self.history.append(observation)
        if self.holdout_source is None and canonical_choice in ("a", "b"):
            self.holdout_source = {"experiment_id": experiment_id, "choice": canonical_choice, "flipped": flipped}

    def holdout_experiment(self) -> dict[str, Any] | None:
        if not self.holdout_source:
            return None
        experiment = find_experiment(self.holdout_source["experiment_id"])
        payload = experiment_public(experiment, 0.0, not bool(self.holdout_source["flipped"]))
        payload["holdout"] = True
        return payload

    def observe_holdout(self, displayed_choice: str, flipped: bool) -> None:
        if not self.holdout_source:
            return
        if displayed_choice not in ("a", "b"):
            self.holdout_consistent = None
            return
        canonical = ("b" if displayed_choice == "a" else "a") if flipped else displayed_choice
        self.holdout_consistent = canonical == self.holdout_source["choice"]

    def report(self) -> dict[str, Any]:
        ranked = sorted(self.posterior.items(), key=lambda item: -item[1])
        leader, probability = ranked[0]
        informative_choices = sum(item["choice"] in ("a", "b") for item in self.history)
        evidence_quality = assess_evidence_quality(informative_choices, self.holdout_consistent)
        highest_rating = max(self.stated_ratings.values())
        stated_priorities = [key for key, value in self.stated_ratings.items() if value == highest_rating]
        gap = (
            leader not in stated_priorities
            and probability >= GAP_PROBABILITY_THRESHOLD
            and evidence_quality != "low"
        )
        return {
            "stated_driver": self.stated_driver,
            "stated_priorities": stated_priorities,
            "stated_ratings": self.stated_ratings,
            "intention_score": self.intention_score,
            "opt_out_count": sum(item["choice"] == "outside" for item in self.history),
            "holdout_consistent": self.holdout_consistent,
            "informative_choices": informative_choices,
            "evidence_quality": evidence_quality,
            "leading_driver": leader,
            "confidence": round(probability, 4),
            "gap_detected": gap,
            "posterior": {key: round(value, 4) for key, value in self.posterior.items()},
            "rounds": self.rounds,
            "headline": report_headline(
                labels=DRIVER_COPY,
                stated_driver=self.stated_driver,
                leading_driver=leader,
                gap_detected=gap,
                evidence_quality=evidence_quality,
                probability=probability,
            ),
            "evidence": [
                {"experiment_id": item["experiment_id"], "choice": item["choice"], "round": item["round"]}
                for item in self.history
            ],
            "limitations": [
                "This is evidence about this decision context, not a stable personality trait.",
                "A small number of hypothetical choices cannot establish a causal effect.",
                "The candidate explanations are deliberately incomplete; unmeasured factors may matter.",
                "Results depend on the utility model and the exact wording and levels shown.",
                "A failed or skipped holdout makes the individual result inconclusive.",
            ],
        }

