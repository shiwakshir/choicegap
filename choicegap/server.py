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

from .engine import DRIVER_COPY, DRIVERS, Session
from .meta import MetaClient


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
SESSIONS: dict[str, Session] = {}
LOCK = threading.Lock()


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
        if length > 1_000_000:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            meta = MetaClient()
            self._json(200, {"ok": True, "meta_enabled": meta.enabled, "model": meta.model if meta.enabled else None})
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
            if self.path == "/api/start":
                self._start(payload)
            elif self.path == "/api/answer":
                self._answer(payload)
            else:
                self._json(404, {"error": "Unknown endpoint"})
        except (ValueError, KeyError, StopIteration) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # keep demo usable if an optional model call fails
            self._json(500, {"error": str(exc)})

    def _start(self, payload: dict[str, Any]) -> None:
        fallback = str(payload.get("driver", ""))
        statement = str(payload.get("statement", "")).strip()[:1000]
        if fallback not in DRIVERS:
            raise ValueError("Choose one stated priority")
        meta = MetaClient()
        try:
            intake = meta.parse_statement(statement, fallback)
        except RuntimeError as exc:
            intake = {"driver": fallback, "reason": str(exc), "source": "local-fallback"}
        # Explicit UI selection wins if free text is empty; otherwise Muse may classify it.
        stated_driver = intake["driver"] if statement else fallback
        session = Session.create(stated_driver, statement)
        candidates = session.candidates()
        try:
            plan = meta.choose_experiment(candidates, session.posterior)
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
            "driver_copy": DRIVER_COPY,
            "meta_enabled": meta.enabled,
        })

    def _answer(self, payload: dict[str, Any]) -> None:
        token = str(payload["session_id"])
        choice = str(payload["choice"])
        if choice not in ("a", "b"):
            raise ValueError("Choice must be a or b")
        with LOCK:
            session = SESSIONS.get(token)
            if session is None:
                raise ValueError("Session expired")
            session.observe(str(payload["experiment_id"]), choice, bool(payload.get("flipped")))

        meta = MetaClient()
        done = session.rounds >= 4
        response: dict[str, Any] = {"posterior": session.posterior, "rounds": session.rounds, "done": done}
        if done:
            report = session.report()
            try:
                narrative = meta.narrate_report(report)
            except RuntimeError as exc:
                narrative = {"summary": report["headline"], "next_step": "Collect more observations before acting.", "source": "local-fallback", "error": str(exc)}
            response.update({"report": report, "narrative": narrative})
        else:
            candidates = session.candidates()
            try:
                plan = meta.choose_experiment(candidates, session.posterior)
            except RuntimeError as exc:
                plan = MetaClient.fallback_plan(candidates, session.posterior)
                plan.update({"reason": str(exc), "source": "local-fallback"})
            response.update({"plan": plan, "experiment": session.next_experiment(plan["experiment_id"])})
        self._json(200, response)


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


if __name__ == "__main__":
    run(port=int(os.getenv("PORT", "8000")))

