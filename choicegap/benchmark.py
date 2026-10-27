from __future__ import annotations

import argparse
import json
import math
import random
from statistics import mean

from .engine import DRIVERS, EXPERIMENTS, Session, choice_probability, find_experiment


FIXED_ORDER = [item.id for item in EXPERIMENTS[:4]]


def _select_experiment(session: Session, strategy: str, turn: int, rng: random.Random):
    if strategy == "adaptive":
        public = session.next_experiment()
        assert public is not None
        return find_experiment(public["id"]), bool(public["flipped"])
    if strategy == "fixed":
        return find_experiment(FIXED_ORDER[turn % len(FIXED_ORDER)]), rng.random() < 0.5
    available = [item for item in EXPERIMENTS if item.id not in session.used]
    return rng.choice(available), rng.random() < 0.5


def _option_features(option: dict[str, object]) -> dict[str, float]:
    return {
        "impact": float(option["impact"]),
        "price": (3.0 - float(option["price"])) / 3.0,
        "convenience": float(option["convenience"]),
        "trust": float(option["trust"]),
    }


def one_run(true_driver: str, strategy: str, seed: int, rounds: int = 4) -> dict[str, float | bool]:
    rng = random.Random(seed)
    # Stated preference is independently wrong 55% of the time to create a real gap-detection task.
    stated = true_driver if rng.random() > 0.55 else rng.choice([d for d in DRIVERS if d != true_driver])
    session = Session.create(stated, f"I care most about {stated}.", seed=seed)
    for turn in range(rounds):
        exp, flipped = _select_experiment(session, strategy, turn, rng)
        canonical = "a" if rng.random() < choice_probability(exp, true_driver) else "b"
        displayed = ("b" if canonical == "a" else "a") if flipped else canonical
        session.observe(exp.id, displayed, flipped)
    predicted = max(session.posterior, key=session.posterior.get)
    brier = mean((session.posterior[d] - (1.0 if d == true_driver else 0.0)) ** 2 for d in DRIVERS)
    return {"correct": predicted == true_driver, "brier": brier, "confidence_true": session.posterior[true_driver]}


def one_robustness_run(true_driver: str, strategy: str, seed: int, rounds: int = 4) -> dict[str, float | bool]:
    """Out-of-model participant with continuous weights, variable noise, lapses, and side bias."""
    rng = random.Random(seed)
    weights = {driver: rng.uniform(0.2, 1.2) for driver in DRIVERS}
    weights[true_driver] += 1.5
    temperature = rng.uniform(0.65, 1.25)
    stated = true_driver if rng.random() > 0.55 else rng.choice([d for d in DRIVERS if d != true_driver])
    session = Session.create(stated, "", seed=seed)
    for turn in range(rounds):
        exp, flipped = _select_experiment(session, strategy, turn, rng)
        a = _option_features(exp.a)
        b = _option_features(exp.b)
        delta = sum(weights[key] * (a[key] - b[key]) for key in DRIVERS) / temperature
        p_a = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, delta))))
        canonical = "a" if rng.random() < p_a else "b"
        if rng.random() < 0.08:  # attention lapse
            canonical = rng.choice(("a", "b"))
        displayed = ("b" if canonical == "a" else "a") if flipped else canonical
        if rng.random() < 0.06:  # modest left-position heuristic
            displayed = "a"
        session.observe(exp.id, displayed, flipped)
    predicted = max(session.posterior, key=session.posterior.get)
    brier = mean((session.posterior[d] - (1.0 if d == true_driver else 0.0)) ** 2 for d in DRIVERS)
    return {"correct": predicted == true_driver, "brier": brier, "confidence_true": session.posterior[true_driver]}


def _summarize(runs: list[dict[str, float | bool]]) -> dict[str, float]:
    return {
        "top1_accuracy": round(mean(float(run["correct"]) for run in runs), 4),
        "mean_brier": round(mean(float(run["brier"]) for run in runs), 4),
        "mean_probability_on_true_driver": round(mean(float(run["confidence_true"]) for run in runs), 4),
    }


def run_benchmark(participants: int = 2000, seed: int = 2026) -> dict[str, object]:
    results: dict[str, object] = {"participants_per_strategy": participants, "rounds": 4, "seed": seed, "strategies": {}}
    for strategy_index, strategy in enumerate(("adaptive", "fixed", "random")):
        runs = []
        for index in range(participants):
            true_driver = DRIVERS[index % len(DRIVERS)]
            runs.append(one_run(true_driver, strategy, seed + strategy_index * 1_000_000 + index))
        results["strategies"][strategy] = _summarize(runs)
    adaptive = results["strategies"]["adaptive"]
    fixed = results["strategies"]["fixed"]
    results["adaptive_accuracy_lift_vs_fixed_pp"] = round(100 * (adaptive["top1_accuracy"] - fixed["top1_accuracy"]), 2)
    results["robustness"] = {"description": "Continuous mixed weights with variable noise, 8% lapses, and 6% left-side bias.", "strategies": {}}
    for strategy_index, strategy in enumerate(("adaptive", "fixed", "random")):
        runs = [
            one_robustness_run(DRIVERS[index % len(DRIVERS)], strategy, seed + 4_000_000 + strategy_index * 1_000_000 + index)
            for index in range(participants)
        ]
        results["robustness"]["strategies"][strategy] = _summarize(runs)
    robust_adaptive = results["robustness"]["strategies"]["adaptive"]
    robust_fixed = results["robustness"]["strategies"]["fixed"]
    results["robustness"]["adaptive_accuracy_lift_vs_fixed_pp"] = round(100 * (robust_adaptive["top1_accuracy"] - robust_fixed["top1_accuracy"]), 2)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ChoiceGap's adaptive experiment policy.")
    parser.add_argument("--participants", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_benchmark(args.participants, args.seed)
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")


if __name__ == "__main__":
    main()

