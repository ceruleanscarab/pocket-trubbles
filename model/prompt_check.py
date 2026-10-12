#!/usr/bin/env python3
"""Check a teacher prompt BEFORE the overnight run. Stdlib only.

The v3 overnight taught us the expensive way that one sentence in the teacher
prompt reshapes every label (P(follow | social>=8) fell 0.50 -> 0.18). This
asks the teacher ~300 questions on a fixed diagnostic panel and prints the
conditional rates the student will inherit - ~7 minutes with 3 workers, not
8 hours. Use it to compare prompts, or teachers (--model qwen3.5:27b ...).

  python3 prompt_check.py --host http://localhost:11434    # the Trubbles panel (the default, 2026-10-09)
  python3 prompt_check.py --schema 3                       # current v3 prompt
  python3 prompt_check.py --schema 3 --prompt-file cand.txt # a candidate prompt
  python3 prompt_check.py --schema 3 --model qwen3.5:27b   # another teacher

Panel (per schema line, identity randomized unless the case pins it):
  social9   content fish, social 9 (expect follow_friend high)     x40
  social1   content fish, social 1 (expect follow_friend ~0)        x40
  bold9     content + energetic, bold 9 (expect dart_play present)  x40
  bold1     same, bold 1 (expect dart_play ~0)                      x40
  content   content, mid identity (watch for a single attractor)    x40
  shadowcalm shadow near, stress 0-3 (expect flee high)             x40
  lonely    friend none, content (must not flee / seek food)        x30
  starving  hunger 9, food near (expect seek_food ~1.0)             x30
  trust     content, trust 9 vs trust 0 (v3 only; expect a shade, not a flip) x40
  v4 (--schema 4; the shadow cases are skipped, bored cases added):
  bored9bub  content, bored 9, last visit_bubbles (expect a change, explore up) x40
  bored9fol  social 8, friend near, bored 9, last follow_friend (expect a change) x40
  bored0bub  content, bored 0, last visit_bubbles (expect last mostly KEPT)     x40
  nightbored night, bored 9, last rest (expect rest - boredom never wakes the tank) x30
"""
import argparse
import concurrent.futures as cf
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_traces as gt  # noqa: E402


def state(rng, schema, **pin):
    f = dict(zone=rng.randint(1, 6), hunger=rng.randint(0, 3), energy=rng.randint(5, 9), stress=rng.randint(0, 2),
             curiosity=rng.randint(3, 8), bold=rng.randint(2, 7), social=rng.randint(2, 6),
             stage=rng.choice(["juv", "adult", "adult", "elder"]), trust=rng.randint(2, 7),
             bored=rng.randint(0, 2), food="none", shadow="none", friend=f"{rng.choice(['near','mid'])} {rng.randint(1,12)}",
             bubble=f"{rng.choice(['near','mid','far'])} {rng.randint(1,12)}",
             reef=f"{rng.choice(['mid','far'])} {rng.randint(1,12)}", wall="clear",
             last=rng.choice(["explore", "inspect_reef", "visit_bubbles", "rest"]), time="day")
    f.update(pin)
    ident = f"hunger {f['hunger']} energy {f['energy']} stress {f['stress']} curiosity {f['curiosity']} bold {f['bold']} social {f['social']} stage {f['stage']}"
    tail = (f"food {f['food']} shadow {f['shadow']} friend {f['friend']} bubble {f['bubble']} reef {f['reef']} "
            f"wall {f['wall']} last {f['last']} time {f['time']}")
    if schema >= 4:
        return (f"zone {f['zone']} {ident} trust {f['trust']} bored {f['bored']} food {f['food']} friend {f['friend']} "
                f"bubble {f['bubble']} reef {f['reef']} wall {f['wall']} last {f['last']} time {f['time']}")
    if schema >= 3:
        return f"zone {f['zone']} {ident} trust {f['trust']} {tail}"
    name = rng.choice(["mira", "bolt", "kelp", "nori"])
    fr = f['friend'] if f['friend'] == "none" else f"{rng.choice(['mira','bolt','kelp','nori'])} {f['friend']}"
    return f"fish {name} zone {f['zone']} {ident} {tail.replace('friend ' + f['friend'], 'friend ' + fr, 1)}"


def panel(rng, schema, n):
    P = []
    def add(case, k, **pin):
        for _ in range(int(n * k / 40)):
            P.append((case, state(rng, schema, **pin)))
    add("social9", 40, social=9)
    add("social1", 40, social=1)
    add("bold9", 40, bold=9, energy=9, hunger=rng.randint(0, 2))
    add("bold1", 40, bold=1, energy=9, hunger=rng.randint(0, 2))
    add("content", 40)
    if schema < 4:
        add("shadowcalm", 40, shadow=f"near {rng.randint(1,12)}", stress=rng.randint(0, 3))
    add("lonely", 30, friend="none")
    add("starving", 30, hunger=9, food=f"near {rng.randint(1,12)}")
    if schema >= 3:
        add("trust9", 20, trust=9)
        add("trust0", 20, trust=0)
    if schema >= 4:
        add("bored9bub", 40, bored=9, last="visit_bubbles", bubble=f"near {rng.randint(1,12)}")
        add("bored9fol", 40, bored=9, last="follow_friend", social=8, friend=f"near {rng.randint(1,12)}")
        add("bored0bub", 40, bored=0, last="visit_bubbles", bubble=f"near {rng.randint(1,12)}")
        add("nightbored", 30, bored=9, last="rest", time="night", energy=rng.randint(3, 6), reef=f"near {rng.randint(1,12)}")
    return P


# ---- the Trubbles panel (2026-10-09, model/trubbles_schema.md) ----
# one pinned situation per teacher priority on a calm, fed, daytime base;
# each with the share of the teacher's answers it should (or must not) get
def trubbles_state(rng, **pin):
    clock = lambda d: f"{d} {rng.randint(1, 12)}"
    f = dict(zone=rng.randint(1, 6), hunger=rng.randint(0, 3), energy=rng.randint(5, 9), stress=rng.randint(0, 2),
             content=rng.randint(4, 7), curiosity=rng.randint(3, 7), bored=rng.randint(0, 2), crowd=rng.randint(0, 3),
             cuddly=rng.randint(2, 7), bold=rng.randint(2, 7), chatty=rng.randint(2, 7),
             stage=rng.choice(["pip", "tuft", "fluff", "fluff"]), bond=rng.randint(2, 7),
             food="none", friend=clock(rng.choice(["near", "mid"])), pile="none", nook=clock(rng.choice(["mid", "far"])),
             keeper="away", chorus="off", last=rng.choice(["explore", "roll", "nap", "chirp"]), time="day")
    f.update(pin)
    return " ".join(f"{k} {f[k]}" for k in ("zone", "hunger", "energy", "stress", "content", "curiosity", "bored", "crowd",
                                          "cuddly", "bold", "chatty", "stage", "bond", "food", "friend", "pile", "nook",
                                          "keeper", "chorus", "last", "time"))


TRUBBLES_CASES = [   # (case, pins, goal, test, threshold)
    ("starving",        dict(hunger=9, food="near 3"),                       "eat",          ">=", 0.95),
    ("hungry_nofood",   dict(hunger=9, bond=8),                              "greet_keeper", ">=", 0.50),
    ("hungry_nofood",   None,                                                "eat",          "==", 0.0),
    ("terrified_shy",   dict(stress=9, bold=1),                              "hide",         ">=", 0.80),
    ("stressed_bold",   dict(stress=6, bold=9),                              "hide",         "<=", 0.50),
    ("night",           dict(time="night", energy=5),                        "nap",          ">=", 0.80),
    ("exhausted",       dict(energy=1),                                      "nap",          ">=", 0.70),
    ("keeper_bonded",   dict(keeper="near", bond=9),                         "greet_keeper", ">=", 0.50),
    ("keeper_wary",     dict(keeper="near", bond=0),                         "greet_keeper", "<=", 0.20),
    ("chorus_chatty",   dict(chorus="on", chatty=9),                         "chirp",        ">=", 0.50),
    ("crowded_cuddly",  dict(crowd=8, cuddly=9, friend="near 3"),            "cuddle",       "<=", 0.20),
    ("cuddly_friend",   dict(cuddly=9, friend="near 3", crowd=1),            "cuddle",       ">=", 0.40),
    ("lonely",          dict(friend="none", pile="none"),                    "cuddle",       "==", 0.0),
    ("lonely",          None,                                                "eat",          "==", 0.0),
    ("bored_explore",   dict(bored=9, last="explore", curiosity=8),          "explore",      "<=", 0.15),
    ("fresh_roll",      dict(bored=0, last="roll", content=8, energy=8),     "roll",         ">=", 0.30),
]


def warm_up(args, st):
    # one untimed-ish call first: a cold gemma4:26b load took 735 s on the
    # WSL box (2026-10-09), and every 30 s panel call during it counted as a failure
    print("warming up the teacher ...", flush=True)
    gt.ask_ollama(args.host, args.model, st, 1800)


def trubbles_main(args):
    gt.SCHEMA = "trubbles"
    if args.prompt_file:
        gt.SYSTEM_PROMPT_TRUBBLES = open(args.prompt_file).read().strip()
    rng = random.Random(args.seed)
    P, pins = [], {}
    for case, pin, *_ in TRUBBLES_CASES:
        if pin is not None:
            pins[case] = pin
    pins["content"] = dict(content=8, hunger=1, stress=0, bored=1)
    for case, pin in pins.items():
        P += [(case, trubbles_state(rng, **pin)) for _ in range(args.n // 2)]
    warm_up(args, P[0][1])
    print(f"{len(P)} calls to {args.model} @ {args.host} ({args.workers} workers) ...", flush=True)

    def ask(item):
        case, st = item
        try:
            g = gt.ask_ollama(args.host, args.model, st, 30)
        except Exception:  # noqa: BLE001
            g = None
        return case, (g.split()[0] if g else None)

    results, fails = {}, 0
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for case, goal in ex.map(ask, P):
            if goal is None:
                fails += 1
                continue
            results.setdefault(case, {}).setdefault(goal, 0)
            results[case][goal] += 1
    print(f"\nfailures: {fails}")
    bad = 0
    for case, _, goal, op, thr in TRUBBLES_CASES:
        d = results.get(case, {}); n = sum(d.values())
        v = d.get(goal, 0) / n if n else float("nan")
        ok = v >= thr if op == ">=" else v <= thr if op == "<=" else v <= thr + 1e-9
        bad += not ok
        print(f"  {'OK ' if ok else 'BAD'}  P({goal} | {case}) = {v:.2f}  (n={n}, want {op} {thr})")
    d = results.get("content", {}); n = sum(d.values()) or 1
    mx = max(d.values()) / n if d else 0
    bad += mx >= 0.45
    print(f"  {'OK ' if mx < 0.45 else 'BAD'}  max single goal | content = {mx:.2f}  (want < 0.45)")
    print("\n  per case:")
    for case in pins:
        d = results.get(case, {}); n = sum(d.values()) or 1
        print(f"    {case:15s} " + ", ".join(f"{g} {c / n:.2f}" for g, c in sorted(d.items(), key=lambda kv: -kv[1])[:4]))
    print(f"\n{'PASS' if not bad else f'{bad} BAD - fix the prompt before an overnight run'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", type=lambda v: int(v) if v.isdigit() else v, choices=(2, 3, 4, "trubbles"), default="trubbles")
    ap.add_argument("--host", default="http://192.168.0.139:11434")
    ap.add_argument("--model", default="gemma4:26b")
    ap.add_argument("--prompt-file", default=None, help="candidate system prompt (default: gen_traces' prompt for the schema)")
    ap.add_argument("--n", type=int, default=40, help="calls per major case (default 40 -> ~320 calls)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    if args.schema == "trubbles":
        return trubbles_main(args)
    gt.SCHEMA = args.schema
    if args.prompt_file:
        txt = open(args.prompt_file).read().strip()
        gt.SYSTEM_PROMPT = txt
        gt.SYSTEM_PROMPT_V3 = txt
        gt.SYSTEM_PROMPT_V4 = txt
    rng = random.Random(args.seed)
    P = panel(rng, args.schema, args.n)
    warm_up(args, P[0][1])
    print(f"{len(P)} calls to {args.model} @ {args.host} ({args.workers} workers) ...", flush=True)

    def ask(item):
        case, st = item
        try:
            g = gt.ask_ollama(args.host, args.model, st, 30)
        except Exception as e:  # noqa: BLE001
            g = None
        return case, (g.split()[0] if g else None)

    results = {}
    fails = 0
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for case, goal in ex.map(ask, P):
            if goal is None:
                fails += 1
                continue
            results.setdefault(case, {}).setdefault(goal, 0)
            results[case][goal] += 1

    def rate(case, goal):
        d = results.get(case, {}); n = sum(d.values())
        return (d.get(goal, 0) / n if n else float("nan")), n

    def top(case):
        d = results.get(case, {}); n = sum(d.values()) or 1
        return ", ".join(f"{g} {c/n:.2f}" for g, c in sorted(d.items(), key=lambda kv: -kv[1])[:3])

    print(f"\nfailures: {fails}")
    checks = [
        ("P(follow | social 9)", *rate("social9", "follow_friend"), ">= 0.40", lambda v: v >= 0.40),
        ("P(follow | social 1)", *rate("social1", "follow_friend"), "<= 0.05", lambda v: v <= 0.05),
        ("P(dart | bold 9, energetic)", *rate("bold9", "dart_play"), ">= 0.10", lambda v: v >= 0.10),
        ("P(dart | bold 1, energetic)", *rate("bold1", "dart_play"), "<= 0.03", lambda v: v <= 0.03),
        ("P(seek_food | starving)", *rate("starving", "seek_food"), ">= 0.95", lambda v: v >= 0.95),
        ("P(seek_food | lonely, not hungry)", *rate("lonely", "seek_food"), "<= 0.05", lambda v: v <= 0.05),
    ]
    if args.schema < 4:
        checks += [
            ("P(flee | shadow near, calm)", *rate("shadowcalm", "flee_shadow"), ">= 0.80", lambda v: v >= 0.80),
            ("P(flee | lonely, no shadow)", *rate("lonely", "flee_shadow"), "== 0", lambda v: v <= 0.02),
        ]
    else:
        checks += [
            ("P(bubbles again | bored 9, last bubbles)", *rate("bored9bub", "visit_bubbles"), "<= 0.15", lambda v: v <= 0.15),
            ("P(explore | bored 9, last bubbles)", *rate("bored9bub", "explore"), ">= 0.25", lambda v: v >= 0.25),
            ("P(follow again | bored 9, last follow)", *rate("bored9fol", "follow_friend"), "<= 0.15", lambda v: v <= 0.15),
            ("P(bubbles kept | bored 0, last bubbles)", *rate("bored0bub", "visit_bubbles"), ">= 0.40", lambda v: v >= 0.40),
            ("P(rest | night, bored 9, last rest)", *rate("nightbored", "rest"), ">= 0.70", lambda v: v >= 0.70),
            ("P(flee | any v4 case)", (sum(d.get("flee_shadow", 0) for d in results.values()) / max(1, sum(sum(d.values()) for d in results.values()))), sum(sum(d.values()) for d in results.values()), "== 0", lambda v: v <= 0.001),
        ]
    for name, v, n, want, ok in checks:
        print(f"  {'OK ' if ok(v) else 'BAD'}  {name:36s} = {v:.2f}  (n={n}, want {want})")
    # attractor check: no single goal should own the content fish
    d = results.get("content", {}); n = sum(d.values()) or 1
    mx = max(d.values()) / n if d else 0
    print(f"  {'OK ' if mx < 0.45 else 'BAD'}  {'max single goal | content':36s} = {mx:.2f}  (want < 0.45)   [{top('content')}]")
    if args.schema >= 3:
        print(f"       trust 9: [{top('trust9')}]\n       trust 0: [{top('trust0')}]")
    print("\n  per case:")
    for case in ("social9", "social1", "bold9", "bold1", "content", "shadowcalm", "lonely", "starving", "trust9", "trust0",
                 "bored9bub", "bored9fol", "bored0bub", "nightbored"):
        if case in results:
            print(f"    {case:10s} {top(case)}")


if __name__ == "__main__":
    main()
