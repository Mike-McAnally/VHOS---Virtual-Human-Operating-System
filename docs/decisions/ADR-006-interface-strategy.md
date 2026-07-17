# ADR-006: Chat interfaces stay outside VHOS — the runtime serves the protocol they already speak

Date: 2026-07-17 · Status: accepted · Decided by: Michael McAnally

## Decision

VHOS does not grow a chat UI. Instead the runtime gains a thin serving
layer (`scripts/serve_vhos.py`, stdlib only) that presents the running
instance as a **model** on an OpenAI-compatible endpoint
(`GET /v1/models`, `POST /v1/chat/completions`, streaming and
non-streaming). Any chat front-end that can talk to an
OpenAI-compatible server — Open WebUI (github.com/open-webui/open-webui),
LM Studio's own chat window pointed at a custom endpoint, a phone
client, anything yet to be written — becomes a viewer over the
simulant without VHOS knowing or caring which one.

The terminal runtime (`chat_turing.py`) remains the reference
operator's interface: commands (`/soma`, `/event`, …), visible
Tier-2 readouts, direct archive access.

## Rationale

Three forces, all pointing the same way:

1. **Survivability (the CONTINUITY argument, one layer up).** Chat
   UIs churn on a 2–3-year cycle; the OpenAI chat-completions dialect
   is the most widely cloned API surface in the ecosystem and is
   already our downstream binding (ADR-005). A UI embedded in VHOS
   would be the least durable component in a system designed to
   outlive its components. By speaking the protocol instead, VHOS
   sits *between* two commodity layers — any UI above, any engine
   below — and owns only what no commodity provides: the body, the
   persona, the archive.
2. **The operator should not maintain UI code.** Open WebUI alone
   ships auth, chat history, mobile layout, voice input, and model
   switching — years of work VHOS gets by conforming to one protocol.
3. **The persona must not depend on client behavior.** With the
   serving layer, the persona, soma, appraisal, and Tier-2 parameters
   are applied server-side on every turn. A web client cannot forget
   the system prompt, override the temperature, or bypass disclosure:
   client-supplied `system` messages and sampling parameters are
   ignored by design (the body decides the temperature, not the UI).

## How a request flows

    Open WebUI / any client
        POST /v1/chat/completions {messages, stream}
    serve_vhos.py
        elapsed wall time -> SomaEngine.run()          (body lives)
        newest user message -> lexical appraiser       (words land)
        soma -> read_soma -> apply_tuning -> Tier 1    (state constructed)
        assemble_system_prompt(...)                    (persona, fresh)
        soma -> generation_params -> Tier 2            (params derived)
        -> LM Studio /v1/chat/completions              (ADR-005 adapter)
        <- reply; archived; returned to client (SSE if stream)

Conversation identity: the serving layer treats a request whose
history contains at most one user message as the start of a new
conversation — the current session archive is closed and a new one
opened. **The body is not reset.** One served instance is one
continuous body across conversations, exactly as the terminal runtime
behaves across turns; a client starting a "new chat" is a visitor
returning, not a new Turing. Operators who want a fresh body restart
the server.

## Consequences

- Sessions archive server-side per Contract 1 / Appendix C
  (autosaved every turn), regardless of what the client stores.
  The client's chat history is a convenience copy; the archive is
  the record.
- The soma readout that the terminal prints per turn is available to
  API clients as a trailing metadata line the UI simply renders as
  part of the reply (off by default; `--show-soma` enables it).
- Multiple simultaneous clients would share one body; v0 serializes
  requests (one turn at a time) and leaves multi-visitor semantics
  as an explicitly open question for the spec.
- Streaming: the upstream engine call stays non-streaming in v0 (the
  adapter's diagnostics — reasoning_content, finish_reason — depend
  on the complete response); the serving layer chunks the finished
  reply to the client as SSE. Perceived latency is unchanged from
  the terminal experience; true token streaming is a v0.2 item.
- `chat_turing.py` and `serve_vhos.py` share the same runtime
  assembly path; a fix in one is a fix in both.
