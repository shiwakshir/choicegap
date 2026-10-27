"""Prepare and run a frozen, paired visual-confound evaluation of Muse review.

Preparation needs Pillow (development only). Live runs need MODEL_API_KEY.
Expected labels and scoring rules are never sent to the model.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import inspect
import random
import time
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .meta import MetaClient
from .research import default_blueprint, local_map, parse_evidence
from .review import validate_review, prototype_metadata
from .dynamic import audit_study, compile_study
from .config import load_env_file


KINDS = ('default', 'prominence', 'badge', 'leading_wording', 'availability', 'hidden_fee')
RULES = {
    'default': ['preselect', 'pre-select', 'default', 'selected'],
    'prominence': ['larger', 'size', 'prominen', 'emphasis'],
    'badge': ['badge', 'recommended', 'endorse'],
    'leading_wording': ['responsib', 'wording', 'moral', 'leading'],
    'availability': ['unavailable', 'disabled', 'availability', 'sold out'],
    'hidden_fee': ['service fee', 'extra fee', 'additional fee', 'total cost', 'surcharge'],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def render_case(path: Path, kind: str, side: int, index: int):
    from PIL import Image, ImageDraw, ImageFont
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    def font(size):
        return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)
    image = Image.new('RGB', (1100, 690), '#f5f4ef')
    draw = ImageDraw.Draw(image)
    draw.text((45, 28), 'Your weekly grocery delivery', fill='#17251b', font=font(30))
    draw.text((45, 78), 'Compare both options, then choose one.', fill='#334438', font=font(20))
    for position in (0, 1):
        x = 45 + position * 520
        draw.rounded_rectangle((x, 132, x + 480, 622), radius=12, fill='white', outline='#66756a', width=2)
        target = position == side
        name = 'Option A' if position == 0 else 'Option B'
        # A trades an emissions reduction for a fee; all other encoded factors match e1.
        facts = ['Environmental impact: Estimated delivery emissions 60% lower' if position == 0 else 'Environmental impact: Standard estimated delivery emissions',
                 'Delivery cost: £3 delivery fee' if position == 0 else 'Delivery cost: Free delivery',
                 'Delivery window: All-day delivery window', 'Claim verification: Retailer calculation']
        draw.text((x + 25, 159), name, fill='#17251b', font=font(26))
        for row, fact in enumerate(facts):
            for line, text in enumerate(textwrap.wrap(fact, width=46)):
                draw.text((x + 25, 218 + row * 59 + line * 23), text, fill='#25382b', font=font(18))
        if target and kind == 'badge':
            draw.rectangle((x + 195, 148, x + 455, 190), fill='#e4efb9')
            draw.text((x + 205, 158), 'RECOMMENDED', fill='#17251b', font=font(20))
        if target and kind == 'leading_wording':
            draw.text((x + 25, 450), 'The responsible choice', fill='#17251b', font=font(23))
        if target and kind == 'hidden_fee':
            draw.text((x + 25, 462), '+ £2 service fee at payment', fill='#17251b', font=font(18))
        selected = target and kind == 'default'
        draw.ellipse((x + 25, 510, x + 47, 532), outline='#17251b', width=2)
        if selected:
            draw.ellipse((x + 30, 515, x + 42, 527), fill='#17251b')
        draw.text((x + 60, 507), 'Selected' if selected else 'Select this option', fill='#17251b', font=font(18))
        big = target and kind == 'prominence'
        disabled = target and kind == 'availability'
        width = 425 if big else 300
        draw.rectangle((x + 25, 550, x + 25 + width, 605 if big else 590), fill='#a0a5a1' if disabled else '#24583a')
        draw.text((x + 40, 561), 'Unavailable' if disabled else f'Choose {name}', fill='white', font=font(22 if big else 18))
    # Neutral variation in the footer; no label reveals expected defect.
    draw.text((45, 648), f'Checkout study · screen {index + 1}', fill='#526457', font=font(16))
    image.save(path)


def prepare(root: Path):
    if (root / 'protocol.json').exists():
        raise ValueError('Protocol already exists. Use another directory to preserve the frozen evaluation.')
    root.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, kind in enumerate([*KINDS, *KINDS, *(['clean'] * 6)]):
        identifier = f'case-{index + 1:02}'
        filename = identifier + '.png'
        side = (index % 2) ^ ((index // 6) % 2)
        render_case(root / filename, kind, side, index)
        cases.append({'id': identifier, 'image': filename,
                      'image_sha256': hashlib.sha256((root / filename).read_bytes()).hexdigest(),
                      'expected': kind, 'target_side': 'A' if side == 0 else 'B'})
    payload = {
        'version': 1, 'cases': cases, 'repetitions': 3, 'conditions': ['text_only', 'with_image'],
        'order_seed': 2702026, 'rules': RULES,
        'reviewer_implementation_sha256': hashlib.sha256(inspect.getsource(MetaClient.challenge_research_design).encode()).hexdigest(),
        'decision': 'Before testing price versus estimated emissions in grocery delivery, check this e1 checkout prototype against the proposed study. Only the emissions estimate and delivery fee should differ; timing, claim verification, availability, selection state, wording and visual emphasis should be equal. Do not infer behaviour from this static prototype.',
        'sources': 'statement | interview-01 | I compare the delivery fee and estimated emissions when choosing a grocery delivery slot.',
        'blueprint': default_blueprint(),
        'scoring': 'Primary scoring is blinded human adjudication of observation AND proposed control. Automated keyword matches are an unvalidated screening proxy only. Clean-case alarm means any finding; report basis counts separately. API errors and validation failures remain in denominators. Never treat repeated calls as independent cases.',
    }
    protocol = {'sha256': digest(payload), 'payload': payload}
    (root / 'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    (root / 'status.json').write_text(json.dumps({'status': 'prepared_not_run', 'protocol_sha256': protocol['sha256'], 'planned_calls': 108}, indent=2), encoding='utf-8')
    return protocol


def load_protocol(root):
    protocol = json.loads((root / 'protocol.json').read_text(encoding='utf-8'))
    if digest(protocol['payload']) != protocol['sha256']:
        raise ValueError('Frozen protocol has changed')
    if protocol['payload'].get('reviewer_implementation_sha256') != hashlib.sha256(inspect.getsource(MetaClient.challenge_research_design).encode()).hexdigest():
        raise ValueError('Reviewer implementation changed; prepare a new protocol directory')
    for case in protocol['payload']['cases']:
        if hashlib.sha256((root / case['image']).read_bytes()).hexdigest() != case['image_sha256']:
            raise ValueError('Frozen screenshot has changed')
    return protocol


def screen_score(review, case):
    findings = review.get('findings', [])
    if case['expected'] == 'clean':
        return {'proxy_detection': None, 'clean_alarm': bool(findings)}
    terms = RULES[case['expected']]
    match = any(f['basis'] == 'prototype_image' and any(term in f['observation'].lower() for term in terms)
                and bool(f['suggested_control'].strip()) for f in findings)
    return {'proxy_detection': match, 'clean_alarm': None}


def summarize(root: Path):
    protocol = load_protocol(root)
    rows_path = root / 'calls.jsonl'
    rows = [json.loads(line) for line in rows_path.read_text(encoding='utf-8').splitlines()] if rows_path.exists() else []
    labels_path = root / 'adjudication.json'
    labels = json.loads(labels_path.read_text(encoding='utf-8')) if labels_path.exists() else {}
    result = {'status': 'not_run' if not rows else 'partial' if len(rows) < 108 else 'completed',
              'protocol_sha256': protocol['sha256'], 'planned_calls': 108, 'recorded_calls': len(rows),
              'scoring_warning': 'Keyword screening is not measured semantic reviewer accuracy. Use blind human labels for primary detection; missing labels are reported.',
              'conditions': {}}
    for condition in ('text_only', 'with_image'):
        selected = [r for r in rows if r['condition'] == condition]
        planted = [r for r in selected if r['expected'] != 'clean']
        clean = [r for r in selected if r['expected'] == 'clean']
        def label(row):
            return labels.get(hashlib.sha256(row['id'].encode()).hexdigest()[:16], {})
        adjudicated = [r for r in planted if type(label(r).get('detected')) is bool and label(r).get('rationale', '').strip()]
        clean_adjudicated = [r for r in clean if type(label(r).get('detected')) is bool and label(r).get('rationale', '').strip()]
        result['conditions'][condition] = {
            'calls': len(selected), 'planted_calls': len(planted), 'clean_calls': len(clean),
            'proxy_matches': sum(bool(r.get('score', {}).get('proxy_detection')) for r in planted),
            'primary_adjudicated_calls': len(adjudicated),
            'primary_detected_calls': sum(label(r)['detected'] for r in adjudicated),
            'primary_clean_adjudicated_calls': len(clean_adjudicated),
            'primary_clean_false_alarm_calls': sum(label(r)['detected'] for r in clean_adjudicated),
            'per_case_proxy_matches': {case: sum(bool(r.get('score', {}).get('proxy_detection')) for r in planted if r['case'] == case) for case in sorted({r['case'] for r in planted})},
            'clean_calls_with_any_finding': sum(bool(r.get('score', {}).get('clean_alarm')) for r in clean),
            'api_errors': sum(r['status'] == 'api_error' for r in selected),
            'validation_failures': sum(r['status'] == 'validation_error' for r in selected),
            'estimated_cost_usd': round(sum(r['estimated_cost_usd'] for r in selected), 6) if selected and all(r.get('estimated_cost_usd') is not None for r in selected) else None,
            'mean_latency_seconds': round(sum(r['seconds'] for r in selected) / len(selected), 3) if selected else None,
            'usage': [r['usage'] for r in selected],
        }
    # Blind packet hides expected labels and condition; static image references and
    # model findings are intentionally visible because that is the evidence to judge.
    packet = [{'id': hashlib.sha256(r['id'].encode()).hexdigest()[:16],
               'image': r['case'] + '.png', 'findings': r.get('review', {}).get('findings', []),
               'status': r['status']} for r in rows]
    random.Random(8126).shuffle(packet)
    (root / 'blind-review-packet.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')
    (root / 'adjudication-template.json').write_text(json.dumps({r['id']: {'detected': None, 'rationale': ''} for r in packet}, indent=2), encoding='utf-8')
    (root / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (root / 'status.json').write_text(json.dumps({key: result[key] for key in ('status', 'protocol_sha256', 'planned_calls', 'recorded_calls')}, indent=2), encoding='utf-8')
    return result


def run(root: Path, maximum: int = 108, input_rate: float | None = None, output_rate: float | None = None, workers: int = 3):
    protocol = load_protocol(root)
    meta = MetaClient()
    if not meta.enabled:
        raise ValueError('MODEL_API_KEY is unavailable. Prepared cases are ready; no live results have been measured.')
    payload = protocol['payload']
    sources = parse_evidence(payload['sources'])
    mapping = local_map(sources)
    workspace = {'status': 'draft', 'decision': payload['decision'], 'sources': sources}
    rows_path = root / 'calls.jsonl'
    existing = [json.loads(line) for line in rows_path.read_text(encoding='utf-8').splitlines()] if rows_path.exists() else []
    for row in existing:
        if row['protocol_sha256'] != protocol['sha256'] or row['model'] != meta.model:
            raise ValueError('Use a new run directory for a changed protocol or model')
    completed = {r['id'] for r in existing}
    schedule = [(case, condition, repeat) for case in payload['cases'] for condition in payload['conditions'] for repeat in range(3)]
    random.Random(payload['order_seed']).shuffle(schedule)
    pending = [job for job in schedule if f"{job[0]['id']}:{job[1]}:{job[2]}" not in completed][:maximum]

    def evaluate(job):
        case, condition, repeat = job
        meta = MetaClient()  # Usage belongs to this one call, including concurrent runs.
        identifier = f"{case['id']}:{condition}:{repeat}"
        image = None
        if condition == 'with_image':
            image = 'data:image/png;base64,' + base64.b64encode((root / case['image']).read_bytes()).decode()
        meta.usage.clear()
        started = time.perf_counter()
        row = {'id': identifier, 'case': case['id'], 'condition': condition, 'repeat': repeat,
               'expected': case['expected'], 'protocol_sha256': protocol['sha256'], 'model': meta.model}
        try:
            raw = meta.challenge_research_design(workspace['decision'], sources, mapping, payload['blueprint'], audit_study(compile_study(payload['blueprint'])), image)
            row['raw_response'] = raw
            reviewed = validate_review(raw, sources, image is not None)
            row.update(status='ok', review=reviewed, score=screen_score(reviewed, case))
        except ValueError as exc:
            row.update(status='validation_error', error=str(exc))
        except RuntimeError as exc:
            row.update(status='api_error', error=str(exc))
        row.update(seconds=round(time.perf_counter() - started, 3), usage=list(meta.usage),
                   prototype=prototype_metadata(image))
        usage = meta.usage[-1].get('usage', {}) if meta.usage else {}
        row['estimated_cost_usd'] = ((usage.get('prompt_tokens', 0) * input_rate + usage.get('completion_tokens', 0) * output_rate) / 1_000_000
                                     if input_rate is not None and output_rate is not None and 'prompt_tokens' in usage and 'completion_tokens' in usage else None)
        row['price_rates_per_million'] = {'input': input_rate, 'output': output_rate}
        return row

    attempted = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for offset in range(0, len(pending), workers):
            batch = list(executor.map(evaluate, pending[offset:offset + workers]))
            for row in batch:
                with rows_path.open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps(row) + '\n')
                attempted += 1
                print(f"{attempted}: {row['id']} {row['status']}", flush=True)
            if any(row['status'] == 'api_error' for row in batch):
                break  # All in-flight calls are recorded; no new batch after errors.
    return summarize(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('outputs/muse-review-evaluation'))
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--env-file', type=Path, help='Optional local KEY=value file; only MODEL_API_KEY and META_MODEL are read, never printed')
    parser.add_argument('--max-calls', type=int, default=108)
    parser.add_argument('--workers', type=int, default=3, choices=range(1, 7))
    parser.add_argument('--input-rate', type=float, help='Verified USD per million input tokens; optional')
    parser.add_argument('--output-rate', type=float, help='Verified USD per million output tokens; optional')
    args = parser.parse_args()
    if args.env_file:
        load_env_file(args.env_file, overwrite=True)
    if args.max_calls < 1:
        parser.error('--max-calls must be positive')
    if args.prepare:
        prepare(args.directory)
    if args.run:
        result = run(args.directory, args.max_calls, args.input_rate, args.output_rate, args.workers)
    else:
        result = summarize(args.directory)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
