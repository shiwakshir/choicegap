"""Muse review of semantic and visual confounds before researcher approval."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any

from .dynamic import audit_study, compile_study
from .research import design_input_digest, validate_map


def prototype_metadata(data_url: str | None) -> dict[str, Any] | None:
    if data_url is None:
        return None
    if not isinstance(data_url, str) or len(data_url) > 1_400_000:
        raise ValueError("Use a PNG or JPEG screenshot smaller than 1 MB")
    try:
        header, encoded = data_url.split(',', 1)
        if header not in ('data:image/png;base64', 'data:image/jpeg;base64'):
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > 1_000_000:
            raise ValueError()
        expected = b'\x89PNG\r\n\x1a\n' if 'png' in header else b'\xff\xd8\xff'
        if not raw.startswith(expected):
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise ValueError("Use a valid base64 PNG or JPEG screenshot smaller than 1 MB") from exc
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "mime_type": header[5:].split(';')[0]}


def validate_review(result: dict[str, Any], sources: list[dict[str, str]], has_image: bool) -> dict[str, Any]:
    if not isinstance(result, dict) or not isinstance(result.get('summary'), str) or not result['summary'].strip():
        raise ValueError("Muse review must contain a summary")
    findings = result.get('findings')
    if not isinstance(findings, list) or len(findings) > 8:
        raise ValueError("Muse review must contain at most eight findings")
    by_id = {source['id']: source for source in sources}
    for finding in findings:
        if not isinstance(finding, dict) or finding.get('account') not in ('a', 'b', 'c', 'd', 'other'):
            raise ValueError("Unknown review account")
        for field in ('observation', 'alternative_explanation', 'suggested_control'):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise ValueError(f"Review finding is missing {field}")
        basis = finding.get('basis')
        if basis not in ('source_text', 'prototype_image', 'proposed_design'):
            raise ValueError("Unknown review evidence basis")
        if basis == 'prototype_image' and not has_image:
            raise ValueError("Muse described an image that was not supplied")
        identifiers = finding.get('source_ids')
        quote = finding.get('quote')
        if not isinstance(identifiers, list) or not isinstance(quote, str):
            raise ValueError("Invalid review source references")
        if basis == 'source_text':
            if not identifiers or any(identifier not in by_id for identifier in identifiers):
                raise ValueError("Review cites an unknown source")
            if not quote.strip() or not any(quote in by_id[identifier]['text'] for identifier in identifiers):
                raise ValueError("Review quotation is absent from the cited sources")
        elif identifiers or quote:
            raise ValueError("Image and design findings must not impersonate textual source citations")
    unresolved = result.get('unresolved')
    if not isinstance(unresolved, list) or any(not isinstance(item, str) for item in unresolved):
        raise ValueError("Review unresolved questions must be text")
    return result


def review_workspace(
    workspace: dict[str, Any], blueprint: dict[str, Any], mapping: dict[str, Any],
    image: str | None, meta: Any,
) -> dict[str, Any]:
    if workspace['status'] != 'draft':
        raise ValueError("Review a draft before approval; published designs are locked")
    if not meta.enabled:
        raise ValueError("Configure MODEL_API_KEY to run the Muse design review. Manual review remains available.")
    metadata = prototype_metadata(image)
    mapping = validate_map(mapping, workspace['sources'])
    audit = audit_study(compile_study(blueprint))
    if not audit['passed']:
        raise ValueError("Correct structural design errors before requesting a semantic review")
    result = meta.challenge_research_design(workspace['decision'], workspace['sources'], mapping, blueprint, audit, image)
    result = validate_review(result, workspace['sources'], metadata is not None)
    review = {
        **result, 'source': meta.model, 'created_at': datetime.now(timezone.utc).isoformat(),
        'reviewed_input_sha256': design_input_digest(blueprint, mapping),
        'prototype': metadata,
        'scope': 'Model advisory review. Visual interpretations require human verification.',
    }
    # Persist the observations and image digest, not the image bytes.
    return {**workspace, 'blueprint': blueprint, 'mapping': mapping, 'design_review': review,
            'design_review_current': True,
            'api_usage': workspace.get('api_usage', []) + meta.usage}
