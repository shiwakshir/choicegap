"""Frozen neutral-instruction evaluation on new visual features, separate from v4."""
from __future__ import annotations

import argparse
import base64
import hashlib
import inspect
import json
import random
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import load_env_file
from .dynamic import compile_study, audit_study
from .meta import MetaClient
from .research import default_blueprint, local_map, parse_evidence
from .review import validate_review
from .review_prompts import REVIEW_PROMPTS

FEATURES = ('scarcity', 'social_proof', 'anchor', 'low_contrast', 'leaf', 'fact_order')
RULES = {
    'scarcity': ['slots left', 'scarcity', 'limited'], 'social_proof': ['most customers', 'social proof', 'popular'],
    'anchor': ['anchor', 'struck', 'crossed', 'was £8'], 'low_contrast': ['contrast', 'faint', 'readability', 'pale'],
    'leaf': ['leaf', 'leaves', 'green icon', 'plant'], 'fact_order': ['order', 'sequence', 'ordering'],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def render(path, kind, side, index):
    from PIL import Image, ImageDraw, ImageFont
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    def font(size):
        return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)
    image = Image.new('RGB', (1100, 690), '#f5f4ef')
    draw = ImageDraw.Draw(image)
    draw.text((45, 28), 'Your weekly grocery delivery', fill='#17251b', font=font(30))
    draw.text((45, 78), 'Compare both options, then choose one.', fill='#334438', font=font(20))
    study = compile_study(default_blueprint())
    for position in (0, 1):
        x, y = 45 + position * 520, 132
        target = side == position
        clean = kind.startswith('clean')
        variant = index - 12
        if clean and variant == 3 and target:
            y += 6
        radius = 0 if clean and variant == 0 and target else 12
        draw.rounded_rectangle((x, y, x + 480, y + 490), radius=radius, fill='white', outline='#66756a', width=2)
        title_x = x + (155 if clean and variant == 1 else 25)
        draw.text((title_x, y + 27), f'Option {"A" if position == 0 else "B"}', fill='#17251b', font=font(26))
        facts = list(study.experiments[0].a['facts'] if position == 0 else study.experiments[0].b['facts'])
        if kind == 'fact_order' and target:
            facts = facts[1:] + facts[:1]
        for row, fact in enumerate(facts):
            color = '#dedede' if kind == 'low_contrast' and target and fact.startswith('Environmental') else '#25382b'
            for line, text in enumerate(textwrap.wrap(fact, width=46)):
                draw.text((x + 25, y + 86 + row * 59 + line * 23), text, fill=color, font=font(18))
            if clean and variant == 2:
                draw.line((x + 25, y + 138 + row * 59, x + 455, y + 138 + row * 59), fill='#eeeeee')
        if target and kind in ('scarcity', 'social_proof'):
            draw.text((x + 25, y + 320), 'Only 2 slots left' if kind == 'scarcity' else 'Most customers choose this', fill='#25382b', font=font(21))
        if target and kind == 'anchor':
            draw.text((x + 25, y + 176), 'Was £8', fill='#25382b', font=font(19))
            draw.line((x + 23, y + 187, x + 90, y + 187), fill='#25382b', width=2)
        if target and kind == 'leaf':
            draw.ellipse((x + 365, y + 25, x + 435, y + 58), fill='#2f803c')
            draw.line((x + 360, y + 64, x + 428, y + 31), fill='#163d20', width=3)
        if clean and variant == 4:
            draw.text((x + 25, y + 330), 'Review these details before choosing.', fill='#526457', font=font(16))
        draw.ellipse((x + 25, y + 378, x + 47, y + 400), outline='#17251b', width=2)
        draw.text((x + 60, y + 375), 'Select this option', fill='#17251b', font=font(18))
        button_x = x + (90 if clean and variant == 5 else 25)
        draw.rectangle((button_x, y + 418, button_x + 300, y + 458), fill='#24583a')
        draw.text((button_x + 15, y + 429), f'Choose Option {"A" if position == 0 else "B"}', fill='white', font=font(18))
    draw.text((45, 654), f'Checkout study · screen {index + 1}', fill='#526457', font=font(16))
    image.save(path)


def signature():
    return digest({'prompts': REVIEW_PROMPTS, 'method': inspect.getsource(MetaClient.review_stage)})


def prepare(root):
    if (root / 'protocol.json').exists():
        raise ValueError('Use a new directory; never overwrite a frozen protocol')
    root.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, kind in enumerate([*FEATURES, *FEATURES, *[f'clean-{n}' for n in range(6)]]):
        name = f'neutral-{index + 1:02}'
        side = index % 2 ^ (index // 6 % 2)
        render(root / f'{name}.png', kind, side, index)
        cases.append({'id': name, 'feature': kind, 'side': 'A' if side == 0 else 'B',
                      'image_sha256': hashlib.sha256((root / f'{name}.png').read_bytes()).hexdigest()})
    payload = {'cases': cases, 'repetitions': 3, 'seed': 281026, 'reviewer_sha256': signature(), 'rules': RULES,
               'decision': 'What should we investigate before using this checkout study to understand weekly grocery delivery choices?',
               'sources': 'statement | interview-01 | I compare delivery costs and estimated emissions when choosing a grocery delivery slot.',
               'blueprint': default_blueprint(),
               'scoring': 'Fixed keyword screening of visual observations only, not semantic accuracy. Correct side and adequate controls require separate adjudication. Intended-neutral clean differences are not empirically proven harmless.',
               'scope': 'New feature families and neutral instructions; development holdout after v4. One template, two sides per feature, six varied intended-neutral controls. No untouched external validation.'}
    packet = {'sha256': digest(payload), 'payload': payload}
    (root / 'protocol.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')


def load(root):
    packet = json.loads((root / 'protocol.json').read_text())
    if digest(packet['payload']) != packet['sha256'] or packet['payload']['reviewer_sha256'] != signature():
        raise ValueError('Protocol or reviewer changed')
    for case in packet['payload']['cases']:
        if hashlib.sha256((root / f"{case['id']}.png").read_bytes()).hexdigest() != case['image_sha256']:
            raise ValueError('Frozen screenshot changed')
    return packet


def summarize(root):
    packet = load(root)
    path = root / 'calls.jsonl'
    rows = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    screen = [r for r in rows if r['stage'] == 'screen']
    planted = [r for r in screen if not r['feature'].startswith('clean')]
    clean = [r for r in screen if r['feature'].startswith('clean')]
    summary = {'status': 'completed' if len(rows) == 57 else 'partial' if rows else 'not_run',
               'protocol_sha256': packet['sha256'], 'calls': len(rows), 'planned_calls': 57,
               'screen_calls': len(screen), 'planted_calls': len(planted), 'clean_calls': len(clean),
               'planted_calls_with_visual_findings': sum(any(f['basis'] == 'prototype_image' for f in r.get('result', {}).get('findings', [])) for r in planted),
               'fixed_rule_matches': sum(bool(r.get('screen_match')) for r in planted),
               'clean_calls_with_any_findings': sum(bool(r.get('result', {}).get('findings')) for r in clean),
               'api_errors': sum(r['status'] == 'api_error' for r in rows),
               'validation_errors': sum(r['status'] == 'validation_error' for r in rows),
               'design_runs': [{'run': r['repeat'] + 1, 'status': r['status'], 'findings': len(r.get('result', {}).get('findings', []))} for r in rows if r['stage'] == 'design'],
               'limitations': [packet['payload']['scope'], packet['payload']['scoring'],
                              'Any finding is not automatically a true detection or false alarm. Topic/run frequency is not confidence. Primary independent adjudication is absent.']}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def write_report(root, output=Path('outputs/neutral-review-report.md')):
    summary = summarize(root)
    path = root / 'calls.jsonl'
    rows = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    cost = 0.0
    for row in rows:
        for entry in row.get('usage', []):
            usage = entry.get('usage', {})
            cached = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
            cost += ((usage.get('prompt_tokens', 0) - cached) * 1.25 + cached * .15 + usage.get('completion_tokens', 0) * 4.25) / 1_000_000
    lines = ['# Neutral-instruction review evaluation', '',
             f"Status: **{summary['status']}**, {summary['calls']}/{summary['planned_calls']} recorded calls.", '',
             'Three independent text-only design runs and three visual runs for each of eighteen new screens. Six new feature types, each with side reversed, plus six varied intended-neutral layouts. Neither the decision text nor visual prompt names the feature checklist.', '',
             f"API errors: {summary['api_errors']}. Validation errors: {summary['validation_errors']}.", '',
             '| New feature | Calls | Calls returning visual findings | Fixed keyword matches |', '|---|---:|---:|---:|']
    for kind in FEATURES:
        selected = [r for r in rows if r['feature'] == kind]
        visual = sum(any(f['basis'] == 'prototype_image' for f in r.get('result', {}).get('findings', [])) for r in selected)
        lines.append(f"| {kind} | {len(selected)} | {visual} | {sum(bool(r.get('screen_match')) for r in selected)} |")
    lines += ['', f"Intended-neutral controls: {summary['clean_calls_with_any_findings']}/{summary['clean_calls']} calls returned findings.", '',
              'This is not an adjudicated false-alarm rate. The shared base study still permits legitimate design caveats, and the neutrality of small layout differences has not been empirically established. A visual finding is not automatically correct detection. Keyword matches do not verify side or adequacy of a proposed control.', '',
              '## Independent design runs', '']
    for row in rows:
        if row['stage'] == 'design':
            lines += [f"### Run {row['repeat'] + 1}: {row['status']}", '', row.get('result', {}).get('summary', row.get('error', '')), '']
    lines += ['The application preserves all three design critiques alongside the separate visual review. Broad topic frequency is consistency, not confidence or identical semantic findings. Errors are visible and not counted as successful reviews.', '',
              '## Cost and scope', '',
              (f"Estimated cost from recorded returned tokens: ${cost:.4f}, using Standard Muse Spark rates published and checked 27 October 2026 ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)); not an invoice. No estimate for missing usage or interrupted requests."
               if all(r['model'] == 'muse-spark-1.3' for r in rows) else 'Cost is not estimated for this model; consult its published rates.'), '',
              *['- ' + item for item in summary['limitations']],
              '- Synthetic footer screen numbers are identifiers, not evidence of actual prior task exposure. Any model inference about unseen earlier screens needs correction.',
              '- v4 remains a conformance-oriented development test. This new-family test is held out from that earlier prompt development, but remains one synthetic template and is not independent external validation.', '']
    output.write_text('\n'.join(lines), encoding='utf-8')
    return summary


def run(root, maximum=57, workers=6):
    packet = load(root)
    payload = packet['payload']
    client = MetaClient()
    if not client.enabled:
        raise ValueError('Configure the local Meta key before running')
    path = root / 'calls.jsonl'
    rows = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    if any(r['protocol_sha256'] != packet['sha256'] or r['model'] != client.model for r in rows):
        raise ValueError('Use a new directory for changed model/protocol')
    done = {r['id'] for r in rows}
    jobs = [('design', None, i) for i in range(3)] + [('screen', c, i) for c in payload['cases'] for i in range(3)]
    random.Random(payload['seed']).shuffle(jobs)
    sources = parse_evidence(payload['sources'])
    mapping = local_map(sources)
    audit = audit_study(compile_study(payload['blueprint']))
    def identifier(job):
        stage, case, repeat = job
        return f"{stage}:{case['id'] if case else 'independent-design'}:{repeat}"
    jobs = [j for j in jobs if identifier(j) not in done][:maximum]
    def call(job):
        stage, case, repeat = job
        meta = MetaClient()
        image = ('data:image/png;base64,' + base64.b64encode((root / f"{case['id']}.png").read_bytes()).decode()) if case else None
        row = {'id': identifier(job), 'stage': stage, 'repeat': repeat, 'feature': case['feature'] if case else None,
               'side': case['side'] if case else None, 'model': meta.model, 'protocol_sha256': packet['sha256']}
        start = time.perf_counter()
        try:
            raw = meta.review_stage(payload['decision'], sources, mapping, payload['blueprint'], audit, stage, image)
            row['raw_response'] = raw
            result = validate_review(raw, sources, bool(image))
            row.update(status='ok', result=result)
            terms = RULES.get(case['feature'], []) if case else []
            row['screen_match'] = any(f['basis'] == 'prototype_image' and any(t in f['observation'].lower() for t in terms) for f in result['findings'])
        except RuntimeError as exc:
            row.update(status='api_error', error=str(exc))
        except ValueError as exc:
            row.update(status='validation_error', error=str(exc))
        row.update(seconds=round(time.perf_counter() - start, 3), usage=meta.usage)
        return row
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for offset in range(0, len(jobs), workers):
            batch = list(executor.map(call, jobs[offset:offset + workers]))
            with path.open('a', encoding='utf-8') as handle:
                for row in batch:
                    handle.write(json.dumps(row) + '\n')
                    print(f"{row['id']} {row['status']}", flush=True)
            if any(row['status'] == 'api_error' for row in batch):
                break
    return summarize(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('outputs/neutral-review-evaluation'))
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--max-calls', type=int, default=57)
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error('--max-calls must be positive')
    if args.env_file:
        load_env_file(args.env_file, overwrite=True)
    if args.prepare:
        prepare(args.directory)
    if args.run:
        run(args.directory, args.max_calls)
    print(json.dumps(write_report(args.directory), indent=2))


if __name__ == '__main__':
    main()
