from __future__ import annotations

import json
import mimetypes
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .dynamic import DynamicSession, StudySpec, audit_study, compile_study
from .engine import DRIVER_COPY, DRIVERS, Session
from .meta import MetaClient


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
SESSIONS: dict[str, Session | DynamicSession] = {}
STUDIES: dict[str, StudySpec] = {}
COMPLETED: list[dict[str, Any]] = []
LOCK = threading.Lock()
MAX_REQUEST_BYTES = 1_000_000
ADAPTIVE_ROUNDS = 4


class Handler(BaseHTTPRequestHandler):
    server_version = "ChoiceGap/0.1"

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
        if length > MAX_REQUEST_BYTES:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            meta = MetaClient()
            self._json(200, {"ok": True, "meta_enabled": meta.enabled, "model": meta.model if meta.enabled else None})
            return
        if path == "/api/export":
            with LOCK:
                records = list(COMPLETED)
            self._json(200, {
                "schema_version": 1,
                "description": "De-identified ChoiceGap session records; no free-text statements are included.",
                "records": records,
            })
            return
        requested = "index.html" if path == "/" else path.lstrip("/")
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
        try:
            payload = self._body()
            if self.path == "/api/design":
                self._design(payload)
            elif self.path == "/api/start":
                self._start(payload)
            elif self.path == "/api/answer":
                self._answer(payload)
            else:
                self._json(404, {"error": "Unknown endpoint"})
        except (ValueError, KeyError, StopIteration) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self.log_error("Unhandled request error: %s", exc)
            self._json(500, {"error": "Internal server error"})

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
        study_id = str(payload.get("study_id", ""))
        study = STUDIES.get(study_id) if study_id else None
        valid_drivers = study.driver_ids if study else DRIVERS
        raw_ratings = payload.get("ratings") or {}
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
        if study:
            intake = {
                "driver": fallback_driver,
                "reason": "Selected from the Muse-compiled study axes.",
                "source": meta.model,
            }
            stated_driver = fallback_driver
            session = DynamicSession.create(study, stated_driver, statement, stated_ratings=ratings, intention_score=intention_score)
            driver_copy = study.driver_copy
        else:
            try:
                intake = meta.parse_statement(statement, fallback_driver)
            except RuntimeError as exc:
                intake = {
                    "driver": fallback_driver,
                    "reason": str(exc),
                    "source": "local-fallback",
                }
            # The structured ratings—not Muse's interpretation—define the stated profile.
            stated_driver = fallback_driver
            session = Session.create(stated_driver, statement, stated_ratings=ratings, intention_score=intention_score)
            driver_copy = DRIVER_COPY
        candidates = session.candidates()
        try:
            plan = meta.choose_experiment(candidates, session.posterior, driver_copy)
        except RuntimeError as exc:
            plan = MetaClient.fallback_plan(candidates, session.posterior)
            plan.update({"reason": str(exc), "source": "local-fallback"})
        experiment = session.next_experiment(plan["experiment_id"])
        token = secrets.token_urlsafe(18)
        with LOCK:
            SESSIONS[token] = session
        self._json(200, {
            "session_id": token,
            "intake": intake,
            "plan": plan,
            "experiment": experiment,
            "posterior": session.posterior,
            "driver_copy": driver_copy,
            "study_title": study.title if study else "Sustainable grocery delivery",
            "meta_enabled": meta.enabled,
        })

    def _answer(self, payload: dict[str, Any]) -> None:
        token = str(payload["session_id"])
        choice = str(payload["choice"])
        if choice not in ("a", "b", "outside"):
            raise ValueError("Choice must be a, b, or outside")
        with LOCK:
            session = SESSIONS.get(token)
            if session is None:
                raise ValueError("Session expired")
            is_holdout = bool(payload.get("holdout"))
            if is_holdout:
                session.observe_holdout(choice, bool(payload.get("flipped")))
            else:
                session.observe(str(payload["experiment_id"]), choice, bool(payload.get("flipped")))

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
            try:
                plan = meta.choose_experiment(candidates, session.posterior, driver_copy)
            except RuntimeError as exc:
                plan = MetaClient.fallback_plan(candidates, session.posterior)
                plan.update({"reason": str(exc), "source": "local-fallback"})
            response.update({"plan": plan, "experiment": session.next_experiment(plan["experiment_id"])})
        self._json(200, response)

    def _finish(self, token: str, session: Session | DynamicSession, meta: MetaClient, response: dict[str, Any]) -> None:
        report = session.report()
        try:
            narrative = meta.narrate_report(report)
        except RuntimeError as exc:
            narrative = {"summary": report["headline"], "next_step": "Collect more observations before acting.", "source": "local-fallback", "error": str(exc)}
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
        }
        with LOCK:
            COMPLETED.append(record)
            SESSIONS.pop(token, None)
        response.update({"done": True, "report": report, "narrative": narrative})


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ChoiceGap running at http://{host}:{port}")
    print("Muse Spark enabled" if MetaClient().enabled else "Local mode: set MODEL_API_KEY to enable Muse Spark")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    run(port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()

