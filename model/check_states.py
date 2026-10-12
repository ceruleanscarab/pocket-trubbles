#!/usr/bin/env python3
"""check_states.py - hold Trubbles state lines to model/trubbles_schema.md.

Every line must be the schema's exact grammar - the fixed field order, each
value from its own domain, every word in the closed vocabulary - and the
file's coverage is printed per field, so a thin corner of the space shows up
before the teacher's time is spent on it.

    ./sim/fishsim --dump-states 40000 1 > model/out/trubbles_states_1.txt
    python3 model/check_states.py model/out/trubbles_states_1.txt

Also takes trace JSONL ({"state": ..., "goal": ...}): then the goal line is
checked too and the label distribution printed. Stdlib only; exit 1 on any
bad line.
"""
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import train_tokenizer as tt
tt.set_schema("trubbles")

D9 = [str(i) for i in range(10)]
CLOCK = [str(i) for i in range(1, 13)]
DRIVES = ["hunger", "energy", "stress", "content", "curiosity", "bored", "crowd"]
TRAITS = ["cuddly", "bold", "chatty"]
GOALS = ["eat", "cuddle", "roll", "nap", "explore", "greet_keeper", "hide", "chirp"]


def parse_state(line):
    """the fields in order, or raise ValueError saying where the line breaks the schema"""
    w, i, out = line.split(), 0, collections.OrderedDict()

    def take(key, domain):
        nonlocal i
        if i + 1 >= len(w) or w[i] != key:
            raise ValueError(f"word {i}: want '{key}', got '{w[i] if i < len(w) else 'END'}'")
        if w[i + 1] not in domain:
            raise ValueError(f"{key}: '{w[i + 1]}' is not one of {domain}")
        out[key] = w[i + 1]
        i += 2

    def sighting(key):
        nonlocal i
        if i >= len(w) or w[i] != key:
            raise ValueError(f"word {i}: want '{key}'")
        if i + 1 < len(w) and w[i + 1] == "none":
            out[key] = "none"; i += 2; return
        if i + 2 >= len(w) or w[i + 1] not in ("near", "mid", "far") or w[i + 2] not in CLOCK:
            raise ValueError(f"{key}: want '<near|mid|far> <1-12>' or 'none'")
        out[key] = w[i + 1]; out[key + "_clock"] = w[i + 2]; i += 3

    take("zone", [str(z) for z in range(1, 7)])
    for k in DRIVES: take(k, D9)
    for k in TRAITS: take(k, D9)
    take("stage", ["pip", "tuft", "fluff"])
    take("bond", D9)
    for k in ("food", "friend", "pile", "nook"): sighting(k)
    take("keeper", ["near", "away"])
    take("chorus", ["on", "off"])
    take("last", GOALS)
    take("time", ["day", "night"])
    if i != len(w):
        raise ValueError(f"{len(w) - i} words past 'time'")
    unknown = [x for x in w if x not in tt._WORD_TO_ID]
    if unknown:
        raise ValueError(f"not in the vocabulary: {unknown}")
    return out


def parse_goal(g):
    w = g.split()
    if len(w) != 3 or w[0] not in GOALS or w[1] != "urgency" or w[2] not in D9:
        raise ValueError(f"goal line '{g}' is not '<goal> urgency <0-9>'")
    return w[0], int(w[2])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cov = collections.defaultdict(collections.Counter)
    labels, urg = collections.Counter(), collections.Counter()
    n = bad = 0
    lengths = collections.Counter()
    for path in sys.argv[1:]:
        for ln, raw in enumerate(open(path), 1):
            raw = raw.strip()
            if not raw:
                continue
            n += 1
            try:
                if raw.startswith("{"):
                    o = json.loads(raw)
                    f = parse_state(o["state"])
                    g, u = parse_goal(o["goal"])
                    labels[g] += 1; urg[u] += 1
                    lengths[len(tt.encode_doc(o["state"], o["goal"]))] += 1
                else:
                    f = parse_state(raw)
                    lengths[len(tt.encode(raw, bos=True)) + 1] += 1
            except ValueError as e:
                bad += 1
                if bad <= 10:
                    print(f"{path}:{ln}: {e}")
                continue
            for k, v in f.items():
                cov[k][v] += 1
    print(f"{n} lines, {bad} bad; tokens per document {min(lengths)}..{max(lengths)}" if lengths else f"{n} lines, {bad} bad")
    for k in ["zone"] + DRIVES + TRAITS + ["stage", "bond", "food", "friend", "pile", "nook", "keeper", "chorus", "last", "time"]:
        c = cov[k]
        if not c:
            continue
        keys = sorted(c, key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else v))
        print(f"  {k:9s} " + "  ".join(f"{v}:{100 * c[v] / n:.0f}%" for v in keys))
    if labels:
        print("labels   " + "  ".join(f"{g}:{100 * labels[g] / n:.0f}%" for g in GOALS))
        print("urgency  " + "  ".join(f"{u}:{100 * urg[u] / n:.0f}%" for u in range(10)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
