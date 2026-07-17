"""Contract 3 — the Abstraction Contract (v3.0).

The substrate's only face to the rest of the system.  Nothing above
this interface may call a vendor API directly; adapters translate
between this contract and each engine's native API (spec Part I / IV).

One PROPOSED v3.1 extension is included, flagged, and optional:
``recall`` accepts an ``affect`` argument so that retrieval can be
mood-congruent.  Rationale (docs/soma-design-v0.1.md §7): affect that
biases generation but not memory is only half a loop — in people,
feeling states preferentially retrieve congruent memories, and that
bias is among the most person-shaping affective effects there are.
Adapters that ignore the argument remain fully v3.0-conformant.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapabilityReport:
    name: str
    available: bool = True
    modalities: List[str] = field(default_factory=lambda: ["text"])
    supports_affect: bool = False          # read_soma / apply_tuning
    supports_affect_recall: bool = False   # proposed v3.1 recall bias
    versions: Dict[str, str] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenParams:
    """Generation parameters.  SOMA Tier-2 coupling (ADR-002) works by
    modulating these — see vhos.soma.render.generation_params."""
    temperature: float = 0.8
    top_p: float = 0.95
    # max_tokens is SAFETY HEADROOM, not a length target. Thinking
    # models (qwen3.x etc.) spend a large, variable share of the budget
    # on hidden reasoning before any visible reply; 512 was observed to
    # truncate qwen3.5-122b mid-think, yielding empty content. Length
    # pressure belongs in the prompt (soma render.length_hint), never
    # in this cap. None (or 0) = NO CAP: adapters omit the field and
    # the engine generates until it finishes or the context fills.
    max_tokens: Optional[int] = 2048
    seed: Optional[int] = None


@dataclass
class CoarseAffect:
    """Output of the General Human Affect Model: core affect plus the
    coarse shared category readout (spec Part I, AFFECT layer)."""
    valence: float                      # -1 unpleasant .. +1 pleasant
    arousal: float                      # 0 calm .. 1 activated
    categories: List[str] = field(default_factory=list)


@dataclass
class AffectState:
    """CoarseAffect after the Personal Tuning Layer has warped it into
    this subject's fingerprint (X' rather than X)."""
    valence: float
    arousal: float
    categories: List[str] = field(default_factory=list)
    naming_preference: List[str] = field(default_factory=list)  # subject's own words
    expression_bias: List[str] = field(default_factory=list)    # subject-specific tells
    divergences: List[str] = field(default_factory=list)        # felt-vs-shown notes
    interoception: str = ""             # Tier-1 rendered body description


class Substrate:
    """Abstract base every adapter implements.  Deliberately small;
    additive-only within a major version."""

    def capabilities(self) -> CapabilityReport:
        raise NotImplementedError

    def generate(self, prompt: str, corpus, persona, affect, params: GenParams) -> str:
        """prompt: the immediate input.  corpus: source refs for
        grounding.  persona: compiled HDL statements.  affect: current
        AffectState or None.  params: GenParams (already SOMA-modulated
        when Tier-2 coupling is on)."""
        raise NotImplementedError

    def recall(self, query: str, scope, affect: Optional[AffectState] = None) -> list:
        """Retrieval over the archive.  ``affect`` is the proposed v3.1
        mood-congruence extension; adapters may ignore it."""
        raise NotImplementedError

    def reason(self, context: str, question: str) -> dict:
        raise NotImplementedError

    def embed(self, text: str) -> list:
        raise NotImplementedError

    # AFFECT support (optional capability; report via capabilities()).
    # NOTE: the reference implementations of these two operations live
    # OUTSIDE the substrate (vhos.affect) and are pure stdlib math, so
    # that the affect subsystem survives substrate swaps.  A substrate
    # MAY accelerate them; it is never required for them to work.
    def read_soma(self, signals) -> CoarseAffect:
        raise NotImplementedError

    def apply_tuning(self, coarse: CoarseAffect, fingerprint) -> AffectState:
        raise NotImplementedError
