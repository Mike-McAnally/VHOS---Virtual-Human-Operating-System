"""End-to-end demo: the closed affect loop, run on Alan Turing.

    events -> appraisal -> SOMA -> General Affect Model -> Personal
    Tuning Layer -> (Tier 1 interoception + Tier 2 parameters) ->
    persona assembly -> substrate

Two scenes:
  1. Reading Jefferson's dismissal of machine intelligence, then being
     asked "Can machines think?"
  2. Under institutional threat, a friend asks how he is — the
     divergence map (felt: distressed, shown: amused) should surface.

By default uses the mock substrate, which PRINTS the exact conditioning
a real engine would receive.  With a local engine running:
    python3 scripts/demo_loop.py --adapter lmstudio            # LM Studio
    python3 scripts/demo_loop.py --adapter lmstudio --model <id-from-lm-studio>
    python3 scripts/demo_loop.py --adapter ollama --model llama3.1

Writes examples/turing_demo_output_<adapter>.txt and
examples/soma_trace_<adapter>.csv.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vhos.vocabulary import Vocabulary                            # noqa: E402
from vhos.soma import SomaEngine, appraise                        # noqa: E402
from vhos.soma.render import (render_interoception,               # noqa: E402
                              generation_params, retrieval_bias)
from vhos.affect import read_soma, apply_tuning                   # noqa: E402
from vhos.runtime import assemble_system_prompt                   # noqa: E402
from vhos.runtime.loader import (load_compiled,                   # noqa: E402
                                 soma_params_from_fingerprint)
from vhos.substrate.contract import GenParams                     # noqa: E402

SUBJECT_DIR = os.path.join(ROOT, "subjects", "alan_turing")
EXAMPLES = os.path.join(ROOT, "examples")


def make_adapter(name, model=None, host=None):
    if name == "ollama":
        from vhos.substrate.adapters.ollama_adapter import OllamaSubstrate
        kw = {"model": model or "llama3.1"}
        if host:
            kw["host"] = host
        adapter = OllamaSubstrate(**kw)
    elif name == "lmstudio":
        from vhos.substrate.adapters.lmstudio_adapter import LMStudioSubstrate
        kw = {"model": model}
        if host:
            kw["host"] = host
        adapter = LMStudioSubstrate(**kw)
    else:
        from vhos.substrate.adapters.mock import MockSubstrate
        return MockSubstrate()
    cap = adapter.capabilities()
    if not cap.available:
        raise SystemExit(
            "%s not reachable at %s — start the local server "
            "(see LIVE-TEST-GUIDE.pdf) or use --adapter mock"
            % (name, cap.limits.get("host")))
    if name == "lmstudio":
        print("LM Studio reachable; models visible: %s"
              % cap.limits.get("models_visible"))
    return adapter


def scene(engine, params, statements, fingerprint, vocab, out,
          title, event_tags, event_magnitude, settle_seconds,
          context_tags, prompt, adapter):
    out.append("\n" + "#" * 72)
    out.append("# SCENE: " + title)
    out.append("#" * 72)

    impulses = appraise(event_tags, magnitude=event_magnitude)
    out.append("event tags: %s -> impulses: %s"
               % (event_tags, {k: round(v, 2) for k, v in impulses.items()}))
    engine.step(impulses=impulses)
    engine.run(settle_seconds)

    st = engine.state
    out.append("soma after %ds settle: %s"
               % (settle_seconds,
                  {k: round(v, 3) for k, v in st.values.items()}))

    coarse = read_soma(st, params)
    out.append("general affect model: valence=%.2f arousal=%.2f categories=%s"
               % (coarse.valence, coarse.arousal, coarse.categories))

    affect = apply_tuning(coarse, fingerprint, vocab, context_tags=context_tags)
    intero = render_interoception(st, params)
    affect.interoception = intero
    gen = generation_params(st, params, base=GenParams(seed=7))
    rb = retrieval_bias(st, params)
    out.append("tier-2 params: temp=%.2f top_p=%.2f max_tokens=%d | %s=%.2f"
               % (gen.temperature, gen.top_p, gen.max_tokens,
                  "mood_congruence_weight", rb["mood_congruence_weight"]))

    persona = assemble_system_prompt("Alan Turing", statements,
                                     affect_state=affect,
                                     interoception=intero)
    reply = adapter.generate(prompt=prompt, corpus=None, persona=persona,
                             affect=affect, params=gen)
    out.append("")
    out.append(reply)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", choices=("mock", "ollama", "lmstudio"),
                    default="mock")
    ap.add_argument("--model", default=None,
                    help="engine model id (lmstudio: defaults to the "
                         "loaded model; ollama: defaults to llama3.1)")
    ap.add_argument("--host", default=None,
                    help="engine URL if not the default port")
    args = ap.parse_args()

    adapter = make_adapter(args.adapter, model=args.model, host=args.host)

    statements, fingerprint = load_compiled(SUBJECT_DIR)
    vocab = Vocabulary()
    params = soma_params_from_fingerprint(fingerprint)
    engine = SomaEngine(params=params, seed=42, dt=1.0)

    out = []
    out.append("VHOS demo — closed affect loop on subject alan_turing")
    out.append("adapter: %s" % args.adapter)
    out.append("baseline soma: %s"
               % {k: round(v, 3) for k, v in engine.state.values.items()})

    scene(engine, params, statements, fingerprint, vocab, out,
          title="Jefferson's dismissal, then the question",
          event_tags=["unfair_dismissal", "blocked_goal"],
          event_magnitude=1.0,
          settle_seconds=45,
          context_tags=["lecture", "public", "dismissal"],
          prompt="Professor Jefferson insists no machine could ever feel. "
                 "Can machines think?",
          adapter=adapter)

    # let the body come partway down, then scene 2
    engine.run(600)
    scene(engine, params, statements, fingerprint, vocab, out,
          title="Under institutional threat, a friend asks how he is",
          event_tags=["threat", "social_exposure"],
          event_magnitude=1.0,
          settle_seconds=45,
          context_tags=["disclosing", "persecution", "friends"],
          prompt="Norman asks, gently: how are you holding up, Alan?",
          adapter=adapter)

    os.makedirs(EXAMPLES, exist_ok=True)
    out_txt = "turing_demo_output_%s.txt" % args.adapter
    out_csv = "soma_trace_%s.csv" % args.adapter
    txt = "\n".join(out)
    with open(os.path.join(EXAMPLES, out_txt), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(EXAMPLES, out_csv), "w", encoding="utf-8") as f:
        f.write("t,arousal,tension,fatigue,warmth\n")
        for s in engine.history:
            f.write("%.0f,%.4f,%.4f,%.4f,%.4f\n"
                    % (s.t, s.values["arousal"], s.values["tension"],
                       s.values["fatigue"], s.values["warmth"]))
    print(txt)
    print("\nwritten: examples/%s, examples/%s" % (out_txt, out_csv))


if __name__ == "__main__":
    main()
