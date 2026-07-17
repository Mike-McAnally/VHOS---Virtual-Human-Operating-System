# Model picks — Mike's machine (personal, hardware-specific)

Scope note: this file is for the operator's own use on ONE specific
machine. It is not general guidance and not part of the spec. Anyone
else should ignore it and size models to their own hardware.

## The machine

- GPU: 16 GB VRAM
- RAM: 64 GB
- CPU: 18-core Xeon (older generation)
- OS: Windows 10
- Engine: LM Studio (OpenAI-compatible server, ADR-005)

## The one rule that decides fast vs. tedious

If the model's weights + KV cache fit inside the 16 GB VRAM, generation
is fast (tens of tokens/sec). If it spills into the 64 GB system RAM,
layers run on the Xeon and speed collapses to single digits. So keep
loaded weights at or under ~13-14 GB and leave the rest for context and
for Windows' own ~1 GB of VRAM use.

Reference point: the VHOS pipeline itself (HDL compile + soma + affect +
assemble) is ~50 ms total. The ONLY real cost is LM Studio inference.
Nothing trains; "compile" just parses text to JSON.

## Shortlist (task = persona fidelity + instruction-following, NOT coding)

All Q4_K_M unless noted. VRAM figures are approximate weight sizes;
add ~0.5-1 GB for a 4096-token KV cache.

| pick | model | ~VRAM | why for THIS test |
|---|---|---|---|
| Start here | Qwen3 14B | ~9 GB | Best all-round for 8-16 GB; strong instruction-following, which is what makes it obey the "embody, never state" guardrails. Apache 2.0. ~6 GB left for context. |
| Best voice | Gemma 4 12B (Jun 2026) | ~8 GB | Gemma prose is the most natural/literary — best shot at the dry Turing wit. Switch to this if Qwen3 feels flat. |
| Fastest / most headroom | GPT-OSS 20B | ~13.7 GB | ~42 tok/s, strong logic. Tight on VRAM, so keep context at 4096. Snappiest iteration. |
| Instruction specialist | Phi-4 Reasoning (Plus) | ~9-10 GB | Top IFBench. CAVEAT: reasoning models think out loud and may LEAK the affect scaffolding into the reply. Run it once to watch what it does with the interoception block, but use a plain instruct model for the clean A/B. |

Skip 24-27B classes on this box: at Q4 they land ~15-16 GB, too tight
once Windows and the KV cache are counted — they will spill and crawl.

## LM Studio settings for all of the above

- quant: Q4_K_M (drop to Q4_K_S if it runs hot; Q5_K_M only on the 8-12B
  picks where VRAM allows)
- GPU offload: ALL layers
- context length: 4096 (the assembled persona is ~970 tokens; no need for more)
- watch the VRAM estimate on load — keep it under ~14 GB

## Suggested run order

1. Qwen3 14B — the A/B trio (calm / stressed / warm), fixed seed.
2. Gemma 4 12B — identical prompts, same seed.
   Two different model families on the same conditioning is itself the
   signal: if BOTH show the calm/stressed divergence, that is the
   conditioning working, not one model's quirk.
3. (optional) Phi-4 Reasoning — to see a reasoning model narrate the soma.

## Honesty note

Names/versions here come from July-2026 roundups, not first-hand
benchmarks, and they drift week to week. Search the current point
release in LM Studio's model browser. Sources on file:
- localllm.in/blog/best-local-llms-16gb-vram
- huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally
- acecloud.ai/blog/best-open-source-llms
