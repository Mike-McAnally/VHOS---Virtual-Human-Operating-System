"""Ask the Turing instance one question, in a chosen bodily state.

This is the A/B harness for the live test: the SAME question asked in
different soma states should produce measurably different answers,
because the state changes both the context (Tier 1) and the sampling
parameters (Tier 2).

    python3 scripts/ask_turing.py --state calm     --prompt "Can machines think?"
    python3 scripts/ask_turing.py --state stressed --prompt "Can machines think?"
    python3 scripts/ask_turing.py --state warm     --prompt "Tell me about Christopher."

States:
    calm      baseline body, no events
    stressed  threat + social_exposure, 45 s settle — also arms the
              disclosure context, so the divergence map (felt:
              distressed, shown: amused) enters the conditioning
    warm      social_warmth + achievement, 45 s settle

Options: --adapter lmstudio|ollama|mock (default lmstudio),
--model, --host, --seed N (fixed for reproducibility),
--show-prompt (dump the full assembled system context).

Defaults to LM Studio (see LIVE-TEST-GUIDE.pdf).
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vhos.vocabulary import Vocabulary                            # noqa: E402
from vhos.soma import SomaEngine, appraise                        # noqa: E402
from vhos.soma.render import render_interoception, generation_params  # noqa: E402
from vhos.affect import read_soma, apply_tuning                   # noqa: E402
from vhos.runtime import assemble_system_prompt                   # noqa: E402
from vhos.runtime.loader import (load_compiled,                   # noqa: E402
                                 soma_params_from_fingerprint)
from vhos.substrate.contract import GenParams                     # noqa: E402
from demo_loop import make_adapter                                # noqa: E402

SUBJECT_DIR = os.path.join(ROOT, "subjects", "alan_turing")

STATES = {
    "calm": {"tags": [], "context": []},
    "stressed": {"tags": ["threat", "social_exposure"],
                 "context": ["disclosing", "persecution", "friends"]},
    "warm": {"tags": ["social_warmth", "achievement"],
             "context": []},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", choices=sorted(STATES), default="calm")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--adapter", choices=("mock", "ollama", "lmstudio"),
                    default="lmstudio")
    ap.add_argument("--model", default=None)
    ap.add_argument("--host", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    adapter = make_adapter(args.adapter, model=args.model, host=args.host)
    statements, fingerprint = load_compiled(SUBJECT_DIR)
    vocab = Vocabulary()
    params = soma_params_from_fingerprint(fingerprint)

    engine = SomaEngine(params=params, seed=args.seed if args.seed is not None else 42)
    spec = STATES[args.state]
    if spec["tags"]:
        engine.step(impulses=appraise(spec["tags"]))
        engine.run(45)

    st = engine.state
    coarse = read_soma(st, params)
    affect = apply_tuning(coarse, fingerprint, vocab,
                          context_tags=spec["context"])
    intero = render_interoception(st, params)
    affect.interoception = intero
    gen = generation_params(st, params, base=GenParams(seed=args.seed))

    print("state=%s  soma=%s" % (args.state,
          {k: round(v, 3) for k, v in st.values.items()}))
    print("affect: valence=%.2f arousal=%.2f %s"
          % (coarse.valence, coarse.arousal, coarse.categories))
    print("params: temp=%.2f top_p=%.2f max_tokens=%d seed=%s"
          % (gen.temperature, gen.top_p, gen.max_tokens, gen.seed))

    persona = assemble_system_prompt("Alan Turing", statements,
                                     affect_state=affect,
                                     interoception=intero)
    if args.show_prompt:
        print("\n----- assembled system context -----\n")
        print(persona)

    reply = adapter.generate(prompt=args.prompt, corpus=None,
                             persona=persona, affect=affect, params=gen)
    print("\n----- reply (%s, %s) -----\n" % (args.adapter, args.state))
    print(reply)


if __name__ == "__main__":
    main()
