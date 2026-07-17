# ADR-005: LM Studio as the first live engine, via OpenAI-compatible API

Date: 2026-07-14 · Status: accepted · Decided by: Michael McAnally

## Decision

The first live-engine test runs on LM Studio (lmstudio.ai, 0.3/0.4-era
current versions), with the MODEL CHOSEN BY THE OPERATOR inside the LM
Studio UI. The adapter (`vhos/substrate/adapters/lmstudio_adapter.py`)
targets LM Studio's OpenAI-compatible endpoints
(`GET /v1/models`, `POST /v1/chat/completions`, default port 1234),
stdlib HTTP only.

## Rationale

LM Studio gives the operator a GUI for model download, quantization
choice, GPU offload, and a one-click local server — the least-friction
path to a fully local engine on a second machine, which is what the
spec's local-first custody principle asks for. The OpenAI-compatible
API shape is the most widely cloned local-API surface in the
ecosystem, so this adapter doubles as a template for any other server
speaking the same dialect (llama.cpp server, vLLM, etc.). LM Studio
also exposes a native REST API (`/api/v1/*` since 0.4.0); we
deliberately bind to the compatibility surface as the more durable of
the two.

## Consequences

Tier-2 SOMA coupling maps cleanly: temperature, top_p, max_tokens, and
seed all pass through the chat-completions call. The engine remains
disposable (spec Part I): the Ollama adapter stays in-tree, and
replacing either touches nothing upstream. Model choice is recorded by
the operator in test reports, not hard-coded anywhere.
