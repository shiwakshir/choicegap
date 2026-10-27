"""Source-linked research planning and durable local workspaces."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dynamic import audit_study, compile_study


KINDS = {"statement", "observed", "hypothetical"}
AXES = (
    ("a", "Environmental impact", "Standard estimated delivery emissions", "Estimated delivery emissions 60% lower"),
    ("b", "Delivery cost", "£3 delivery fee", "Free delivery"),
    ("c", "Delivery window", "All-day delivery window", "Two-hour delivery window"),
    ("d", "Claim verification", "Retailer calculation", "Method independently verified"),
)

EXAMPLE_EVIDENCE = """statement | interview-01 | I try to choose the lower-impact delivery option, but I need to know when it will arrive.
observed | prototype-01 | In the checkout task, the participant selected the two-hour standard slot rather than an all-day lower-impact slot. Both cost £3.
statement | interview-02 | I do not trust the retailer's green delivery label without independent verification.
observed | prototype-02 | In the task, the participant chose free standard delivery rather than a £3 lower-impact slot. Verification and timing were the same.
hypothetical | survey-03 | The respondent said they would pay £3 for lower-impact delivery."""


def parse_evidence(raw: str) -> list[dict[str, str]]:
    if not isinstance(raw, str) or len(raw) > 30_000:
        raise ValueError("Evidence must be text of at most 30,000 characters")
    records = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3 or parts[0] not in KINDS or not parts[1] or not parts[2]:
            raise ValueError("Use one source per line: statement, observed, or hypothetical | source label | excerpt")
        kind, label, excerpt = parts
        records.append({"id": f"S{len(records) + 1}", "kind": kind, "label": label[:120], "text": excerpt})
    if not records or len(records) > 60:
        raise ValueError("Provide between 1 and 60 evidence excerpts")
    return records


def default_blueprint() -> dict[str, Any]:
    return {
        "title": "Sustainable grocery delivery",
        "decision_prompt": "Which delivery option would you choose for your weekly grocery shop?",
        "attributes": [
            {
                "id": key, "label": label, "low_label": low, "high_label": high,
                "hypothesis_label": label,
                "hypothesis_description": f"Differences in {label.lower()} may explain delivery choices.",
            }
            for key, label, low, high in AXES
        ],
    }


def design_input_digest(blueprint: dict[str, Any], mapping: dict[str, Any]) -> str:
    encoded = json.dumps({"blueprint": blueprint, "mapping": mapping}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def validate_map(mapping: dict[str, Any], sources: list[dict[str, str]]) -> dict[str, Any]:
    """Check source IDs and verbatim grounding; interpretation still requires human review."""
    if not isinstance(mapping, dict):
        raise ValueError("Evidence map must be an object")
    by_id = {item["id"]: item for item in sources}
    accounts = mapping.get("accounts")
    if not isinstance(accounts, list) or any(not isinstance(item, dict) for item in accounts) or [item.get("id") for item in accounts] != list("abcd"):
        raise ValueError("Evidence mapping must contain accounts a, b, c, d in order")
    for account in accounts:
        if not isinstance(account.get("explanation"), str) or not account["explanation"].strip():
            raise ValueError("Each explanation must contain text")
        refs = account.get("references")
        if not isinstance(refs, list):
            raise ValueError("References must be a list")
        for ref in refs:
            if not isinstance(ref, dict):
                raise ValueError("Each reference must be an object")
            source = by_id.get(ref.get("source_id"))
            if source is None:
                raise ValueError("Evidence map contains an unknown source ID")
            quote = ref.get("quote")
            if not isinstance(quote, str) or not quote.strip() or quote not in source["text"]:
                raise ValueError("Every quoted excerpt must occur verbatim in its cited source")
            if ref.get("relation") not in ("supports", "challenges", "context"):
                raise ValueError("Unknown evidence relationship")
            # Attach the trusted type from the source, never the model's representation.
            ref["source_kind"] = source["kind"]
        if not isinstance(account.get("missing_evidence"), str) or not account["missing_evidence"].strip():
            raise ValueError("Each account must specify missing evidence")
    if not isinstance(mapping.get("unresolved"), list) or any(not isinstance(item, str) for item in mapping["unresolved"]):
        raise ValueError("Unresolved questions must be a list")
    return mapping


def local_map(sources: list[dict[str, str]]) -> dict[str, Any]:
    # Local mode deliberately makes no automated semantic assignments.
    return {
        "accounts": [
            {"id": key, "explanation": f"{label} may constrain lower-impact delivery adoption.",
             "references": [], "missing_evidence": "Review the imported sources and add a distinguishing test."}
            for key, label, _, _ in AXES
        ],
        "unresolved": [
            "Imported sources have not been semantically mapped in local mode.",
            "Availability, access, and omitted explanations may matter.",
            "Sources are not linked to the same participant unless the researcher establishes that link.",
        ],
    }


def draft_workspace(decision: str, raw: str, meta: Any) -> dict[str, Any]:
    if not isinstance(decision, str) or not 20 <= len(decision.strip()) <= 2000:
        raise ValueError("Describe the product decision in 20–2,000 characters")
    sources = parse_evidence(raw)
    warning = ""
    if meta.enabled:
        try:
            mapping = validate_map(meta.map_research_evidence(decision, sources), sources)
            source = meta.model
        except (RuntimeError, ValueError) as exc:
            mapping = local_map(sources)
            source = "local-unmapped"
            warning = f"Automated mapping unavailable; sources are retained for manual review. {exc}"
    else:
        mapping = local_map(sources)
        source = "local-unmapped"
    return {
        "id": secrets.token_urlsafe(12), "status": "draft", "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision.strip(), "sources": sources, "mapping": mapping,
        "blueprint": default_blueprint(), "source": source, "warning": warning,
        "api_usage": list(meta.usage),
    }


def distinguishing_tests(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    """Draft separate one-factor field contrasts, not individual causal diagnoses."""
    attributes = blueprint["attributes"]
    tests = []
    for item in attributes:
        baseline = {attribute["id"]: attribute["low_label"] for attribute in attributes}
        # For non-impact contrasts, keep the focal option's lower-impact claim constant.
        if item["id"] != "a":
            baseline["a"] = attributes[0]["high_label"]
        tests.append({
            "account": item["id"], "factor": item["label"],
            "baseline": dict(baseline),
            "intervention": {**baseline, item["id"]: item["high_label"]},
            "held_constant": [other["label"] for other in attributes if other["id"] != item["id"]],
            "prediction": f"If {item['label'].lower()} matters at these levels, the intervention may change lower-impact option uptake.",
            "design": "Randomly assign eligible participants to baseline or intervention; keep presentation, availability, and other attributes fixed.",
            "outcome": "Actual selection of the focal option, with exposure denominators and environmental estimates recorded separately.",
            "limitations": "Proposed field experiment only. Review ethical and operational feasibility, interactions, randomization unit, power, and analysis before launch.",
        })
    return tests


def approve_workspace(draft: dict[str, Any], blueprint: dict[str, Any], mapping: dict[str, Any], confirmed: bool) -> dict[str, Any]:
    if confirmed is not True:
        raise ValueError("Review and approve the evidence, explanations, and exact factor levels before publishing")
    if draft["status"] != "draft":
        raise ValueError("This study is already approved. Create another draft for a different version.")
    for key, maximum in (("title", 100), ("decision_prompt", 240)):
        if not isinstance(blueprint.get(key), str) or not 1 <= len(blueprint[key].strip()) <= maximum:
            raise ValueError(f"Study {key} must contain 1–{maximum} characters")
    attributes = blueprint.get("attributes", [])
    if len(attributes) != 4 or len({item.get("label", "").strip().casefold() for item in attributes}) != 4:
        raise ValueError("Use four distinct factor names")
    study = compile_study(blueprint)
    audit = audit_study(study)
    if not audit["passed"]:
        raise ValueError("The revised study failed its structural audit")
    mapping = validate_map(mapping, draft["sources"])
    approved = {**draft, "status": "approved", "blueprint": blueprint, "mapping": mapping,
                "audit": audit, "approved_at": datetime.now(timezone.utc).isoformat(),
                "field_tests": distinguishing_tests(blueprint)}
    review = draft.get('design_review')
    approved['design_review_current'] = bool(
        review and review.get('reviewed_input_sha256') == design_input_digest(blueprint, mapping)
    )
    packet = {key: approved[key] for key in ("decision", "sources", "mapping", "blueprint", "version")}
    approved["design_sha256"] = hashlib.sha256(
        json.dumps(packet, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return approved


def decision_report(workspace: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [record for record in records if record.get("study_id") == workspace["id"]]
    usable = [record for record in eligible if record.get("evidence_quality") != "low"]
    counts = {item["id"]: 0 for item in workspace["blueprint"]["attributes"]}
    unresolved = 0
    for record in usable:
        report = record["report"]
        if report["confidence"] < .45:
            unresolved += 1
        else:
            counts[report["leading_driver"]] += 1
    return {
        "decision": workspace["decision"], "completed_sessions": len(eligible),
        "study_title": workspace["blueprint"]["title"],
        "status": workspace["status"], "version": workspace["version"],
        "approved_at": workspace.get("approved_at"),
        "blueprint": workspace["blueprint"], "audit": workspace.get("audit"),
        "mapping_source": workspace["source"],
        "design_review": workspace.get('design_review'),
        "design_review_current": bool(
            workspace.get('design_review') and workspace['design_review'].get('reviewed_input_sha256')
            == design_input_digest(workspace['blueprint'], workspace['mapping'])
        ),
        "evidence_origin": workspace.get("evidence_origin", "researcher-supplied-unverified"),
        "response_checks_passed": len(usable), "inconclusive_response_checks": len(eligible) - len(usable),
        "weak_model_separation": unresolved,
        "session_leader_counts": counts,
        "next_step": (
            "Collect approved choice-task responses before prioritizing a field experiment."
            if not usable else
            "Review the session evidence and contradictory cases, then select one of the proposed field contrasts."
        ),
        "limitations": [
            "Leader counts describe these sessions under the candidate models; they are not population prevalence or causal effects.",
            "Repeated sessions are not verified as unique participants.",
            "The 0.45 model-separation threshold is an uncalibrated prototype heuristic.",
            "Imported source material and new hypothetical choices are different evidence types.",
            "Field experiments are proposals and have not been run by this application.",
        ],
        "field_tests": workspace.get("field_tests", []),
        "field_test_basis": "Generic single-factor templates, not result-derived recommendations.",
        "account_evidence": [
            {"account": account["id"], "explanation": account["explanation"],
             "source_references": account["references"], "missing_evidence": account["missing_evidence"],
             "sessions_led": counts[account["id"]],
             "baseline_level": next(a["low_label"] for a in workspace["blueprint"]["attributes"] if a["id"] == account["id"]),
             "alternative_level": next(a["high_label"] for a in workspace["blueprint"]["attributes"] if a["id"] == account["id"]),
             "interpretation": "Source interpretations and new hypothetical sessions are shown together for review; they are not matched participants or a causal confirmation."}
            for account in workspace["mapping"]["accounts"]
        ],
        "sources": workspace["sources"], "mapping": workspace["mapping"],
        "design_sha256": workspace.get("design_sha256"),
        "session_cases": [
            {"case": index + 1, "response_quality": record.get("evidence_quality"),
             "leading_account": record["report"]["leading_driver"],
             "model_probability": record["report"]["confidence"],
             "stated_priorities": record.get("stated_priorities", []),
             "outside_choices": record.get("opt_out_count", 0),
             "holdout_consistent": record.get("holdout_consistent")}
            for index, record in enumerate(eligible)
        ],
    }


class ResearchStore:
    """JSON documents in SQLite; each approved design is immutable."""

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        connection.execute("CREATE TABLE IF NOT EXISTS documents (kind TEXT, id TEXT, payload TEXT, PRIMARY KEY(kind,id))")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def put(self, kind: str, identifier: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute("SELECT payload FROM documents WHERE kind=? AND id=?", (kind, identifier)).fetchone()
            if previous and kind == "workspace" and json.loads(previous[0]).get("status") == "approved":
                raise ValueError("Approved designs are immutable")
            connection.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?)", (kind, identifier, json.dumps(payload)))

    def get(self, kind: str, identifier: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM documents WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise ValueError("Research workspace unavailable")
        return json.loads(row[0])

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM documents WHERE kind=? ORDER BY rowid", (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]
