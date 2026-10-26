from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


DRIVERS = ("trust", "control", "price", "risk")

DRIVER_COPY = {
    "trust": {
        "label": "Trust & proof",
        "short": "proof",
        "description": "Independent evidence and a recognizable vendor reduce uncertainty.",
    },
    "control": {
        "label": "User control",
        "short": "control",
        "description": "Review, approval, and granular settings matter more than automation speed.",
    },
    "price": {
        "label": "Price sensitivity",
        "short": "price",
        "description": "The respondent trades other benefits for a lower monthly cost.",
    },
    "risk": {
        "label": "Risk avoidance",
        "short": "risk",
        "description": "Data retention and organizational exposure dominate the decision.",
    },
}

# Utilities are deliberately distinct but not deterministic. Each row is a
# falsifiable, single-driver account of behaviour, not a personality label.
HYPOTHESES: dict[str, dict[str, float]] = {
    "trust": {"trust": 2.6, "control": 0.6, "price": 0.5, "risk": 0.8},
    "control": {"trust": 0.6, "control": 2.6, "price": 0.5, "risk": 0.8},
    "price": {"trust": 0.5, "control": 0.5, "price": 2.8, "risk": 0.6},
    "risk": {"trust": 0.7, "control": 0.8, "price": 0.4, "risk": 2.7},
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
        "proof-v-price",
        "Proof or savings?",
        "Trades independent evidence against price while holding controls and retention fixed.",
        {"name": "Verity", "price": 24, "trust": 1, "control": 0, "risk": 0,
         "facts": ["$24 per seat", "Independent security audit", "Basic admin controls", "30-day retention"]},
        {"name": "Pico", "price": 12, "trust": 0, "control": 0, "risk": 0,
         "facts": ["$12 per seat", "Vendor security statement", "Basic admin controls", "30-day retention"]},
    ),
    Experiment(
        "control-v-price",
        "Control or savings?",
        "Trades granular approval controls against price; proof and retention stay fixed.",
        {"name": "Steer", "price": 24, "trust": 0, "control": 1, "risk": 0,
         "facts": ["$24 per seat", "Vendor security statement", "Approve every action", "30-day retention"]},
        {"name": "Swift", "price": 12, "trust": 0, "control": 0, "risk": 0,
         "facts": ["$12 per seat", "Vendor security statement", "Fully automatic", "30-day retention"]},
    ),
    Experiment(
        "retention-v-price",
        "Low exposure or savings?",
        "Trades zero retention against price while proof and controls stay fixed.",
        {"name": "Vanish", "price": 24, "trust": 0, "control": 0, "risk": 1,
         "facts": ["$24 per seat", "Vendor security statement", "Basic admin controls", "Zero data retention"]},
        {"name": "Archive", "price": 12, "trust": 0, "control": 0, "risk": 0,
         "facts": ["$12 per seat", "Vendor security statement", "Basic admin controls", "30-day retention"]},
    ),
    Experiment(
        "proof-v-control",
        "Evidence or control?",
        "Separates trust in external proof from desire for direct control at the same price.",
        {"name": "Assure", "price": 18, "trust": 1, "control": 0, "risk": 0,
         "facts": ["$18 per seat", "Independent security audit", "Fully automatic", "30-day retention"]},
        {"name": "Command", "price": 18, "trust": 0, "control": 1, "risk": 0,
         "facts": ["$18 per seat", "Vendor security statement", "Approve every action", "30-day retention"]},
    ),
    Experiment(
        "proof-v-retention",
        "Evidence or low exposure?",
        "Separates reassurance from proof and reassurance from reduced data exposure.",
        {"name": "Certified", "price": 18, "trust": 1, "control": 0, "risk": 0,
         "facts": ["$18 per seat", "Independent security audit", "Basic admin controls", "30-day retention"]},
        {"name": "Ephemeral", "price": 18, "trust": 0, "control": 0, "risk": 1,
         "facts": ["$18 per seat", "Vendor security statement", "Basic admin controls", "Zero data retention"]},
    ),
    Experiment(
        "control-v-retention",
        "Control or low exposure?",
        "Separates intervention control from passive risk reduction at the same price.",
        {"name": "Review", "price": 18, "trust": 0, "control": 1, "risk": 0,
         "facts": ["$18 per seat", "Vendor security statement", "Approve every action", "30-day retention"]},
        {"name": "Forget", "price": 18, "trust": 0, "control": 0, "risk": 1,
         "facts": ["$18 per seat", "Vendor security statement", "Fully automatic", "Zero data retention"]},
    ),
)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _entropy(distribution: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0)


def _utility(option: dict[str, Any], hypothesis: str) -> float:
    weights = HYPOTHESES[hypothesis]
    price_score = (24.0 - float(option["price"])) / 12.0
    return (
        weights["trust"] * float(option["trust"])
        + weights["control"] * float(option["control"])
        + weights["risk"] * float(option["risk"])
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


def prior_from_stated(driver: str | None, confidence: float = 0.48) -> dict[str, float]:
    if driver not in DRIVERS:
        return {key: 0.25 for key in DRIVERS}
    remainder = (1.0 - confidence) / (len(DRIVERS) - 1)
    return {key: confidence if key == driver else remainder for key in DRIVERS}


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


@dataclass
class Session:
    stated_driver: str
    statement: str
    posterior: dict[str, float]
    seed: int
    rounds: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, stated_driver: str, statement: str, seed: int | None = None) -> "Session":
        actual_seed = seed if seed is not None else random.SystemRandom().randrange(1, 10_000_000)
        return cls(stated_driver, statement, prior_from_stated(stated_driver), actual_seed)

    @property
    def used(self) -> set[str]:
        return {item["experiment_id"] for item in self.history}

    def candidates(self, limit: int = 3) -> list[dict[str, Any]]:
        return [experiment_public(exp, score) for exp, score in ranked_experiments(self.posterior, self.used)[:limit]]

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
        if flipped:
            canonical_choice = "b" if displayed_choice == "a" else "a"
        before = dict(self.posterior)
        self.posterior = update_posterior(self.posterior, experiment, canonical_choice)
        self.rounds += 1
        self.history.append({
            "round": self.rounds,
            "experiment_id": experiment_id,
            "choice": canonical_choice,
            "displayed_choice": displayed_choice,
            "posterior_before": before,
            "posterior_after": dict(self.posterior),
        })

    def report(self) -> dict[str, Any]:
        ranked = sorted(self.posterior.items(), key=lambda item: -item[1])
        leader, probability = ranked[0]
        gap = leader != self.stated_driver and probability >= 0.45
        return {
            "stated_driver": self.stated_driver,
            "leading_driver": leader,
            "confidence": round(probability, 4),
            "gap_detected": gap,
            "posterior": {key: round(value, 4) for key, value in self.posterior.items()},
            "rounds": self.rounds,
            "headline": (
                f"Choices lean toward {DRIVER_COPY[leader]['label'].lower()}, despite stating "
                f"{DRIVER_COPY[self.stated_driver]['label'].lower()}."
                if gap else
                f"Choices are most consistent with {DRIVER_COPY[leader]['label'].lower()}."
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
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "stated_driver": self.stated_driver,
            "statement": self.statement,
            "posterior": self.posterior,
            "seed": self.seed,
            "rounds": self.rounds,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Session":
        return cls(
            stated_driver=payload["stated_driver"],
            statement=payload.get("statement", ""),
            posterior={key: float(value) for key, value in payload["posterior"].items()},
            seed=int(payload["seed"]),
            rounds=int(payload.get("rounds", 0)),
            history=list(payload.get("history", [])),
        )

