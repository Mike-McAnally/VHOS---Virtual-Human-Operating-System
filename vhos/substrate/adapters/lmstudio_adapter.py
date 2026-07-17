"""LM Studio adapter — local engine via the OpenAI-compatible API.

LM Studio (lmstudio.ai) serves whatever model the operator has loaded
at http://localhost:1234 with OpenAI-compatible endpoints; since
LM Studio 0.4.x a native REST API also exists at /api/v1/*.  This
adapter targets the OpenAI-compatible surface because it is the most
durable local-API shape in the ecosystem (ADR-005):

    GET  /v1/models             -> list loaded/available model ids
    POST /v1/chat/completions   -> generation (system + user messages)
    POST /v1/embeddings         -> embeddings (if an embedding model is loaded)

The operator chooses the model inside LM Studio; if --model is not
given, the adapter uses the first id reported by /v1/models.

Adapters are DISPOSABLE by design (spec Part I): stdlib HTTP only,
nothing upstream knows this file exists.
"""

import json
import urllib.request
import urllib.error

from ..contract import Substrate, CapabilityReport, GenParams

DEFAULT_HOST = "http://localhost:1234"


class LMStudioSubstrate(Substrate):

    def __init__(self, model=None, host=DEFAULT_HOST, timeout=None):
        self.model = model            # None -> first loaded model
        self.host = host.rstrip("/")
        self.timeout = timeout or 1800   # thinking models at ~4 t/s are slow
        # Diagnostics from the most recent generate() call. Thinking
        # models return their chain-of-thought in reasoning_content and
        # may leave content empty when truncated; callers that want to
        # warn (or display the reasoning) read this. Additive only —
        # the Substrate contract is unchanged.
        self.last_result = {}

    # ------------------------------------------------------------------
    def _get(self, path, timeout=None):
        req = urllib.request.Request(self.host + path)
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.host + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer lm-studio"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _models(self, timeout=4):
        out = self._get("/v1/models", timeout=timeout)
        return [m.get("id", "?") for m in out.get("data", [])]

    def _resolve_model(self):
        if self.model:
            return self.model
        models = self._models()
        if not models:
            raise RuntimeError(
                "LM Studio is running but no model is loaded. Load one in "
                "the LM Studio window (or the Developer > Server tab), "
                "then retry.")
        self.model = models[0]
        return self.model

    # ------------------------------------------------------------------
    def capabilities(self):
        try:
            models = self._models()
            ok = True
        except (urllib.error.URLError, OSError, ValueError):
            models, ok = [], False
        return CapabilityReport(
            name="lmstudio:%s" % (self.model or (models[0] if models else "?")),
            available=ok,
            modalities=["text"],
            supports_affect=False,          # affect math is runtime-side
            supports_affect_recall=False,
            versions={"adapter": "0.1.0", "api": "openai-compat"},
            limits={"host": self.host, "models_visible": models},
        )

    def generate(self, prompt, corpus, persona, affect, params: GenParams) -> str:
        payload = {
            "model": None,   # filled below
            "messages": [
                {"role": "system",
                 "content": persona if isinstance(persona, str) else str(persona)},
                {"role": "user", "content": prompt},
            ],
            "temperature": params.temperature,
            "top_p": params.top_p,
            "stream": False,
        }
        # omitted max_tokens = no cap: LM Studio generates until the
        # model stops on its own or the context window is exhausted
        if params.max_tokens:
            payload["max_tokens"] = params.max_tokens
        if params.seed is not None:
            payload["seed"] = params.seed
        try:
            payload["model"] = self._resolve_model()
            out = self._post("/v1/chat/completions", payload)
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(
                "LM Studio not reachable at %s (%s).\n"
                "  1. Open LM Studio and load your chosen model\n"
                "  2. Developer tab -> Start Server (default port 1234)\n"
                "  3. If you changed the port, pass --host http://localhost:<port>"
                % (self.host, e))
        choices = out.get("choices") or []
        if not choices:
            raise RuntimeError("LM Studio returned no choices: %s"
                               % json.dumps(out)[:400])
        msg = choices[0].get("message") or {}
        usage = out.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        self.last_result = {
            "content": msg.get("content") or "",
            # LM Studio uses reasoning_content; some servers use reasoning
            "reasoning": msg.get("reasoning_content")
                         or msg.get("reasoning") or "",
            "finish_reason": choices[0].get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens"),
        }
        return self.last_result["content"]

    def recall(self, query, scope, affect=None):
        # v0: retrieval is runtime-side (roadmap step 2).
        return []

    def reason(self, context, question):
        text = self.generate(
            prompt="Context:\n%s\n\nQuestion: %s\nAnswer with a conclusion "
                   "and a short rationale." % (context, question),
            corpus=None, persona="You are a careful reasoner.",
            affect=None, params=GenParams(temperature=0.2, max_tokens=400))
        return {"conclusion": text.strip(), "rationale": "see conclusion"}

    def embed(self, text):
        try:
            out = self._post("/v1/embeddings",
                             {"model": self._resolve_model(), "input": text})
            data = out.get("data") or []
            return data[0].get("embedding", []) if data else []
        except (urllib.error.URLError, OSError, RuntimeError):
            return []
