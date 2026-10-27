"""Create readable reports from recorded evaluations; never calls a model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .review_benchmark import summarize


PRICING_SOURCE = 'https://dev.meta.ai/docs/pricing-rate-limits'


def build_report(root: Path, output: Path):
    summary = summarize(root)
    rows_file = root / 'calls.jsonl'
    rows = [json.loads(s) for s in rows_file.read_text(encoding='utf-8').splitlines()] if rows_file.exists() else []
    measured = []
    for row in rows:
        usage = row.get('usage', [])
        if not usage:
            continue
        item = usage[-1]['usage']
        if 'prompt_tokens' not in item or 'completion_tokens' not in item:
            continue
        prompt = item['prompt_tokens']
        cached = item.get('prompt_tokens_details', {}).get('cached_tokens', 0)
        completion = item['completion_tokens']
        measured.append({'id': row['id'], 'prompt': prompt, 'cached': cached, 'completion': completion,
                         'estimated_usd': ((prompt - cached) * 1.25 + cached * .15 + completion * 4.25) / 1_000_000})
    cost = {'source': PRICING_SOURCE, 'verified_date': '2026-10-27',
            'rates_usd_per_million': {'uncached_input': 1.25, 'cached_input': .15, 'output': 4.25},
            'applies_to': 'muse-spark-1.3 Standard only; estimates are not an invoice',
            'calls_with_usage': len(measured), 'recorded_calls': len(rows),
            'estimated_usd': round(sum(r['estimated_usd'] for r in measured), 6) if all(r['model'] == 'muse-spark-1.3' for r in rows) else None,
            'prompt_tokens': sum(r['prompt'] for r in measured),
            'cached_input_tokens': sum(r['cached'] for r in measured),
            'completion_tokens': sum(r['completion'] for r in measured)}
    (root / 'cost-estimate.json').write_text(json.dumps(cost, indent=2), encoding='utf-8')
    lines = ['# ChoiceGap: recorded Muse design-review evaluation', '',
             f"Status: **{summary['status']}**. Recorded {len(rows)} of 108 planned calls.", '',
             f"Frozen protocol: `{summary['protocol_sha256']}`.", '',
             '## Scope', '',
             'Six planted defect types on one synthetic grocery checkout template, with affected side reversed; six clean render repeats. Three runs per screen in each of two input conditions. Pilots are stored separately and excluded. These are controlled repeats, not independently sampled real studies.', '',
             '## Recorded outcomes', '',
             '| Input condition | Calls | Planted calls | Visual-basis screening matches | Clean calls with any finding | Validation failures | API errors | Mean latency |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for condition, result in summary['conditions'].items():
        latency = result['mean_latency_seconds']
        lines.append(f"| {condition} | {result['calls']} | {result['planted_calls']} | {result['proxy_matches']} | {result['clean_calls_with_any_finding']}/{result['clean_calls']} | {result['validation_failures']} | {result['api_errors']} | {latency if latency is not None else 'unmeasured'} s |")
    lines += ['', '### Image-conditioned screening by planted type', '',
              '| Planted issue | Calls | Fixed-rule matches |', '|---|---:|---:|']
    for kind in ('default', 'prominence', 'badge', 'leading_wording', 'availability', 'hidden_fee'):
        selected = [r for r in rows if r['condition'] == 'with_image' and r['expected'] == kind]
        lines.append(f"| {kind} | {len(selected)} | {sum(bool(r.get('score', {}).get('proxy_detection')) for r in selected)} |")
    lines += ['', 'Visual-basis keyword matches are an unvalidated screening proxy. The text-only condition cannot produce validated image-basis findings, so this contrast is not an unbiased semantic accuracy lift. Exact observations and suggested controls need adjudication; a keyword match alone does not verify correctness, side, or an adequate control. Clean calls with any finding are a conservative screening statistic, not adjudicated false alarms.', '',
              '## Review status', '',
              f"Human-adjudicated planted calls: {sum(r['primary_adjudicated_calls'] for r in summary['conditions'].values())}. Human-adjudicated clean calls: {sum(r['primary_clean_adjudicated_calls'] for r in summary['conditions'].values())}.", '',
              'The shuffled review packet, label template, original outputs and frozen screenshots accompany this report. Missing labels remain missing rather than being treated as correct.', '',
              '## Usage and estimated cost', '',
              f"Returned usage: {cost['prompt_tokens']:,} input tokens ({cost['cached_input_tokens']:,} cached) and {cost['completion_tokens']:,} output tokens across {cost['calls_with_usage']} calls with usable counts.", '',
              f"Estimated Standard-mode cost: ${cost['estimated_usd']:.4f}." if cost['estimated_usd'] is not None else 'Cost estimate unavailable for the returned model.', '',
              f"Uses [Meta's published pricing]({PRICING_SOURCE}), checked 27 October 2026; excludes calls without returned usage and separate pilot runs. Actual account billing may differ.", '',
              '## Limits', '',
              '- The prototype and prompt were improved using pilot observations; this is a development evaluation, not an untouched external holdout.',
              '- It measures review of synthetic screenshots, not researcher time saved, customer demand or improved field-study outcomes.',
              '- Six clean renders repeat one underlying clean layout. Repeated calls and renders do not establish generalization to other products.',
              '- A screenshot-versus-no-screenshot comparison measures access to visual context. It does not compare Muse against another provider or against equivalent textual descriptions.',
              '- The participant engine benchmark is separate and does not measure Muse.', '']
    spot_path = root / 'developer-spotcheck.json'
    if spot_path.exists():
        spot = json.loads(spot_path.read_text(encoding='utf-8'))
        lines += ['## Developer spot check (separate from primary scoring)', '',
                  spot['scope'], '', spot['selection'], '',
                  f"Assessor: {spot['assessor']}. {len(spot['checks'])} examples have individual rationales in developer-spotcheck.json. This is an unblinded development audit and must not be presented as independent or human-validated accuracy.", '']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    return summary


def write_workbench_report(path: Path, output: Path):
    result = json.loads(path.read_text(encoding='utf-8'))
    lines = ['# Workbench engine: simulated-participant benchmark', '',
             f"{result['participants_per_condition']} sessions per population and policy; seed {result['seed']}.", '',
             '| Simulated population | Policy | Tasks + repeat | Largest-factor recovery | Failed repeat | Null mismatch, all sessions | Null mismatch, passing sessions |',
             '|---|---|---:|---:|---:|---:|---:|']
    for population, policies in result['populations'].items():
        for policy, row in policies.items():
            values = [row[key] for key in ('top1_recovery', 'response_check_inconclusive_rate', 'null_mismatch_rate_all', 'null_mismatch_rate_passing')]
            formatted = [f'{value:.2%}' if value is not None else 'unavailable' for value in values]
            lines.append(f"| {population} | {policy} | {row['total_questions_including_repeat']} | " + ' | '.join(formatted) + ' |')
    lines += ['', 'All ratings in these null cohorts agree with the generating largest preference weight. A descriptive mismatch is therefore a model/measurement disagreement, not evidence that a participant failed to act on a stated value.', '',
              'Adaptive uses two fewer tasks than all-six. Small differences in top-one recovery do not establish superior accuracy. Mixed preferences may fit none of the four candidate models.', '',
              'The raw JSON includes Brier scores and threshold sensitivity. Raising the separation threshold from .45 to .90 did not reduce adaptive null mismatch in this seeded evaluation. No diagnostic threshold was tuned on these results; the app removes the behaviour-gap claim instead.', '',
              *['- ' + item for item in result['limitations']], '']
    output.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('outputs/muse-review-evaluation-v4'))
    args = parser.parse_args()
    result = build_report(args.directory, Path('outputs/muse-review-evaluation-report.md'))
    benchmark = Path('outputs/workbench-benchmark.json')
    if benchmark.exists():
        write_workbench_report(benchmark, Path('outputs/workbench-benchmark-report.md'))
    print(f"Report refreshed: {result['recorded_calls']}/108 recorded calls; {result['status']}.")


if __name__ == '__main__':
    main()
