"""Ollama adapter — a real local-engine adapter, stdlib HTTP only.

Targets the Ollama REST API (default http://localhost:11434), which is
the easiest way to run a local model on consumer hardware in 2026 and
matches the spec's local-first custody principle: the subject's persona
never leaves the machine.

Adapters are DISPOSABLE by design (spec Part I): when Ollama is gone,
this file is replaced and nothing upstream changes.

Status: written to the published API; exercise it with
    python3 scripts/demo_loop.py --adapter ollama --model <name>
"""

import json
import urllib.request
import urllib.error

from ..contract import Substrate, CapabilityReport, GenParams

DEFAULT_HOST = "http://localhost:11434"


class OllamaSubstrate(Substrate):

    def __init__(self, model="llama3.1", host=DEFAULT_HOST, timeout=120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    def _post(self, path, payload):
        req = urllib.request.Request(
            self.host + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def capabilities(self):
        try:
            req = urllib.request.Request(self.host + "/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                json.loads(resp.read().decode("utf-8"))
            ok = True
        except (urllib.error.URLError, OSError, ValueError):
            ok = False
        return CapabilityReport(
            name="ollama:" + self.model,
            available=ok,
            modalities=["text"],
            supports_affect=False,          # affect math is runtime-side
            supports_affect_recall=False,
            versions={"adapter": "0.1.0"},
            limits={"host": self.host},
        )

    def generate(self, prompt, corpus, persona, affect, params: GenParams) -> str:
        payload = {
            "model": self.model,
            "system": persona if isinstance(persona, str) else str(persona),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.temperature,
                "top_p": params.top_p,
                "num_predict": params.max_tokens or -1,   # -1 = no cap
            },
        }
        if params.seed is not None:
            payload["options"]["seed"] = params.seed
        try:
            out = self._post("/api/generate", payload)
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(
                "Ollama not reachable at %s (%s). Install/start Ollama and "
                "pull a model, e.g.:  ollama pull %s" % (self.host, e, self.model))
        return out.get("response", "")

    def recall(self, query, scope, affect=None):
        # v0: retrieval is runtime-side (no vector store dependency here).
        return []

    def reason(self, context, question):
        text = self.generate(
            prompt="Context:\n%s\n\nQuestion: %s\nAnswer with a conclusion "
                   "and a short rationale." % (context, question),
            corpus=None, persona="You are a careful reasoner.",
            affect=None, params=GenParams(temperature=0.2, max_tokens=400))
        return {"conclusion": text.strip(), "rationale": "see conclusion"}

    def embed(self, text):
        out = self._post("/api/embeddings", {"model": self.model, "prompt": text})
        return out.get("embedding", [])
