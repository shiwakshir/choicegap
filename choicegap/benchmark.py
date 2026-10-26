from __future__ import annotations

import argparse
import json
import math
import random
from statistics import mean

from .engine import DRIVERS, EXPERIMENTS, Session, choice_probability, find_experiment


FIXED_ORDER = [item.id for item in EXPERIMENTS[:4]]


def one_run(true_driver: str, strategy: str, seed: int, rounds: int = 4) -> dict[str, float | bool]:
    rng = random.Random(seed)
    # Stated preference is independently wrong 55% of the time to create a real gap-detection task.
    stated = true_driver if rng.random() > 0.55 else rng.choice([d for d in DRIVERS if d != true_driver])
    session = Session.create(stated, f"I care most about {stated}.", seed=seed)
    for turn in range(rounds):
        if strategy == "adaptive":
            public = session.next_experiment()
            assert public is not None
            exp = find_experiment(public["id"])
            flipped = bool(public["flipped"])
        elif strategy == "fixed":
            exp = find_experiment(FIXED_ORDER[turn % len(FIXED_ORDER)])
            flipped = rng.random() < 0.5
        else:
            available = [item for item in EXPERIMENTS if item.id not in session.used]
            exp = rng.choice(available)
            flipped = rng.random() < 0.5
        canonical = "a" if rng.random() < choice_probability(exp, true_driver) else "b"
        displayed = ("b" if canonical == "a" else "a") if flipped else canonical
        session.observe(exp.id, displayed, flipped)
    predicted = max(session.posterior, key=session.posterior.get)
    brier = mean((session.posterior[d] - (1.0 if d == true_driver else 0.0)) ** 2 for d in DRIVERS)
    return {"correct": predicted == true_driver, "brier": brier, "confidence_true": session.posterior[true_driver]}


def run_benchmark(participants: int = 2000, seed: int = 2026) -> dict[str, object]:
    results: dict[str, object] = {"participants_per_strategy": participants, "rounds": 4, "seed": seed, "strategies": {}}
    for strategy_index, strategy in enumerate(("adaptive", "fixed", "random")):
        runs = []
        for index in range(participants):
            true_driver = DRIVERS[index % len(DRIVERS)]
            runs.append(one_run(true_driver, strategy, seed + strategy_index * 1_000_000 + index))
        results["strategies"][strategy] = {
            "top1_accuracy": round(mean(float(run["correct"]) for run in runs), 4),
            "mean_brier": round(mean(float(run["brier"]) for run in runs), 4),
            "mean_probability_on_true_driver": round(mean(float(run["confidence_true"]) for run in runs), 4),
        }
    adaptive = results["strategies"]["adaptive"]
    fixed = results["strategies"]["fixed"]
    results["adaptive_accuracy_lift_vs_fixed_pp"] = round(100 * (adaptive["top1_accuracy"] - fixed["top1_accuracy"]), 2)
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

