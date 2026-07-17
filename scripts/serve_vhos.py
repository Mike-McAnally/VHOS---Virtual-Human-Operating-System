"""serve_vhos.py — the running instance as an OpenAI-compatible model.

ADR-006: chat interfaces stay outside VHOS. This serving layer
presents the simulant on the protocol every chat front-end already
speaks, so Open WebUI (or any OpenAI-compatible client) becomes a
viewer over the instance without VHOS containing any UI code:

    GET  /v1/models             -> one model id, e.g. "alan-turing-vhos"
    POST /v1/chat/completions   -> one conversational turn (SSE or JSON)

The persona, soma, appraisal, and Tier-2 parameters are applied
SERVER-SIDE on every turn, exactly as in chat_turing.py — a client
cannot forget the system prompt, override the temperature, or bypass
disclosure. Client-supplied system messages and sampling parameters
are ignored by design: the body decides the temperature, not the UI.

    python3 scripts/serve_vhos.py                      # LM Studio upstream
    python3 scripts/serve_vhos.py --adapter mock       # engine-free dry run
    python3 scripts/serve_vhos.py --bind 0.0.0.0       # reachable on the LAN

Then point the client at http://<this-machine>:8765/v1 (any API key).
In Open WebUI: Admin Settings -> Connections -> OpenAI API ->
add connection with that base URL.

One served instance is ONE CONTINUOUS BODY. A client starting a new
chat rotates the session archive but does not reset the soma — a new
conversation is a visitor returning, not a new subject. Restart the
server for a fresh body. Sessions archive per Contract 1/Appendix C
(autosaved every turn) regardless of what the client stores.

Spec: VHOS v4.0 — RUNTIME interface separation (rev. 2026-07-17),
Tier 1/2 coupling (Part I), run manifest (Contract 3). ADR-001:
stdlib only. ADR-005: OpenAI-compatible upstream. ADR-006: this file.
"""

import argparse
import datetime
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vhos.vocabulary import Vocabulary                                # noqa: E402
from vhos.soma import SomaEngine, appraise                            # noqa: E402
from vhos.soma.render import (render_interoception,                  # noqa: E402
                              generation_params, length_hint)
from vhos.affect import read_soma, apply_tuning                       # noqa: E402
from vhos.runtime import assemble_system_prompt                       # noqa: E402
from vhos.runtime.loader import (load_compiled,                       # noqa: E402
                                 soma_params_from_fingerprint)
from vhos.substrate.contract import GenParams                         # noqa: E402
from demo_loop import make_adapter                                    # noqa: E402
from chat_turing import (Session, appraise_message,                   # noqa: E402
                         MESSAGE_MAGNITUDE, sha12)

DEFAULT_SUBJECT = os.path.join(ROOT, "subjects", "alan_turing")


class VhosService:
    """The continuous instance behind the endpoint: one body, one
    engine adapter, a rotating session archive. All turn processing is
    serialized under a lock — one body speaks to one visitor at a
    time (ADR-006 leaves multi-visitor semantics explicitly open)."""

    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.adapter = make_adapter(args.adapter, model=args.model,
                                    host=args.upstream)
        self.statements, self.fingerprint = load_compiled(args.subject)
        self.vocab = Vocabulary()
        self.params = soma_params_from_fingerprint(self.fingerprint)
        self.engine = SomaEngine(params=self.params,
                                 seed=args.seed if args.seed is not None
                                 else 42)
        self.base = GenParams(seed=args.seed, max_tokens=None)
        self.model_id = args.model_id or (
            re.sub(r"[^a-z0-9]+", "-", args.name.lower()).strip("-")
            + "-vhos")
        self.last_t = time.monotonic()
        self.sess = self._new_session()

    def _new_session(self):
        s = Session(self.args.subject, self.args.name, self.args.you,
                    self.args.adapter)
        s.seed = self.args.seed
        return s

    def _rotate_session(self):
        if self.sess.turns:
            try:
                self.sess.save("", self.engine.state, self.base)
                print("  session archived -> %s"
                      % os.path.relpath(self.sess.dir, ROOT))
            except OSError as e:
                print("  ! session save failed: %s" % e)
        self.sess = self._new_session()

    # ------------------------------------------------------------------
    def turn(self, messages):
        """One conversational turn from an OpenAI-style message list.
        Returns (reply_text, meta dict)."""
        users = [m for m in messages
                 if m.get("role") == "user" and (m.get("content") or "").strip()]
        if not users:
            raise ValueError("no user message in request")
        user = users[-1]["content"].strip()

        with self.lock:
            # a fresh client conversation rotates the archive; the body
            # persists (ADR-006: a new chat is a visitor returning)
            if len(users) <= 1 and self.sess.turns:
                self._rotate_session()

            # the body lives through the silence between requests
            now = time.monotonic()
            elapsed = min(now - self.last_t, 600.0)
            self.last_t = now
            if elapsed >= 1.0:
                self.engine.run(int(elapsed))

            # the visitor's words land as events
            tags = appraise_message(user)
            if tags:
                self.engine.step(impulses=appraise(tags, MESSAGE_MAGNITUDE))
                self.engine.run(6)
            state = self.engine.state

            # construct the current state (general -> personal)
            coarse = read_soma(state, self.params)
            ctx = set(tags) | set(re.findall(r"[a-z']+", user.lower()))
            affect = apply_tuning(coarse, self.fingerprint, self.vocab,
                                  context_tags=sorted(ctx))
            intero = render_interoception(state, self.params)
            hint = length_hint(state, self.params)
            if hint:
                intero = intero + " " + hint
            affect.interoception = intero
            gen = generation_params(state, self.params, base=self.base)

            persona = assemble_system_prompt(self.args.name, self.statements,
                                             affect_state=affect,
                                             interoception=intero)
            persona_sha = sha12(persona)
            self.sess.personas.setdefault(persona_sha, persona)

            # prompt window from the CLIENT's history (their record of
            # this conversation), newest last; client system messages
            # are ignored — the persona is server-side or nowhere
            window = [m for m in messages if m.get("role") in
                      ("user", "assistant")][-(self.args.window * 2):]
            convo = "".join(
                "%s: %s\n" % (self.args.you if m["role"] == "user"
                              else self.args.name,
                              (m.get("content") or "").strip())
                for m in window[:-1])
            prompt = (
                ("Conversation so far:\n%s\n" % convo if convo else "")
                + "%s: %s\n\n" % (self.args.you, user)
                + "Reply as %s — one conversational turn, first person, "
                  "no speaker label." % self.args.name)

            self.sess.add_turn(self.args.you, user)
            reply = self.adapter.generate(prompt=prompt, corpus=None,
                                          persona=persona, affect=affect,
                                          params=gen)
            reply = (reply or "").strip()
            meta = getattr(self.adapter, "last_result", None) or {}
            if reply.lower().startswith(self.args.name.lower() + ":"):
                reply = reply[len(self.args.name) + 1:].strip()
            if not reply:
                reply = ("[no visible reply — finish_reason=%s; the "
                         "engine may have spent the window on hidden "
                         "reasoning]" % (meta.get("finish_reason")
                                         or "unknown"))

            soma_line = "· soma " + "  ".join(
                "%s=%.2f" % (k, v) for k, v in state.values.items()) + (
                "  |  temp=%.2f top_p=%.2f" % (gen.temperature, gen.top_p))
            if self.args.show_soma:
                reply = reply + "\n\n*" + soma_line + "*"

            self.sess.add_turn(self.args.name, reply,
                               params={"temperature": round(gen.temperature, 3),
                                       "top_p": round(gen.top_p, 3),
                                       "max_tokens": gen.max_tokens},
                               persona_sha=persona_sha)
            self.sess.add_trace(state, gen)
            self.sess.engine_id = (getattr(self.adapter, "model", None)
                                   or self.args.adapter)
            try:
                self.sess.save(persona_sha, state, self.base)
            except OSError:
                pass

            stamp = datetime.datetime.now().strftime("%H:%M:%S")
            print("  [%s] turn %d · %s" % (stamp,
                  sum(1 for t in self.sess.turns
                      if t["who"] == self.args.you), soma_line))
            return reply, meta


# ----------------------------------------------------------------------
def make_handler(service):

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # quiet the default per-request stderr logging
        def log_message(self, fmt, *a):
            pass

        def _headers(self, code=200, ctype="application/json", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers",
                             "Authorization, Content-Type")
            for k, v in (extra or {}).items():
                self.send_header(k, v)

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode("utf-8")
            self._headers(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._headers(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if self.path.rstrip("/") in ("/v1/models", "/models"):
                self._json({"object": "list", "data": [{
                    "id": service.model_id, "object": "model",
                    "created": 0, "owned_by": "vhos"}]})
            elif self.path.rstrip("/") in ("", "/", "/health"):
                self._json({"status": "ok", "model": service.model_id,
                            "note": "VHOS serving layer (ADR-006); "
                                    "modeled approximation, not the person"})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path.rstrip("/") not in ("/v1/chat/completions",
                                             "/chat/completions"):
                self._json({"error": "not found"}, 404)
                return
            try:
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n).decode("utf-8"))
                stream = bool(req.get("stream"))
                reply, meta = service.turn(req.get("messages") or [])
            except ValueError as e:
                self._json({"error": {"message": str(e),
                                      "type": "invalid_request_error"}}, 400)
                return
            except RuntimeError as e:
                self._json({"error": {"message": str(e),
                                      "type": "upstream_error"}}, 502)
                return

            created = int(time.time())
            cid = "vhos-%d" % created
            if not stream:
                self._json({
                    "id": cid, "object": "chat.completion",
                    "created": created, "model": service.model_id,
                    "choices": [{"index": 0,
                                 "message": {"role": "assistant",
                                             "content": reply},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": None,
                              "completion_tokens":
                                  meta.get("completion_tokens"),
                              "total_tokens": None},
                })
                return

            # SSE: the upstream call is non-streaming in v0 (adapter
            # diagnostics need the whole response); chunk the finished
            # reply so streaming clients render normally
            self._headers(200, "text/event-stream",
                          {"Cache-Control": "no-cache"})
            self.end_headers()

            def chunk(delta, finish=None):
                return ("data: " + json.dumps({
                    "id": cid, "object": "chat.completion.chunk",
                    "created": created, "model": service.model_id,
                    "choices": [{"index": 0, "delta": delta,
                                 "finish_reason": finish}]}) +
                    "\n\n").encode("utf-8")

            try:
                self.wfile.write(chunk({"role": "assistant"}))
                for i in range(0, len(reply), 120):
                    self.wfile.write(chunk({"content": reply[i:i + 120]}))
                self.wfile.write(chunk({}, finish="stop"))
                self.wfile.write(b"data: [DONE]\n\n")
            except (BrokenPipeError, ConnectionError):
                pass
            self.close_connection = True

    return Handler


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", choices=("mock", "ollama", "lmstudio"),
                    default="lmstudio")
    ap.add_argument("--model", default=None,
                    help="upstream engine model id (default: first loaded)")
    ap.add_argument("--upstream", default=None, metavar="URL",
                    help="upstream engine URL (default: the adapter's, "
                         "e.g. http://localhost:1234 for LM Studio)")
    ap.add_argument("--bind", default="127.0.0.1",
                    help="address to serve on; default local-only. Use "
                         "0.0.0.0 to reach it from other machines on "
                         "your LAN (e.g. an Open WebUI host)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--subject", default=DEFAULT_SUBJECT)
    ap.add_argument("--name", default="Alan Turing")
    ap.add_argument("--you", default="You")
    ap.add_argument("--model-id", default=None,
                    help="model id shown to clients (default: derived "
                         "from --name, e.g. alan-turing-vhos)")
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--show-soma", action="store_true",
                    help="append the per-turn soma/params readout to "
                         "each reply (visible in any client)")
    args = ap.parse_args()

    service = VhosService(args)
    httpd = ThreadingHTTPServer((args.bind, args.port),
                                make_handler(service))
    print("VHOS serving layer — %s (modeled approximation)" % args.name)
    print("  model id : %s" % service.model_id)
    print("  endpoint : http://%s:%d/v1" % (args.bind, args.port))
    print("  upstream : %s adapter" % args.adapter)
    print("  archive  : %s" % os.path.relpath(
        os.path.join(args.subject, "sessions"), ROOT))
    print("  one continuous body; new client chats rotate the session "
          "archive, not the soma. Ctrl-C stops and saves.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        with service.lock:
            service._rotate_session()
    print("goodbye.")


if __name__ == "__main__":
    main()
