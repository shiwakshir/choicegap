from __future__ import annotations

import json
import hashlib
import math
import mimetypes
import os
import secrets
import threading
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from .dynamic import DynamicSession, StudySpec, audit_study, compile_study
from .engine import DRIVER_COPY, DRIVERS, Session
from .meta import MetaClient
from .research import (
    ResearchStore, EXAMPLE_EVIDENCE, draft_workspace, approve_workspace, decision_report, prepared_delivery_study,
)
from .review import review_workspace
from .config import load_env_file
from . import mechanisms, explore, studio, studio_capabilities as capabilities


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
if not STATIC.is_dir():
    STATIC = Path(sys.prefix) / "share" / "choicegap" / "static"
SESSIONS: dict[str, Session | DynamicSession] = {}
STUDIES: dict[str, StudySpec] = {}
COMPLETED: list[dict[str, Any]] = []
PENDING: dict[str, dict[str, Any]] = {}
TRACES: dict[str, list[dict[str, Any]]] = {}
USAGE: dict[str, list[dict[str, Any]]] = {}
SESSION_STUDIES: dict[str, str] = {}
EXPERIENCES: dict[str, int] = {}
LOCK = threading.Lock()
MAX_REQUEST_BYTES = 2_000_000
ADAPTIVE_ROUNDS = 4
STORE = ResearchStore(Path(os.getenv("CHOICEGAP_DATA_DIR", str(Path.cwd() / "work" / "choicegap-data"))) / "research.sqlite3")


def load_study(study_id: str) -> StudySpec | None:
    if study_id in STUDIES:
        return STUDIES[study_id]
    try:
        workspace = STORE.get("workspace", study_id)
        if workspace["status"] != "approved":
            return None
        study = compile_study(workspace["blueprint"])
    except ValueError:
        try:
            study = compile_study(STORE.get("study", study_id))
        except ValueError:
            return None
    with LOCK:
        STUDIES[study_id] = study
    return study


def issue_experiment(
    token: str, experiment: dict[str, Any], plan: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> str:
    answer_token = secrets.token_urlsafe(18)
    candidate = next((item for item in candidates if item["id"] == experiment["id"]), {})
    encoded = json.dumps(experiment, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with LOCK:
        PENDING[token] = {
            "answer_token": answer_token,
            "experiment": experiment,
            "plan": plan,
            "predictions": candidate.get("predictions", {}),
            "stimulus_sha256": hashlib.sha256(encoded).hexdigest(),
        }
    return answer_token


def consume_answer(token: str, payload: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Validate the issued question and consume its nonce before updating any evidence."""
    choice = payload.get("choice")
    if choice not in ("a", "b", "outside"):
        raise ValueError("Choice must be a, b, or outside")
    with LOCK:
        session = SESSIONS.get(token)
        pending = PENDING.get(token)
        if session is None:
            raise ValueError("Session expired")
        if pending is None:
            raise ValueError("A response is already being processed")
        if payload.get("answer_token") != pending["answer_token"]:
            raise ValueError("This question has already been answered or is out of date")
        experiment = pending["experiment"]
        if payload.get("experiment_id") != experiment["id"]:
            raise ValueError("Response does not match the issued experiment")
        PENDING.pop(token)
        before = dict(session.posterior)
        if experiment.get("holdout"):
            session.observe_holdout(choice, experiment["flipped"])
        else:
            session.observe(experiment["id"], choice, experiment["flipped"])
        entropy = lambda p: -sum(value * math.log2(value) for value in p.values() if value)
        TRACES.setdefault(token, []).append({
            "step": len(TRACES.get(token, [])) + 1,
            "holdout": bool(experiment.get("holdout")),
            "plan_before_response": pending["plan"],
            "stimulus": experiment,
            "stimulus_sha256": pending["stimulus_sha256"],
            "p_canonical_a_by_hypothesis": pending["predictions"],
            "displayed_choice": choice,
            "posterior_before": before,
            "posterior_after": dict(session.posterior),
            "uncertainty_before_bits": round(entropy(before), 4),
            "uncertainty_after_bits": round(entropy(session.posterior), 4),
        })
        return session, experiment


class Handler(BaseHTTPRequestHandler):
    server_version = "ChoiceGap/0.1"

    def _local_request(self, write=False):
        """Keep this unauthenticated prototype confined to its own local origin."""
        port = self.server.server_port
        allowed = {f'{host}:{port}' for host in ('localhost', '127.0.0.1')}
        if port == 80:
            allowed.update(('localhost', '127.0.0.1'))
        host = self.headers.get('Host', '').lower()
        origin = self.headers.get('Origin')
        if (host not in allowed or
                (origin is not None and origin != f'http://{host}') or
                (write and self.headers.get('Sec-Fetch-Site') == 'cross-site')):
            self._json(403, {'error': 'This local prototype only accepts requests from its own local address.'})
            return False
        if write and self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            self._json(415, {'error': 'Send an application/json request.'})
            return False
        return True

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[choicegap] {format % args}")

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        limit = (16_100_000 if self.path == '/api/studio/inspect-clip' else
                 4_100_000 if self.path == '/api/studio/transcribe' else MAX_REQUEST_BYTES)
        if length < 0 or length > limit:
            raise ValueError("Request too large")
        payload = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        if not self._local_request():
            return
        path = urlparse(self.path).path
        if path.startswith('/api/studio/'):
            try:
                self._studio_get(path, parse_qs(urlparse(self.path).query))
            except ValueError as exc:
                self._json(404, {'error': str(exc)})
            return
        if path.startswith('/api/mechanisms/'):
            try:
                self._mechanism_get(path, parse_qs(urlparse(self.path).query))
            except ValueError as exc:
                self._json(404, {'error': str(exc)})
            return
        if path.startswith("/api/research/"):
            try:
                query = parse_qs(urlparse(self.path).query)
                identifier = query.get("id", [""])[0]
                if path == "/api/research/example":
                    self._json(200, {"evidence": EXAMPLE_EVIDENCE, "decision": "Which change should we test to improve lower-impact grocery-delivery adoption: cost, timing, or claim verification?"})
                elif path == "/api/research/workspaces":
                    self._json(200, {"workspaces": [
                        {key: workspace.get(key) for key in ("id", "decision", "status", "created_at", "evidence_origin")}
                        for workspace in STORE.list("workspace")
                    ]})
                elif path == "/api/research/workspace":
                    self._json(200, STORE.get("workspace", identifier))
                elif path == "/api/research/report":
                    workspace = STORE.get("workspace", identifier)
                    report = decision_report(workspace, STORE.list("session"))
                    report['ux_research']['collection_progress'] = explore.collection_progress(STORE.list('exploration'), workspace['id'])
                    self._json(200, report)
                else:
                    self._json(404, {"error": "Unknown research endpoint"})
            except ValueError as exc:
                self._json(404, {"error": str(exc)})
            return
        if path == "/api/health":
            meta = MetaClient()
            self._json(200, {"ok": True, "meta_enabled": meta.enabled, "model": meta.model if meta.enabled else None})
            return
        if path == "/api/export":
            with LOCK:
                records = list(COMPLETED)
            self._json(200, {
                "schema_version": 2,
                "description": "ChoiceGap session records. Integrated interviews include participant free text and corrections; review for identifying information before sharing.",
                "records": records,
            })
            return
        if path == "/api/study":
            study_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            study = load_study(study_id)
            if study is None:
                self._json(404, {"error": "Study unavailable or not yet approved."})
            else:
                try:
                    experience_version = STORE.get('workspace', study_id)['blueprint'].get('experience_version', 0)
                    enhanced = experience_version in (1, 2)
                except ValueError:
                    enhanced = False
                self._json(200, {"study_id": study_id, "study": study.to_public(), 'experience_enabled': enhanced, 'experience_version': experience_version if enhanced else 0})
            return
        requested = "index.html" if path == "/" else path.lstrip("/")
        if path == '/' and not any(k in parse_qs(urlparse(self.path).query) for k in ('study', 'mechanism', 'workspace')):
            requested = 'studio.html'
        target = (STATIC / requested).resolve()
        if STATIC.resolve() not in target.parents and target != STATIC.resolve():
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if not self._local_request(write=True):
            return
        try:
            payload = self._body()
            if self.path.startswith('/api/studio/'):
                self._studio_post(self.path, payload)
            elif self.path.startswith('/api/mechanisms/'):
                self._mechanism_post(self.path, payload)
            elif self.path == "/api/design":
                self._design(payload)
            elif self.path == '/api/research/prepared-delivery':
                workspace = prepared_delivery_study()
                STORE.put('workspace', workspace['id'], workspace)
                self._json(200, workspace)
            elif self.path == "/api/research/draft":
                meta = MetaClient()
                workspace = draft_workspace(payload.get("decision", ""), payload.get("evidence", ""), meta)
                workspace["evidence_origin"] = (
                    "fictional-example" if payload.get("example") is True else "researcher-supplied-unverified"
                )
                STORE.put("workspace", workspace["id"], workspace)
                self._json(200, workspace)
            elif self.path == "/api/research/approve":
                draft = STORE.get("workspace", str(payload.get("id", "")))
                workspace = approve_workspace(
                    draft, payload["blueprint"], payload["mapping"], payload.get("confirmed"),
                )
                STORE.put("workspace", workspace["id"], workspace)
                with LOCK:
                    STUDIES[workspace["id"]] = compile_study(workspace["blueprint"])
                self._json(200, workspace)
            elif self.path == "/api/research/review":
                draft = STORE.get("workspace", str(payload.get("id", "")))
                workspace = review_workspace(
                    draft, payload['blueprint'], payload['mapping'], payload.get('prototype_image'), MetaClient(),
                )
                STORE.put('workspace', workspace['id'], workspace)
                self._json(200, workspace)
            elif self.path == "/api/start":
                self._start(payload)
            elif self.path == "/api/answer":
                self._answer(payload)
            elif self.path in ('/api/explore', '/api/explore/resume'):
                self._explore(payload, resume=self.path.endswith('/resume'))
            else:
                self._json(404, {"error": "Unknown endpoint"})
        except RuntimeError:
            self._json(502, {'error': 'Muse is unavailable right now. Your saved study is safe; please try again.'})
        except (ValueError, KeyError, StopIteration) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self.log_error("Unhandled request error: %s", exc)
            self._json(500, {"error": "Internal server error"})

    def _studio_get(self, path, query):
        identifier = query.get('id', [''])[0]
        if path == '/api/studio/capabilities':
            from . import voice_stream
            self._json(200, {'meta_enabled': MetaClient().enabled, 'streaming_voice': voice_stream.available(),
                'avatar_3d': True, 'liveavatar_configured': False})
        elif path == '/api/studio/studies':
            self._json(200, {'studies': [{'id': s['id'], 'title': s['design']['title'], 'status': s['status'],
                'created_at': s['created_at']} for s in STORE.list('studio_study')]})
        elif path == '/api/studio/study':
            self._json(200, STORE.get('studio_study', identifier))
        elif path == '/api/studio/participant':
            study = STORE.get('studio_study', identifier)
            if study['status'] != 'approved':
                raise ValueError('This study has not been published')
            self._json(200, {'id': study['id'], 'title': study['design']['title'],
                'intro': study['design']['participant_intro'], 'method': study['method'],
                'recording': study['recording'],
                'recording_seconds': study['policy'].get('recording_seconds', 30),
                'spoken_moderator': study['recording'] and study['method'] != 'survey' and study['policy'].get('spoken_moderator') is True,
                'streaming_voice': study['recording'] and study['policy'].get('streaming_voice') is True,
                'avatar': study.get('avatar', 'none'), 'task_recording': study['policy'].get('task_recording') is True,
                'base_questions':
                (len(study['design']['questions']) if study['method'] != 'interview' else 0) +
                (len(study['design']['interview_questions']) if study['method'] != 'survey' else 0) +
                int(bool(study.get('task_prompt') and study['policy'].get('task_recording'))) +
                (3 if study.get('comparisons') else 0) + 1})
        elif path == '/api/studio/results':
            study = STORE.get('studio_study', identifier)
            sessions = [s for s in STORE.list('studio_session') if s['study_id'] == identifier]
            reports = [r for r in STORE.list('studio_report') if r['study_id'] == identifier]
            self._json(200, {'completed': sum(s['status'] == 'completed' for s in sessions),
                'started': len(sessions), 'reports': reports[-1:], 'sessions':
                [{'id': f'Participant {i+1}', 'status': s['status'], 'responses': studio.evidence(s),
                  'decisions': s['decisions']} for i, s in enumerate(sessions)]})
        else:
            raise ValueError('Unknown studio endpoint')

    def _studio_post(self, path, payload):
        meta = MetaClient()
        if path == '/api/studio/background':
            result = capabilities.background(payload.get('brief'), meta)
            STORE.put('studio_background', result['id'], result)
            self._json(200, result)
        elif path == '/api/studio/concept':
            result = capabilities.concept(payload.get('prompt'), payload.get('reference', ''), meta)
            STORE.put('studio_concept', result['id'], result)
            self._json(200, result)
        elif path == '/api/studio/comparisons':
            result = capabilities.draft_comparisons(studio.design(payload.get('design')), meta)
            self._json(200, result)
        elif path == '/api/studio/generate':
            payload.pop('_reviewed_background', None)
            if payload.get('background_id'):
                background = STORE.get('studio_background', str(payload['background_id']))
                if payload.get('background_reviewed') is not True or background['brief_digest'] != capabilities.digest(str(payload.get('brief', ''))):
                    raise ValueError('Review background research for this exact brief before using it')
                payload['_reviewed_background'] = background
            draft = studio.generate(payload, meta)
            if payload.get('concept_id'):
                concept = STORE.get('studio_concept', str(payload['concept_id']))
                if concept['image'] != draft['stimulus']['image']:
                    raise ValueError('The selected concept does not match the attached image')
                draft['stimulus_provenance'] = {k: v for k, v in concept.items() if k != 'image'}
            STORE.put('studio_study', draft['id'], draft)
            self._json(200, draft)
        elif path == '/api/studio/save':
            draft = STORE.get('studio_study', str(payload.get('id', '')))
            if draft['status'] != 'draft':
                raise ValueError('Published studies are fixed. Create a new draft to change the questions.')
            draft['design'] = studio.design(payload.get('design'))
            method = payload.get('method', draft.get('method', 'combined'))
            if method not in ('survey', 'interview', 'combined'):
                raise ValueError('Choose a supported study format')
            draft['method'] = method
            draft['recording'] = payload.get('recording', draft.get('recording', False)) is True
            draft['comparisons'] = capabilities.validate_comparisons(payload.get('comparisons', draft.get('comparisons')))
            draft['task_prompt'] = studio.text(payload.get('task_prompt', draft.get('task_prompt', '')), 1200, 'Task instructions', True)
            draft['avatar'] = payload.get('avatar', draft.get('avatar', 'none'))
            draft['voice_keywords'] = studio.strings(payload.get('voice_keywords', draft.get('voice_keywords', [])), 8, 'Voice vocabulary hints')
            STORE.put('studio_study', draft['id'], draft)
            self._json(200, draft)
        elif path == '/api/studio/approve':
            draft = STORE.get('studio_study', str(payload.get('id', '')))
            study = studio.approve(draft, payload)
            if study['avatar'] == 'liveavatar':
                raise ValueError('Use the included 3D moderator. External realistic video is not enabled in this build.')
            STORE.put('studio_study', study['id'], study)
            self._json(200, study)
        elif path == '/api/studio/start':
            study = STORE.get('studio_study', str(payload.get('study_id', '')))
            state = studio.start(study, payload.get('consent'))
            STORE.put('studio_session', state['id'], state)
            self._json(200, studio.public_session(state, study))
        elif path in ('/api/studio/answer', '/api/studio/resume', '/api/studio/transcribe',
                      '/api/studio/inspect-clip', '/api/studio/voice-ticket'):
            state = STORE.get('studio_session', str(payload.get('id', '')))
            study = STORE.get('studio_study', state['study_id'])
            if path.endswith('/answer'):
                if state['status'] == 'active' and state['queue'][state['index']]['type'] == 'task' and payload.get('skip') is not True:
                    review_id = (payload.get('answer') or {}).get('review_id', '') if isinstance(payload.get('answer'), dict) else ''
                    review = STORE.get('studio_clip_review', str(review_id))
                    payload['answer'] = capabilities.task_answer(payload['answer'], review, state)
                    payload['input_mode'] = 'task_review'
                updated = studio.answer(study, state, payload, meta)
                STORE.save_studio_session(updated, state['nonce'])
                state = updated
            elif path.endswith('/transcribe'):
                self._json(200, studio.transcribe(payload, study, state, meta))
                return
            elif path.endswith('/inspect-clip'):
                review = capabilities.inspect_clip(payload, study, state, meta)
                STORE.put('studio_clip_review', review['id'], review)
                self._json(200, review)
                return
            elif path.endswith('/voice-ticket'):
                from . import voice_stream
                result = voice_stream.ticket(study, state, payload.get('nonce'), STORE)
                self._json(200, result)
                return
            self._json(200, studio.public_session(state, study))
        elif path == '/api/studio/analyse':
            study = STORE.get('studio_study', str(payload.get('id', '')))
            result = studio.report(study, STORE.list('studio_session'), meta)
            STORE.put('studio_report', result['id'], result)
            self._json(200, result)
        else:
            raise ValueError('Unknown studio endpoint')

    def _mechanism_get(self, path, query):
        identifier = query.get('id', [''])[0]
        if path == '/api/mechanisms/catalog':
            self._json(200, {'mechanisms': [mechanisms.protocol(key) for key in mechanisms.CATALOG],
                             'deferred': 'Present bias is not inferred here: it needs a separate credible timing/incentive design.'})
        elif path == '/api/mechanisms/plan':
            workspace = STORE.get('workspace', identifier)
            try:
                plan = STORE.get('mechanism_plan', identifier)
            except ValueError:
                plan = mechanisms.manual_plan(workspace)
            self._json(200, plan)
        elif path == '/api/mechanisms/studies':
            studies = sorted((s for s in STORE.list('mechanism_study') if s['workspace_id'] == identifier), key=lambda s: (s['created_at'], s['id']))
            self._json(200, {'studies': [{'id': s['id'], 'label': s['protocol']['label'], 'workspace_id': s['workspace_id'], 'created_at': s['created_at']} for s in studies]})
        elif path == '/api/mechanisms/participant':
            study = STORE.get('mechanism_study', identifier)
            self._json(200, {'question': study['protocol']['question'], 'context': study['protocol']['context'],
                             'notice': 'One hypothetical choice; no purchase or real delivery will be made. Responses are stored locally.'})
        elif path == '/api/mechanisms/report':
            study = STORE.get('mechanism_study', identifier)
            self._json(200, mechanisms.report(study, STORE.list('mechanism_assignment')))
        else:
            raise ValueError('Unknown behavioural research endpoint')

    def _mechanism_post(self, path, payload):
        if path == '/api/mechanisms/plan':
            workspace = STORE.get('workspace', str(payload.get('workspace_id', '')))
            plan = mechanisms.make_plan(workspace, MetaClient())
            STORE.put('mechanism_plan', workspace['id'], plan)
            self._json(200, plan)
        elif path == '/api/mechanisms/approve':
            workspace = STORE.get('workspace', str(payload.get('workspace_id', '')))
            try:
                origin = STORE.get('mechanism_plan', workspace['id'])
            except ValueError:
                origin = mechanisms.manual_plan(workspace)
            plan = payload.get('plan', origin)
            plan['source'] = origin['source']
            plan['advisory_review_context'] = origin.get('advisory_review_context')
            study = mechanisms.approve_study(workspace, plan, str(payload.get('mechanism_id', '')), payload.get('confirmed'))
            STORE.put('mechanism_study', study['id'], study)
            self._json(200, study)
        elif path == '/api/mechanisms/start':
            if payload.get('consent') is not True:
                raise ValueError('Acknowledge the hypothetical study before starting')
            study = STORE.get('mechanism_study', str(payload.get('study_id', '')))
            assigned = mechanisms.assignment(study)
            STORE.put('mechanism_assignment', assigned['id'], assigned)
            self._json(200, {key: assigned[key] for key in ('id', 'answer_token', 'stimulus', 'stimulus_sha256')})
        elif path == '/api/mechanisms/answer':
            STORE.answer_mechanism(str(payload.get('id', '')), payload.get('answer_token'), payload.get('choice'))
            self._json(200, {'done': True, 'message': 'Thank you. Your choice has been recorded.'})
        else:
            raise ValueError('Unknown behavioural research endpoint')

    def _design(self, payload: dict[str, Any]) -> None:
        context = str(payload.get("context", "")).strip()
        if len(context) < 30:
            raise ValueError("Describe the decision and what you want to learn in at least 30 characters")
        meta = MetaClient()
        blueprint = meta.design_study(context)
        study = compile_study(blueprint)
        audit = audit_study(study)
        if not audit["passed"]:
            raise ValueError("The generated study did not pass the controlled-design audit")
        token = secrets.token_urlsafe(12)
        STORE.put("study", token, blueprint)
        with LOCK:
            STUDIES[token] = study
        self._json(200, {
            "study_id": token,
            "study": study.to_public(),
            "audit": audit,
            "source": blueprint.get("source", meta.model),
        })

    def _start(self, payload: dict[str, Any]) -> None:
        fallback_driver = str(payload.get("driver", ""))
        statement = str(payload.get("statement", "")).strip()[:1000]
        study_id = str(payload.get("study_id") or "")
        study = load_study(study_id) if study_id else None
        if study_id and study is None:
            raise ValueError("Study unavailable. Ask the researcher for a new study link.")
        enhanced = payload.get('experience_enabled') is True
        experience_version = explore.VERSION
        if enhanced:
            if payload.get('interview_consent') is not True:
                raise ValueError('Please review the interview and data-sharing notice before continuing')
            if study_id:
                workspace = STORE.get('workspace', study_id)
                experience_version = workspace['blueprint'].get('experience_version', 0)
                if experience_version not in (1, 2):
                    raise ValueError('This study was not approved for adaptive interviews')
                if workspace['blueprint'].get('experience_policy') != explore.policy(experience_version):
                    raise ValueError('The approved follow-up protocol differs from this version. Ask the researcher for a newly approved study.')
        valid_drivers = study.driver_ids if study else DRIVERS
        raw_ratings = payload.get("ratings") or {}
        if not isinstance(raw_ratings, dict):
            raise ValueError("Ratings must be an object")
        if raw_ratings:
            ratings = {key: int(raw_ratings.get(key, 0)) for key in valid_drivers}
            if any(value < 1 or value > 5 for value in ratings.values()):
                raise ValueError("Rate every factor from 1 to 5")
            fallback_driver = max(
                valid_drivers,
                key=lambda key: (ratings[key], -valid_drivers.index(key)),
            )
        else:
            if fallback_driver not in valid_drivers:
                raise ValueError("Rate the factors before starting")
            ratings = {key: (5 if key == fallback_driver else 3) for key in valid_drivers}
        intention_score = int(payload.get("intention_score", 3))
        if intention_score < 1 or intention_score > 5:
            raise ValueError("Intention rating must be from 1 to 5")
        meta = MetaClient()
        intake = {"driver": fallback_driver, "reason": "Structured importance ratings; free text retained without automated interpretation.", "source": "structured-ratings"}
        if study:
            stated_driver = fallback_driver
            session = DynamicSession.create(study, stated_driver, statement, stated_ratings=ratings, intention_score=intention_score)
            driver_copy = study.driver_copy
        else:
            # The structured ratings—not Muse's interpretation—define the stated profile.
            stated_driver = fallback_driver
            session = Session.create(stated_driver, statement, stated_ratings=ratings, intention_score=intention_score)
            driver_copy = DRIVER_COPY
        candidates = session.candidates()
        plan = MetaClient.fallback_plan(candidates, session.posterior)
        experiment = session.next_experiment(plan["experiment_id"])
        token = secrets.token_urlsafe(18)
        with LOCK:
            SESSIONS[token] = session
            TRACES[token] = []
            USAGE[token] = list(meta.usage)
            SESSION_STUDIES[token] = study_id
            if enhanced:
                EXPERIENCES[token] = experience_version
        answer_token = issue_experiment(token, experiment, plan, candidates)
        self._json(200, {
            "session_id": token,
            "intake": intake,
            "plan": plan,
            "experiment": experiment,
            "posterior": session.posterior,
            "driver_copy": driver_copy,
            "study_title": study.title if study else "Sustainable grocery delivery",
            "meta_enabled": meta.enabled,
            "answer_token": answer_token,
        })

    def _answer(self, payload: dict[str, Any]) -> None:
        token = str(payload["session_id"])
        session, issued = consume_answer(token, payload)
        is_holdout = bool(issued.get("holdout"))

        meta = MetaClient()
        response: dict[str, Any] = {"posterior": session.posterior, "rounds": session.rounds, "done": False}
        if is_holdout:
            self._finish(token, session, meta, response)
        elif session.rounds >= ADAPTIVE_ROUNDS:
            holdout = session.holdout_experiment()
            if holdout:
                response.update({
                    "holdout": True,
                    "experiment": holdout,
                    "plan": {
                        "reason": "A repeated choice with reversed sides checks response consistency.",
                        "source": "quality-check",
                        "leading_account": max(session.posterior, key=session.posterior.get),
                        "rival_account": sorted(session.posterior, key=session.posterior.get, reverse=True)[1],
                        "falsification_rule": "This response is not used to update the posterior.",
                    },
                })
            else:
                self._finish(token, session, meta, response)
        else:
            candidates = session.candidates()
            driver_copy = session.study.driver_copy if isinstance(session, DynamicSession) else DRIVER_COPY
            plan = MetaClient.fallback_plan(candidates, session.posterior)
            response.update({"plan": plan, "experiment": session.next_experiment(plan["experiment_id"])})
        if not response["done"] and not response.get('interview'):
            next_candidates = session.candidates() if not response.get("holdout") else []
            response["answer_token"] = issue_experiment(
                token, response["experiment"], response["plan"], next_candidates,
            )
        with LOCK:
            if token in USAGE:
                USAGE[token].extend(meta.usage)
        self._json(200, response)

    def _finish(self, token: str, session: Session | DynamicSession, meta: MetaClient, response: dict[str, Any]) -> None:
        report = session.report()
        report["decision_trace"] = TRACES.get(token, [])
        report["driver_labels"] = (
            session.study.driver_copy if isinstance(session, DynamicSession) else DRIVER_COPY
        )
        narrative = {"summary": report["headline"], "next_step": "Review exact tested levels and contradictory cases before designing a field experiment.", "source": "computed-report"}
        record = {
            "study_title": report.get("study_title", "Sustainable grocery delivery"),
            "stated_ratings": report.get("stated_ratings", {}),
            "intention_score": report.get("intention_score"),
            "choices": report.get("evidence", []),
            "posterior": report["posterior"],
            "opt_out_count": report.get("opt_out_count", 0),
            "holdout_consistent": report.get("holdout_consistent"),
            "informative_choices": report.get("informative_choices"),
            "evidence_quality": report.get("evidence_quality"),
            "study_id": SESSION_STUDIES.get(token, ""),
            "stated_priorities": report["stated_priorities"],
            "decision_trace": report["decision_trace"],
            "driver_labels": report["driver_labels"],
            "api_usage": USAGE.get(token, []) + meta.usage,
            "report": report,
            "narrative": narrative,
        }
        enhanced = token in EXPERIENCES
        if enhanced:
            state = explore.begin(session, report, EXPERIENCES[token])
            state['record'] = record
            STORE.put('exploration', token, state)
        else:
            STORE.put("session", token, record)
        with LOCK:
            if not enhanced:
                COMPLETED.append(record)
            EXPERIENCES.pop(token, None)
            SESSIONS.pop(token, None)
            PENDING.pop(token, None)
            TRACES.pop(token, None)
            USAGE.pop(token, None)
            SESSION_STUDIES.pop(token, None)
        if enhanced:
            response.update(done=False, interview=explore.public_step(state))
        else:
            response.update({"done": True, "report": report, "narrative": narrative})

    def _explore(self, payload, resume=False):
        token = str(payload.get('session_id', ''))
        with explore.lock_for(token):
            state = STORE.get('exploration', token)
            if state['phase'] == 'complete':
                if not resume:
                    raise ValueError('This study is complete')
                record = state['record']
                self._json(200, {'done': True, 'report': record['report'], 'narrative': record['narrative']})
                return
            if resume:
                self._json(200, {'done': False, 'interview': explore.public_step(state)})
                return
            old_token = state['pending']['answer_token']
            explore.advance(state, payload, MetaClient())
            record = None
            if state['phase'] == 'complete':
                record = state['record']
                record['report']['ux_analysis'] = explore.synthesis(state)
                comparable = [c for c in state['contrasts'] if c['response'] and c['response']['switched'] is not None]
                switches = sum(c['response']['switched'] for c in comparable)
                record['report']['headline'] = 'Which details mattered in this study?'
                record['narrative']['summary'] = f'{switches} of {len(comparable)} comparable single-detail follow-ups coincided with a different selected option. Review the exact conditions and the participant explanation below; these are descriptive study responses.'
                record['api_usage'] += state['api_usage']
                record['narrative']['next_step'] = 'Review participant corrections, both single-detail comparisons and rival explanations before deciding what to test in the field.'
            STORE.save_exploration(token, old_token, state, record)
            if record:
                with LOCK:
                    COMPLETED.append(record)
                self._json(200, {'done': True, 'report': record['report'], 'narrative': record['narrative']})
            else:
                self._json(200, {'done': False, 'interview': explore.public_step(state)})


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    with LOCK:
        COMPLETED[:] = STORE.list("session")
    server = ThreadingHTTPServer((host, port), Handler)
    from . import voice_stream
    bridge = voice_stream.start(port)
    print(f"ChoiceGap running at http://{host}:{port}")
    print("Muse Spark enabled" if MetaClient().enabled else "Local mode: set MODEL_API_KEY to enable Muse Spark")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if bridge:
            bridge.stop()
        server.server_close()


def main() -> None:
    if Path('.env').is_file():
        load_env_file(Path('.env'))
    run(port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()

