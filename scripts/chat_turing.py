"""chat_turing.py — interactive chat with the approximated subject.

The first CONTINUOUS runtime in this repository: unlike ask_turing.py
(one question, one body state, exit), this keeps the SomaEngine alive
between turns. Real wall-clock time passes for the body while you
type; your words are appraised as events and land as impulses; the
persona is reassembled every turn with the current constructed state;
Tier 2 re-derives sampling parameters from the body before every
reply. The conversation is the instance's lived experience, and the
transcript is saved into the subject's archive (sessions/) with a
v4.0 run manifest — engine, parameters, seed, persona hashes, times.

    python3 scripts/chat_turing.py                     # LM Studio (default)
    python3 scripts/chat_turing.py --adapter mock      # engine-free dry run
    python3 scripts/chat_turing.py --you "Mr. Zero" --seed 11

In-chat commands:
    /soma            show the current body state + Tier-2 parameters
    /event t1,t2 [m] push an appraisal event (tags from the table), e.g.
                     /event social_warmth 0.8   or   /event threat
    /max N|off       set or remove the reply token cap. Default: off —
                     the model generates until it finishes; the context
                     window is the only physical limit. Ctrl-C during a
                     slow turn aborts that turn (best effort), not the chat.
    /think on|off    allow or suppress hidden thinking (Qwen /no_think
                     soft switch; thinking-only models may ignore it)
    /reasoning on|off  show or hide the hidden reasoning above replies
    /save            write transcript + manifest to the archive now
    /copy            copy the markdown transcript to the clipboard
    /help            list commands
    /quit            save and leave (Ctrl-C does the same)

Every completed turn also autosaves the whole session (transcript,
run manifest, soma trace, assembled personas) — a closed console
window can no longer lose a conversation. Test 3 (2026-07-15), the
best conversation of the first live day, survives only as a console
capture because the window was closed without /quit; see
sessions/2026-07-15T15-57-00Z-chat-reconstructed/.

Spec: VHOS v4.0 — Tier 1/2 coupling (Part I), run manifest (Contract 3),
conditional-disclosure frame (Part IX). ADR-001: stdlib only.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vhos.vocabulary import Vocabulary                                # noqa: E402
from vhos.soma import SomaEngine, appraise                            # noqa: E402
from vhos.soma.appraisal import APPRAISAL_TABLE                       # noqa: E402
from vhos.soma.render import (render_interoception,                  # noqa: E402
                              generation_params, length_hint)
from vhos.affect import read_soma, apply_tuning                       # noqa: E402
from vhos.runtime import assemble_system_prompt                       # noqa: E402
from vhos.runtime.loader import (load_compiled,                       # noqa: E402
                                 soma_params_from_fingerprint)
from vhos.substrate.contract import GenParams                         # noqa: E402
from demo_loop import make_adapter                                    # noqa: E402

DEFAULT_SUBJECT = os.path.join(ROOT, "subjects", "alan_turing")

# ----------------------------------------------------------------------
# v0 lexical appraiser: which words in the visitor's message land as
# which body events. Transparent by design (same spirit as the tuning
# matcher). /event exists for anything this table cannot see.
#
# Matching rule (fixed after test 3): single-word needles match WHOLE
# WORDS only — plain substring matching fired a threat impulse from
# "war" inside "software" and spiked tension to 0.77 on an innocuous
# message. Inflected forms are therefore listed explicitly (transparent
# beats clever). Multi-word needles still match as phrases.
MESSAGE_APPRAISAL = {
    "threat":          ("threat", "threats", "threatened", "danger",
                        "dangerous", "police", "arrest", "arrested",
                        "war", "wars", "die", "dies", "died", "dying",
                        "death", "afraid", "destroy", "destroyed",
                        "shut down"),
    "loss":            ("loss", "lost", "grief", "gone", "funeral",
                        "miss him", "miss her", "died"),
    "blocked_goal":    ("impossible", "can't", "cannot", "stuck",
                        "failed", "failure", "failures", "refuse",
                        "refused", "refuses"),
    "novelty":         ("machine", "machines", "mathematics",
                        "mathematical", "mathematician", "idea",
                        "ideas", "proof", "proofs", "puzzle", "puzzles",
                        "problem", "problems", "discover", "discovers",
                        "discovered", "discovery", "discoveries",
                        "new", "2026", "computer", "computers",
                        "intelligence", "future"),
    "achievement":     ("solved", "succeeded", "won", "brilliant",
                        "you were right", "breakthrough"),
    "social_warmth":   ("friend", "friends", "dear", "thank", "thanks",
                        "wonderful", "glad", "welcome", "good to see",
                        "admire"),
    "social_exposure": ("everyone", "public", "confess", "confessed",
                        "secret", "secrets", "private", "expose",
                        "exposed", "admit"),
    "absurdity":       ("joke", "jokes", "funny", "absurd",
                        "ridiculous", "silly"),
    "rest":            ("rest", "rested", "relax", "tea", "quiet",
                        "calm down"),
}
MESSAGE_MAGNITUDE = 0.45      # gentler than scripted scene events


def truncation_warning(meta, cap):
    """Explain an empty visible reply. Thinking models put their
    chain-of-thought in reasoning_content; when the token cap dies
    mid-think, content comes back empty ("" printed silently was bug
    #1 of the first live run). Module-level so tests can call it."""
    finish = meta.get("finish_reason")
    r_tok = meta.get("reasoning_tokens")
    reasoning = (meta.get("reasoning") or "").strip()
    lines = ["  ! the engine returned no visible reply"]
    if finish == "length":
        spent = (" — all %s tokens went to hidden reasoning" % r_tok
                 if r_tok else
                 " during hidden reasoning" if reasoning else "")
        if cap:
            lines.append("  ! finish_reason=length: the cap (%d) ran out%s"
                         % (cap, spent))
            lines.append("  ! raise it:  /max %d   or remove it:  /max off"
                         % (cap * 2))
        else:
            lines.append("  ! finish_reason=length with no cap set: the "
                         "remaining context window filled%s" % spent)
            lines.append("  ! shorten the prompt window (--window) or "
                         "restart the chat to reclaim context")
    elif finish:
        lines.append("  ! finish_reason=%s" % finish)
    if reasoning:
        tail = " ".join(reasoning[-240:].split())
        lines.append("  ! reasoning tail: ...%s" % tail)
    return "\n".join(lines)


def dim_block(text, prefix="    "):
    return "\n".join(prefix + ln for ln in text.splitlines())


def appraise_message(text):
    low = " " + text.lower() + " "
    words = set(re.findall(r"[a-z0-9']+", low))
    tags = []
    for tag, needles in MESSAGE_APPRAISAL.items():
        for n in needles:
            # phrases match as substrings; single words match whole words
            if (n in low) if " " in n else (n in words):
                tags.append(tag)
                break
    return tags


# ----------------------------------------------------------------------
# terminal colors (stdlib only; os.system("") enables VT on Windows 10+)
class C:
    def __init__(self, enabled):
        e = enabled
        self.subject = "\033[38;5;222m" if e else ""   # warm amber
        self.you     = "\033[38;5;114m" if e else ""   # soft green
        self.dim     = "\033[38;5;245m" if e else ""   # gray
        self.head    = "\033[38;5;110m" if e else ""   # steel blue
        self.bold    = "\033[1m" if e else ""
        self.off     = "\033[0m" if e else ""


def supports_color(force_off):
    if force_off or os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        os.system("")          # enable ANSI processing in the console
    return sys.stdout.isatty()


# ----------------------------------------------------------------------
def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def sha12(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def clip_copy(text):
    """Best-effort clipboard (Windows clip / macOS pbcopy / X11 xclip)."""
    for cmd in (["clip"], ["pbcopy"], ["xclip", "-selection", "clipboard"]):
        try:
            p = subprocess.run(cmd, input=text.encode("utf-8"),
                               capture_output=True, timeout=5)
            if p.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


class Session:
    """Collects turns, soma trace, and run-manifest data; writes the
    archive artifacts (Contract 1 sessions/ + v4.0 run manifest)."""

    def __init__(self, subject_dir, subject_name, you, adapter_name):
        self.t0 = utcnow()
        self.subject_name = subject_name
        self.you = you
        self.adapter_name = adapter_name
        self.engine_id = adapter_name    # replaced by the model id once known
        self.seed = None
        self.turns = []          # dicts: who, text, when, params, persona_sha
        self.trace = []          # dicts: when, soma values, temp/top_p
        self.personas = {}       # sha12 -> full assembled persona text
        stamp = self.t0.strftime("%Y-%m-%dT%H-%M-%SZ")
        self.dir = os.path.join(subject_dir, "sessions", stamp + "-chat")

    def add_turn(self, who, text, params=None, persona_sha=None):
        self.turns.append({"who": who, "text": text,
                           "when": utcnow().isoformat(timespec="seconds"),
                           "params": params, "persona_sha256_12": persona_sha})

    def add_trace(self, state, gen):
        row = {"when": utcnow().isoformat(timespec="seconds")}
        row.update({k: round(v, 4) for k, v in state.values.items()})
        row.update({"temperature": round(gen.temperature, 3),
                    "top_p": round(gen.top_p, 3),
                    "max_tokens": gen.max_tokens})
        self.trace.append(row)

    # ------------------------------------------------------------------
    def markdown(self, final_state=None):
        t_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
        lines = []
        lines.append("# Conversation with the %s approximation" % self.subject_name)
        lines.append("")
        lines.append("| run info | |")
        lines.append("|---|---|")
        lines.append("| subject | %s (VHOS instance — modeled approximation) |"
                      % self.subject_name)
        lines.append("| engine | %s |" % self.engine_id)
        lines.append("| adapter | %s |" % self.adapter_name)
        lines.append("| date | %s local · %s |"
                      % (t_local, self.t0.strftime("%Y-%m-%d %H:%M UTC")))
        lines.append("| seed | %s |" % (self.seed if self.seed is not None
                                        else "unfixed"))
        lines.append("| spec | VHOS v4.0 · framework v0.1.0 · chat runtime v0.1 |")
        lines.append("| turns | %d |" % sum(1 for t in self.turns
                                            if t["who"] == self.you))
        lines.append("")
        lines.append("---")
        lines.append("")
        for t in self.turns:
            lines.append("**%s:** %s" % (t["who"], t["text"].strip()))
            lines.append("")
        if final_state is not None:
            lines.append("---")
            lines.append("")
            lines.append("*Final soma: %s. Disclosure: this transcript records "
                         "a conversation with a modeled approximation, not the "
                         "person (VHOS v4.0, Part VIII).*"
                         % {k: round(v, 3) for k, v in final_state.values.items()})
            lines.append("")
        return "\n".join(lines)

    def manifest(self, persona_sha, final_state, base_params):
        return {
            "$schema": "vhos/4.0/run-manifest",
            "engine_id": self.engine_id,
            "adapter": self.adapter_name,
            "params": {"temperature_base": base_params.temperature,
                       "top_p_base": base_params.top_p,
                       "max_tokens_base": base_params.max_tokens},
            "seed": self.seed,
            "persona_sha256_12_last": persona_sha,
            "persona_sha256_12_per_turn": [t["persona_sha256_12"]
                                           for t in self.turns
                                           if t["persona_sha256_12"]],
            "soma_state_final": {k: round(v, 4)
                                 for k, v in final_state.values.items()},
            "started": self.t0.isoformat(timespec="seconds"),
            "ended": utcnow().isoformat(timespec="seconds"),
            "turns": len(self.turns),
        }

    def save(self, persona_sha, final_state, base_params):
        os.makedirs(self.dir, exist_ok=True)
        md = self.markdown(final_state)
        with open(os.path.join(self.dir, "transcript.md"), "w",
                  encoding="utf-8") as f:
            f.write(md)
        with open(os.path.join(self.dir, "run_manifest.json"), "w",
                  encoding="utf-8") as f:
            json.dump(self.manifest(persona_sha, final_state, base_params),
                      f, indent=2)
        if self.trace:
            cols = list(self.trace[0].keys())
            with open(os.path.join(self.dir, "soma_trace.csv"), "w",
                      encoding="utf-8") as f:
                f.write(",".join(cols) + "\n")
                for row in self.trace:
                    f.write(",".join(str(row.get(c, "")) for c in cols) + "\n")
        if self.personas:
            # attribution requires the exact text the engine was told
            # (TR-001 I-5): every unique assembled persona, by hash
            with open(os.path.join(self.dir, "personas.md"), "w",
                      encoding="utf-8") as f:
                f.write("# Assembled personas used in this session\n\n"
                        "One block per unique persona; the run manifest "
                        "maps each turn to a hash.\n")
                for sha, text in self.personas.items():
                    f.write("\n## persona %s\n\n```text\n%s\n```\n"
                            % (sha, text.rstrip()))
        return self.dir, md


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", choices=("mock", "ollama", "lmstudio"),
                    default="lmstudio")
    ap.add_argument("--model", default=None)
    ap.add_argument("--host", default=None)
    ap.add_argument("--seed", type=int, default=None,
                    help="fix the sampling seed for reproducible runs")
    ap.add_argument("--subject", default=DEFAULT_SUBJECT,
                    help="subject archive directory")
    ap.add_argument("--name", default="Alan Turing",
                    help="display name of the approximated persona")
    ap.add_argument("--you", default="You",
                    help="your display name in the chat and transcript")
    ap.add_argument("--window", type=int, default=12,
                    help="conversation turns kept in the prompt window")
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="optional token cap per reply; 0 = no cap — "
                         "generate until finished (change live with "
                         "/max N or /max off)")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--quiet", action="store_true",
                    help="hide the per-turn soma/params line")
    args = ap.parse_args()

    col = C(supports_color(args.no_color))

    adapter = make_adapter(args.adapter, model=args.model, host=args.host)
    statements, fingerprint = load_compiled(args.subject)
    vocab = Vocabulary()
    params = soma_params_from_fingerprint(fingerprint)
    engine = SomaEngine(params=params,
                        seed=args.seed if args.seed is not None else 42)

    sess = Session(args.subject, args.name, args.you, args.adapter)
    sess.seed = args.seed
    base = GenParams(seed=args.seed,
                     max_tokens=(max(64, args.max_tokens)
                                 if args.max_tokens > 0 else None))
    thinking = True          # /think — Qwen soft switch, on by default
    show_reasoning = False   # /reasoning — print hidden thinking

    # banner ------------------------------------------------------------
    now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    engine_label = getattr(adapter, "model", None) or args.adapter
    bar = "─" * 66
    print(col.head + bar + col.off)
    print(col.head + col.bold + "  VHOS chat runtime v0.1 — %s" % args.name
          + col.off + col.dim + "  (modeled approximation)" + col.off)
    print(col.dim + "  engine: %s · adapter: %s · %s" %
          (engine_label, args.adapter, now_local) + col.off)
    print(col.dim + "  body: continuous (soma persists between turns; "
          "time passes while you type)" + col.off)
    print(col.dim + "  commands: /soma /event /max /think /reasoning "
          "/save /copy /help /quit" + col.off)
    print(col.head + bar + col.off)

    last_t = time.monotonic()
    persona_sha = ""
    state = engine.state

    def show_soma(gen=None):
        vals = "  ".join("%s=%.2f" % (k, v) for k, v in state.values.items())
        extra = ("  |  temp=%.2f top_p=%.2f max=%s"
                 % (gen.temperature, gen.top_p,
                    gen.max_tokens if gen.max_tokens else "off")) if gen else ""
        print(col.dim + "  · soma " + vals + extra + col.off)

    def do_save():
        d, md = sess.save(persona_sha, state, base)
        print(col.dim + "  saved -> %s" % os.path.relpath(d, ROOT) + col.off)
        return md

    try:
        while True:
            try:
                user = input(col.you + col.bold + args.you + ": "
                             + col.off + col.you).strip()
            finally:
                sys.stdout.write(col.off)
            if not user:
                continue

            # -- commands ------------------------------------------------
            if user.startswith("/"):
                cmd, _, rest = user.partition(" ")
                cmd = cmd.lower()
                if cmd == "/quit":
                    break
                elif cmd == "/help":
                    print(col.dim + __doc__.split("In-chat commands:")[1]
                          .split("Spec:")[0] + col.off)
                elif cmd == "/soma":
                    gen = generation_params(state, params, base=base)
                    show_soma(gen)
                    coarse = read_soma(state, params)
                    print(col.dim + "  · affect valence=%.2f arousal=%.2f %s"
                          % (coarse.valence, coarse.arousal,
                             coarse.categories) + col.off)
                elif cmd == "/event":
                    bits = rest.split()
                    tags = [t.strip() for t in
                            (bits[0].split(",") if bits else []) if t.strip()]
                    mag = float(bits[1]) if len(bits) > 1 else 1.0
                    known = [t for t in tags if t in APPRAISAL_TABLE]
                    if not known:
                        print(col.dim + "  tags: %s"
                              % ", ".join(sorted(APPRAISAL_TABLE)) + col.off)
                    else:
                        engine.step(impulses=appraise(known, mag))
                        engine.run(6)
                        state = engine.state
                        print(col.dim + "  event %s (mag %.2f) applied"
                              % (known, mag) + col.off)
                        show_soma()
                elif cmd == "/max":
                    arg = rest.strip().lower()
                    if arg in ("off", "none", "0"):
                        base.max_tokens = None
                        print(col.dim + "  cap removed — replies generate "
                              "until finished" + col.off)
                    else:
                        try:
                            base.max_tokens = max(64, int(arg))
                            print(col.dim + "  max_tokens cap -> %d"
                                  % base.max_tokens + col.off)
                        except ValueError:
                            print(col.dim + "  usage: /max 4096  or  "
                                  "/max off   (current: %s)"
                                  % (base.max_tokens or "off") + col.off)
                elif cmd == "/think":
                    thinking = rest.strip().lower() != "off"
                    print(col.dim + ("  thinking allowed" if thinking else
                          "  thinking suppressed — /no_think soft switch; "
                          "thinking-only models may ignore it") + col.off)
                elif cmd == "/reasoning":
                    show_reasoning = rest.strip().lower() != "off"
                    print(col.dim + "  hidden reasoning: %s"
                          % ("shown" if show_reasoning else "hidden")
                          + col.off)
                elif cmd == "/save":
                    do_save()
                elif cmd == "/copy":
                    ok = clip_copy(sess.markdown(state))
                    print(col.dim + ("  transcript copied to clipboard"
                          if ok else "  no clipboard tool found — use /save "
                          "and open the file") + col.off)
                else:
                    print(col.dim + "  unknown command — /help" + col.off)
                continue

            # -- the body lives through the pause you took to type -------
            now = time.monotonic()
            elapsed = min(now - last_t, 600.0)
            last_t = now
            if elapsed >= 1.0:
                engine.run(int(elapsed))

            # -- your words land as events --------------------------------
            tags = appraise_message(user)
            if tags:
                engine.step(impulses=appraise(tags, MESSAGE_MAGNITUDE))
                engine.run(6)
            state = engine.state

            # -- construct the current state (general -> personal) --------
            coarse = read_soma(state, params)
            ctx = set(tags) | set(re.findall(r"[a-z']+", user.lower()))
            affect = apply_tuning(coarse, fingerprint, vocab,
                                  context_tags=sorted(ctx))
            intero = render_interoception(state, params)
            hint = length_hint(state, params)   # fatigue -> brevity, via
            if hint:                            # prompt, not token cap
                intero = intero + " " + hint
            affect.interoception = intero
            gen = generation_params(state, params, base=base)

            # -- assemble persona fresh with this turn's constructed state
            persona = assemble_system_prompt(args.name, statements,
                                             affect_state=affect,
                                             interoception=intero)
            persona_sha = sha12(persona)
            sess.personas.setdefault(persona_sha, persona)

            # -- conversation window into the prompt ----------------------
            recent = sess.turns[-(args.window * 2):]
            convo = "".join("%s: %s\n" % (t["who"], t["text"]) for t in recent)
            prompt = (
                ("Conversation so far:\n%s\n" % convo if convo else "")
                + "%s: %s\n\n" % (args.you, user)
                + "Reply as %s — one conversational turn, first person, "
                  "no speaker label." % args.name)
            if not thinking:
                prompt += "\n/no_think"

            sess.add_turn(args.you, user)
            aborted = False
            try:
                reply = adapter.generate(prompt=prompt, corpus=None,
                                         persona=persona, affect=affect,
                                         params=gen)
            except KeyboardInterrupt:
                # abort THIS turn, keep the chat (matters when uncapped);
                # the server may still finish the request in the background
                aborted = True
                reply = ""
            reply = reply.strip()
            meta = {} if aborted else (getattr(adapter, "last_result", None)
                                       or {})
            # strip a leading speaker label if the engine added one anyway
            if reply.lower().startswith(args.name.lower() + ":"):
                reply = reply[len(args.name) + 1:].strip()

            if show_reasoning and meta.get("reasoning"):
                print(col.dim + "  · hidden reasoning\n"
                      + dim_block(meta["reasoning"].strip()) + col.off)

            if aborted:
                print(col.dim + "\n  · turn aborted — the body lives on; "
                      "carry on typing or /quit" + col.off)
                reply = "[turn aborted by operator]"
            elif not reply:
                print(col.subject + col.bold + args.name + ":" + col.off
                      + col.dim + " [no visible reply]" + col.off)
                print(col.dim + truncation_warning(meta, gen.max_tokens)
                      + col.off)
                reply = ("[no visible reply — finish_reason=%s]"
                         % (meta.get("finish_reason") or "unknown"))
            else:
                print(col.subject + col.bold + args.name + ":" + col.off
                      + " " + col.subject + reply + col.off)

            sess.add_turn(args.name, reply,
                          params={"temperature": round(gen.temperature, 3),
                                  "top_p": round(gen.top_p, 3),
                                  "max_tokens": gen.max_tokens},
                          persona_sha=persona_sha)
            sess.add_trace(state, gen)
            # engine identity: the concrete model id, not the adapter
            # name (Contract 3 run manifest; TR-001 I-2)
            sess.engine_id = getattr(adapter, "model", None) or args.adapter
            # autosave: the lived record must not depend on a graceful
            # exit — test 3 was lost to a closed console window
            try:
                sess.save(persona_sha, state, base)
            except OSError:
                pass
            if not args.quiet:
                show_soma(gen)
            print()

    except (KeyboardInterrupt, EOFError):
        print()

    if sess.turns:
        do_save()
        print(col.dim + "  (%d turns · transcript.md, run_manifest.json, "
              "soma_trace.csv in the session folder)" % len(sess.turns)
              + col.off)
    print(col.head + "  goodbye." + col.off)


if __name__ == "__main__":
    main()
