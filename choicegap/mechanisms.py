"""Behavioural hypotheses, locked randomized protocols and aggregate contrasts.

These experiments measure responses to prototype manipulations, not mental traits.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import secrets
from datetime import datetime, timezone


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


CATALOG = {
    'default': {
        'id': 'default', 'label': 'Default effects', 'domain': 'Automatic motivation / choice context',
        'hypothesis': 'Preselection changes the final choice even when the option attributes stay the same.',
        'rivals': ['A preselection may imply a recommendation.', 'Changing a selection takes effort.', 'A reference point may change the comparison.'],
        'design': 'Randomly assign one participant session to lower-emissions preselected, standard preselected, or no preselection. Options and confirm action stay identical.',
        'falsification': 'A precise near-zero difference between the two preselection arms would weaken the operational default-effect account at these levels.',
        'boundary': 'A default effect does not identify effort, endorsement or reference dependence separately. A participant must confirm the selection; this is not passive real-world enrolment.',
        'sources': [{'title': 'Dinner et al. (2011), Partitioning Default Effects (with correction)', 'url': 'https://doi.org/10.1037/a0024354'},
                    {'title': 'Fowlie et al., randomized electricity pricing defaults', 'url': 'https://www.nber.org/papers/w23553'}],
    },
    'planning': {
        'id': 'planning', 'label': 'Advance planning information', 'domain': 'Opportunity / information timing',
        'hypothesis': 'Earlier arrival-time information increases selection of the lower-emissions option by reducing planning uncertainty.',
        'rivals': ['Earlier information may have rational scheduling value.', 'Receipt constraints or work commitments may dominate.', 'The information promise may change perceived service quality.'],
        'design': 'Randomly vary when the exact arrival time for the focal option becomes known. Its actual two-hour window, fee, emissions and evidence stay the same.',
        'falsification': 'A precise near-zero uptake difference would weaken this information-timing account in the stated scenario.',
        'boundary': 'This tests information timing, not a pure ambiguity-aversion trait, delivery speed or present bias. Practical scheduling value remains a rival mechanism.',
        'sources': [{'title': 'Michie et al. (2011), COM-B and the Behaviour Change Wheel', 'url': 'https://doi.org/10.1186/1748-5908-6-42'},
                    {'title': 'Ellsberg (1961), uncertainty distinctions; conceptual boundary, not a replication', 'url': 'https://doi.org/10.2307/1884324'}],
    },
    'credibility': {
        'id': 'credibility', 'label': 'Claim credibility versus general endorsement', 'domain': 'Reflective motivation / evidence evaluation',
        'hypothesis': 'Independent verification strengthens response to an emissions benefit, beyond any general endorsement effect.',
        'rivals': ['Verification may act as a general endorsement.', 'Numerical emissions differences may be misunderstood.', 'Attention or perceived service quality could explain an interaction.'],
        'design': 'A between-session 2×2 design crosses an emissions benefit (0.4 versus 1.0 kg CO₂e) with retailer-only versus independent verification for the focal option. The comparator, price and window stay fixed.',
        'falsification': 'A precise near-zero interaction, or the same verification effect with and without an emissions benefit, would weaken the benefit-specific credibility account.',
        'boundary': 'An interaction is consistent with credibility moderating a claim; it does not prove the psychological mediator. Belief measures and real choices are still needed.',
        'sources': [{'title': 'Hovland & Weiss (1951), Source Credibility and Communication Effectiveness', 'url': 'https://doi.org/10.1086/266350'}],
    },
}


def protocol(mechanism_id):
    if mechanism_id not in CATALOG:
        raise ValueError('Choose a supported behavioural mechanism')
    spec = copy.deepcopy(CATALOG[mechanism_id])
    def arm(identifier, label, benefit=True, verified=True, information='Exact arrival time confirmed when you book.', default=None):
        focal = {'emissions': 'Estimated delivery emissions: 0.4 kg CO₂e' if benefit else 'Estimated delivery emissions: 1.0 kg CO₂e',
                 'fee': 'Delivery fee: £3', 'window': 'Delivery window: 18:00–20:00',
                 'verification': 'Emissions calculation independently verified.' if verified else 'Emissions calculation supplied by retailer.',
                 'information': information}
        comparator = {'emissions': 'Estimated delivery emissions: 1.0 kg CO₂e', 'fee': 'Delivery fee: £3' if mechanism_id == 'credibility' else 'Delivery fee: £0',
                      'window': 'Delivery window: 18:00–20:00',
                      'verification': 'Emissions calculation independently verified.' if mechanism_id != 'credibility' else 'Emissions calculation supplied by retailer.',
                      'information': 'Exact arrival time confirmed when you book.'}
        return {'id': identifier, 'label': label, 'a': focal, 'b': comparator, 'default': default}
    if mechanism_id == 'default':
        spec['arms'] = [arm('focal_default', 'Lower-emissions option preselected', default='a'),
                        arm('standard_default', 'Standard option preselected', default='b'),
                        arm('active', 'Neither option preselected')]
        spec['contrast'] = {'label': 'Preselecting the focal rather than standard option',
                            'weights': {'focal_default': 1, 'standard_default': -1}}
        spec['changed_fields'] = ['default']
    elif mechanism_id == 'planning':
        spec['arms'] = [arm('advance', 'Exact time known at booking'),
                        arm('later', 'Exact time known on delivery morning', information='Exact arrival time confirmed on the morning of delivery.')]
        spec['contrast'] = {'label': 'Advance rather than later arrival-time information', 'weights': {'advance': 1, 'later': -1}}
        spec['changed_fields'] = ['a.information']
    else:
        spec['arms'] = [arm('benefit_verified', 'Emissions benefit · independently verified'),
                        arm('benefit_retailer', 'Emissions benefit · retailer calculation', verified=False),
                        arm('equal_verified', 'Equal emissions · independently verified', benefit=False),
                        arm('equal_retailer', 'Equal emissions · retailer calculation', benefit=False, verified=False)]
        spec['contrast'] = {'label': 'Benefit-by-verification interaction (difference of differences)',
                            'weights': {'benefit_verified': 1, 'benefit_retailer': -1, 'equal_verified': -1, 'equal_retailer': 1}}
        spec['changed_fields'] = ['a.emissions', 'a.verification']
    spec.update(version=1, question='Which delivery option would you choose for your weekly grocery shop?',
                context='Imagine booking one week before delivery. Both options cover the same grocery basket and address. All displayed estimates and service details are hypothetical.',
                outcome='Confirmed choice of canonical focal option A; neither is a separate response, counted as not choosing A.',
                assignment='Equal-probability random assignment between participant sessions; random left/right order. One choice per session.',
                status='hypothesis_not_established', analysis='One prespecified aggregate contrast; no individual mechanism classification.')
    spec['audit'] = audit_protocol(spec)
    return spec


def audit_protocol(spec):
    """Check exact encoded changes, including the four factorial cells."""
    base = spec['arms'][0]
    differences = set()
    for item in spec['arms'][1:]:
        for side in ('a', 'b'):
            for key in base[side]:
                if item[side][key] != base[side][key]:
                    differences.add(f'{side}.{key}')
        if item['default'] != base['default']:
            differences.add('default')
    checks = {'only_declared_fields_change': differences == set(spec['changed_fields']),
              'comparator_fixed': all(a['b'] == base['b'] for a in spec['arms']),
              'unique_arm_ids': len({a['id'] for a in spec['arms']}) == len(spec['arms']),
              'no_price_or_window_change': all(a['a']['fee'] == base['a']['fee'] and a['a']['window'] == base['a']['window'] for a in spec['arms'])}
    if spec['id'] == 'credibility':
        checks['complete_factorial'] = len({(a['a']['emissions'], a['a']['verification']) for a in spec['arms']}) == 4
    return {'passed': all(checks.values()), 'checks': checks}


def manual_plan(workspace):
    return {'workspace_id': workspace['id'], 'source': 'manual-unmapped',
            'accounts': [{'id': key, 'explanation': item['hypothesis'], 'references': [],
                          'missing_evidence': 'Review source material and the rival accounts before selecting this test.'}
                         for key, item in CATALOG.items()],
            'unresolved': ['Capability, affordability and access constraints may matter; do not assume all barriers are psychological.']}


def validate_plan(plan, workspace):
    from .research import validate_references
    if not isinstance(plan, dict) or not isinstance(plan.get('accounts'), list) or any(not isinstance(a, dict) for a in plan['accounts']):
        raise ValueError('Provide a behavioural explanation plan')
    if [a.get('id') for a in plan['accounts']] != list(CATALOG):
        raise ValueError('Mechanism accounts must match the supported catalogue')
    for account in plan['accounts']:
        for field in ('explanation', 'missing_evidence'):
            if not isinstance(account.get(field), str) or not account[field].strip() or len(account[field]) > 2000:
                raise ValueError('Each mechanism needs a bounded explanation and missing-evidence note')
        account['references'] = validate_references(account.get('references'), workspace['sources'])
    if not isinstance(plan.get('unresolved'), list) or any(not isinstance(s, str) for s in plan['unresolved']):
        raise ValueError('Unresolved questions must be text')
    return plan


def make_plan(workspace, meta):
    if not meta.enabled:
        return manual_plan(workspace)
    from .research import design_input_digest
    review = workspace.get('design_review')
    context = review if review and review.get('reviewed_input_sha256') == design_input_digest(workspace['blueprint'], workspace['mapping']) else None
    result = validate_plan(meta.propose_mechanisms(workspace['decision'], workspace['sources'], list(CATALOG.values()), context), workspace)
    return {**result, 'workspace_id': workspace['id'], 'source': meta.model, 'api_usage': list(meta.usage),
            'advisory_review_context': context}


def approve_study(workspace, plan, mechanism_id, confirmed):
    if confirmed is not True:
        raise ValueError('Review the hypotheses, rivals, exact arms and analysis, then confirm approval')
    plan = validate_plan(copy.deepcopy(plan), workspace)
    spec = protocol(mechanism_id)
    if not spec['audit']['passed']:
        raise ValueError('Mechanism protocol failed its structural audit')
    selected = next(a for a in plan['accounts'] if a['id'] == mechanism_id)
    packet = {'id': secrets.token_urlsafe(12), 'status': 'approved', 'workspace_id': workspace['id'],
              'created_at': datetime.now(timezone.utc).isoformat(), 'protocol': spec, 'account': selected,
              'decision': workspace['decision'], 'sources': workspace['sources'], 'unresolved': plan['unresolved'],
              'planning_source': plan.get('source', 'researcher-edited'), 'evidence_origin': workspace.get('evidence_origin', 'researcher-supplied-unverified')}
    packet['advisory_review_context'] = plan.get('advisory_review_context')
    packet['design_sha256'] = digest(packet)
    return packet


def assignment(study, arm_id=None, flipped=None):
    if study.get('status') != 'approved' or not study['protocol']['audit']['passed']:
        raise ValueError('Use an approved mechanism study')
    # Explicit arm/orientation are for deterministic simulations; HTTP never accepts them.
    arm = next(a for a in study['protocol']['arms'] if a['id'] == arm_id) if arm_id else secrets.choice(study['protocol']['arms'])
    flipped = bool(secrets.randbelow(2)) if flipped is None else flipped
    default = arm['default']
    displayed_default = ('b' if default == 'a' else 'a') if flipped and default else default
    stimulus = {'question': study['protocol']['question'], 'context': study['protocol']['context'],
                'a': list(arm['b' if flipped else 'a'].values()), 'b': list(arm['a' if flipped else 'b'].values()),
                'default': displayed_default}
    return {'id': secrets.token_urlsafe(18), 'answer_token': secrets.token_urlsafe(24),
            'study_id': study['id'], 'design_sha256': study['design_sha256'], 'arm_id': arm['id'],
            'flipped': flipped, 'stimulus': stimulus, 'stimulus_sha256': digest(stimulus),
            'status': 'pending', 'created_at': datetime.now(timezone.utc).isoformat()}


def contrast(arms, weights, alpha=.05):
    """Fixed-time conservative bound from Hoeffding + union bound across cells."""
    if any(not arms[key]['completed'] for key in weights):
        return {'estimate': None, 'lower': None, 'upper': None, 'status': 'Missing responses in at least one required arm'}
    estimate = low = high = 0.0
    for key, weight in weights.items():
        cell = arms[key]
        p = cell['a'] / cell['completed']
        radius = math.sqrt(math.log(2 * len(weights) / alpha) / (2 * cell['completed']))
        lo, hi = max(0, p - radius), min(1, p + radius)
        estimate += weight * p
        low += weight * (lo if weight > 0 else hi)
        high += weight * (hi if weight > 0 else lo)
    return {'estimate': estimate, 'lower': low, 'upper': high,
            'status': 'Imprecise: range includes zero' if low <= 0 <= high else 'Range excludes zero under stated assumptions',
            'method': 'Fixed-time 95% conservative Hoeffding/union bound for one prespecified contrast, assuming independent Bernoulli session outcomes; not adjusted for repeated peeking or multiple studies.'}


def report(study, records):
    cells = {a['id']: {'label': a['label'], 'assigned': 0, 'completed': 0, 'a': 0, 'b': 0, 'outside': 0} for a in study['protocol']['arms']}
    for row in records:
        if row.get('study_id') != study['id']:
            continue
        cell = cells[row['arm_id']]
        cell['assigned'] += 1
        if row.get('status') == 'completed':
            cell['completed'] += 1
            cell[row['choice']] += 1
    for cell in cells.values():
        cell['missing'] = cell['assigned'] - cell['completed']
        cell['focal_share_completed'] = cell['a'] / cell['completed'] if cell['completed'] else None
    estimate = contrast(cells, study['protocol']['contrast']['weights'])
    if estimate['estimate'] is None:
        why = 'No contrast can be estimated until each required arm has responses.'
    elif estimate['lower'] <= 0 <= estimate['upper']:
        why = 'The uncertainty range includes no effect. These responses do not yet distinguish the operational account from its rivals.'
    elif estimate['lower'] > 0:
        why = 'The observed pattern is compatible with the prespecified operational account under the analysis assumptions. It does not identify a unique psychological mechanism; the listed rivals remain.'
    else:
        why = 'The contrast runs against the prespecified direction under the analysis assumptions. Revisit the account and its rivals; do not assign a psychological label to participants.'
    return {'study': study, 'arms': cells, 'contrast': estimate,
            'response_records': [{key: row.get(key) for key in ('id', 'study_id', 'arm_id', 'flipped', 'stimulus', 'stimulus_sha256', 'design_sha256', 'status', 'choice', 'displayed_choice', 'created_at', 'completed_at')}
                                 for row in records if row.get('study_id') == study['id']],
            'evidence_status': 'Randomized hypothetical prototype responses; no individual psychological diagnosis.',
            'why_summary': why,
            'limitations': [study['protocol']['boundary'],
                           'Single respondents do not establish a mechanism. Repeated sessions are not verified as unique people.',
                           'Dropout can differ by arm; completed-response shares can be selection-biased. Missing answers are not coded as rejection.',
                           'The contrast is conditional on these hypothetical options, not actual uptake or environmental savings.',
                           'Preregister sample size, exclusions and analysis timing before recruiting. Repeated inspection is not sequentially valid inference.']}
