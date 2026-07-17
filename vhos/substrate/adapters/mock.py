"""Mock substrate adapter.

Deterministic, dependency-free, engine-free.  Its ``generate`` echoes
back the exact conditioning it received, so demos and tests can SHOW
what a real engine would be given — the assembled persona, the
interoceptive block, and the SOMA-modulated generation parameters —
without needing a model.  This is the null adapter the spec's Contract 3
anticipates: unsupported affect calls, nothing upstream breaks.
"""

from ..contract import Substrate, CapabilityReport, GenParams


class MockSubstrate(Substrate):

    def capabilities(self):
        return CapabilityReport(
            name="mock",
            available=True,
            modalities=["text"],
            supports_affect=False,
            supports_affect_recall=False,
            versions={"adapter": "0.1.0"},
        )

    def generate(self, prompt, corpus, persona, affect, params: GenParams) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append("MOCK SUBSTRATE — this is exactly what a real engine would receive")
        lines.append("=" * 72)
        lines.append("")
        lines.append("--- system context (persona + affect) " + "-" * 30)
        lines.append(persona if isinstance(persona, str) else repr(persona))
        lines.append("")
        lines.append("--- generation parameters (SOMA Tier-2 modulated) " + "-" * 18)
        lines.append("temperature=%.3f  top_p=%.3f  max_tokens=%s"
                     % (params.temperature, params.top_p,
                        params.max_tokens if params.max_tokens else "no cap"))
        lines.append("")
        lines.append("--- user prompt " + "-" * 52)
        lines.append(prompt)
        lines.append("")
        lines.append("--- mock reply " + "-" * 53)
        lines.append("[the engine's answer would appear here, conditioned as shown above]")
        return "\n".join(lines)

    def recall(self, query, scope, affect=None):
        return []

    def reason(self, context, question):
        return {"conclusion": "unsupported", "rationale": "mock adapter"}

    def embed(self, text):
        return [0.0]
