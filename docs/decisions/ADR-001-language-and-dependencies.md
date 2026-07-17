# ADR-001: Python, stdlib-only core

Date: 2026-07-14 · Status: accepted · Decided by: Michael McAnally

## Decision

Reference implementation in Python (3.10+). The core — HDL compiler,
SOMA engine, affect models, archive tools — imports NOTHING outside
the standard library. Substrate adapters are the only exception zone,
and even the Ollama adapter uses stdlib HTTP.

## Rationale

Python is readable by all three of the spec's audiences and owns the
local-AI ecosystem the runtime will need. The 20-year durability risk
of an interpreted language is answered by the dependency rule: zero
third-party packages means zero supply-chain rot; this code runs
unmodified on any Python of the 2040s. Adapters are disposable by
design (spec Part I), so their dependencies die with them, harmlessly.

## Rejected

Rust (durability win, but slower iteration at the 10,000-foot stage,
weaker AI ecosystem, unreadable to the spec's first audience).
TypeScript (fastest-churning ecosystem of the three — worst 20-year fit).
Curated dependencies (pydantic etc.: nicer ergonomics, real rot risk).
