"""VHOS — Virtual Human OS reference implementation.

Stdlib-only core implementing the machine-readable contracts of the
VHOS Unified Specification v4.0 (schema URIs keep each contract's own
version — a schema only bumps when its shape changes, so Contract 2
payloads remain vhos/3.0/* while the run manifest is vhos/4.0/*):

    Contract 1  archive layout          -> vhos.archive
    Contract 2  data schemas            -> vhos.hdl (parser, validator, compiler)
    Contract 3  substrate interface     -> vhos.substrate

plus the SOMA v0.1 engine (vhos.soma) and the reference General Affect
Model / Personal Tuning Layer (vhos.affect) that spec v3.0 declared but
left unspecified.  See docs/soma-design-v0.1.md.

Durability rules (ADR-001): the core imports nothing outside the Python
standard library.  Substrate adapters are the only disposable code and
even they use stdlib HTTP.
"""

__version__ = "0.1.1"
SPEC_VERSION = "4.0"
COMPILER_VERSION = "vhosc-0.1.0"
