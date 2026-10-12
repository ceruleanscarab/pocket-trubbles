#!/usr/bin/env python3
"""Word-level tokenizer for the pocket-tank advisor. Stdlib only.

The schema (schema.md, FROZEN v2) is a closed vocabulary of whitespace-delimited
words, so one token per word is the natural encoding: a v2 state line is ~44
tokens instead of ~190 char-level tokens - a ~4x cut in per-decision latency,
which is what makes the ESP32's 1-3s advisor cadence feasible.

Vocab layout (llama2.c tokenizer.bin format, readable by run.c's decode()):
  id 0 <unk>   id 1 BOS ("\n<s>\n")   id 2 EOS ("\n</s>\n")
  id 3.. one token per lexicon word, stored WITH a leading space so decoded
         token streams read as normal text ("seek_food urgency 8").

Encoding is a plain split-and-lookup (encode()); run.c's BPE encoder is NOT
used - sim/advisor_llm.c and model/runw.c carry the same lookup in C, and the
firmware will too (simpler than BPE). Training doc: <BOS> state -> goal.

Usage: python3 train_tokenizer.py                     # the Trubbles schema (model/trubbles_schema.md):
                                                      # out/tokenizer_trubbles.bin, vocab 59
       python3 train_tokenizer.py --schema 2 [--out out/tokenizer.bin] [--verify out/v2_clean.jsonl]
       python3 train_tokenizer.py --schema 3          # out/tokenizer_v3.bin (no names, + trust)
       python3 train_tokenizer.py --schema 4          # out/tokenizer_v4.bin (no shadow, + bored)
The schema is chosen by --schema, or by the POCKET_SCHEMA environment variable
when imported (train.py / probe_dist.py): POCKET_SCHEMA=3 python train.py ...
The default (2026-10-09) is `trubbles`; 2 / 3 / 4 are pocket-tank's fish lines.
"""

import argparse
import glob
import json
import os
import struct

BOS_ID, EOS_ID, UNK_ID = 1, 2, 0
SEP = " -> "

SCHEMA = os.environ.get("POCKET_SCHEMA", "trubbles")
SCHEMA = int(SCHEMA) if SCHEMA.isdigit() else SCHEMA

# the Trubbles lexicon (model/trubbles_schema.md v1, FROZEN): the schema's
# vocabulary table in its order - field keys, digits, the extra clock hours,
# distances, stages, keeper, chorus, time, the goals, the separator. 56 words
# + the 3 specials = vocab 59. The order fixes the token ids: never reorder.
TRUBBLES_LEXICON = (
    ["zone", "hunger", "energy", "stress", "content", "curiosity", "bored", "crowd",
     "cuddly", "bold", "chatty", "stage", "bond", "food", "friend", "pile", "nook",
     "keeper", "chorus", "last", "time", "urgency"]
    + [str(i) for i in range(0, 10)] + ["10", "11", "12"]
    + ["none", "near", "mid", "far"]
    + ["pip", "tuft", "fluff"]
    + ["away"] + ["on", "off"] + ["day", "night"]
    + ["eat", "cuddle", "roll", "nap", "explore", "greet_keeper", "hide", "chirp"]
    + ["->"])
assert len(TRUBBLES_LEXICON) == 56 and len(set(TRUBBLES_LEXICON)) == 56


def lexicon_for(schema):
    if schema == "trubbles":
        return TRUBBLES_LEXICON
    head = (["fish", "mira", "bolt", "kelp", "nori", "zone"] if schema == 2
            else ["zone"])                                   # v3: names carry no signal - dropped
    ident = (["hunger", "energy", "stress", "curiosity", "bold", "social", "stage",
              "fry", "juv", "adult", "elder"] + (["trust"] if schema >= 3 else [])
             + (["bored"] if schema >= 4 else []))
    # v4: the shadow field is gone (the predator left the game 2026-09-13).
    # `flee_shadow` STAYS in the lexicon - it is never a v4 label, so the
    # student learns ~0 probability for it - because common/tank.c keeps
    # GOAL_FLEE_SHADOW in its enum and advisor_core_init wants a token id for
    # every goal. One unused embedding row is cheaper than a C special case.
    return (head + ident
            + ["food"] + (["shadow"] if schema < 4 else []) + ["friend", "bubble", "reef", "wall",
               "none", "near", "mid", "far", "clear",
               "last", "time", "day", "night"]
            + [str(i) for i in range(0, 13)]                 # drives 0-9, clock 1-12
            + ["seek_food", "flee_shadow", "visit_bubbles", "follow_friend",
               "explore", "rest", "dart_play", "inspect_reef",
               "urgency", "->"])


def set_schema(schema):
    """switch the module's lexicon (v2: vocab 58, v3/v4: 54, trubbles: 59)"""
    global SCHEMA, LEXICON, VOCAB, VOCAB_SIZE, _WORD_TO_ID
    SCHEMA = schema
    LEXICON = lexicon_for(schema)
    VOCAB = ["<unk>", "\n<s>\n", "\n</s>\n"] + [" " + w for w in LEXICON]
    VOCAB_SIZE = len(VOCAB)
    _WORD_TO_ID = {w: 3 + i for i, w in enumerate(LEXICON)}


set_schema(SCHEMA)


def encode(text, bos=False):
    ids = [BOS_ID] if bos else []
    for w in text.split():
        ids.append(_WORD_TO_ID.get(w, UNK_ID))
    return ids


def encode_doc(state, goal):
    return encode(state + SEP + goal, bos=True)


def decode(ids):
    return "".join(VOCAB[i] for i in ids).strip()


def write_bin(path):
    with open(path, "wb") as f:
        f.write(struct.pack("<i", max(len(v.encode()) for v in VOCAB)))
        for v in VOCAB:
            b = v.encode("utf-8")
            f.write(struct.pack("<fi", 0.0, len(b)))
            f.write(b)


def verify(paths):
    """Every word in every trace must be in the lexicon (closed vocabulary)."""
    bad, n = {}, 0
    for path in paths:
        with open(path) as fh:
            for line in fh:
                o = json.loads(line); n += 1
                for w in (o["state"] + SEP + o["goal"]).split():
                    if w not in _WORD_TO_ID:
                        bad[w] = bad.get(w, 0) + 1
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--schema", type=lambda v: int(v) if v.isdigit() else v, choices=(2, 3, 4, "trubbles"), default=SCHEMA)
    ap.add_argument("--out", default=None)
    ap.add_argument("--verify", default=None)
    args = ap.parse_args()
    set_schema(args.schema)
    if args.out is None:
        args.out = os.path.join(here, "out", "tokenizer.bin" if args.schema == 2 else
                                "tokenizer_trubbles.bin" if args.schema == "trubbles" else f"tokenizer_v{args.schema}.bin")
    if args.verify is None:
        args.verify = os.path.join(here, "out", "trubbles_traces*.jsonl" if args.schema == "trubbles" else f"v{args.schema}_traces*.jsonl")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_bin(args.out)
    sample = ("fish mira zone 2 hunger 7 -> seek_food urgency 8" if args.schema == 2
              else "zone 5 hunger 6 crowd 7 stage tuft keeper away chorus off -> cuddle urgency 6" if args.schema == "trubbles"
              else "zone 2 hunger 7 trust 5 -> seek_food urgency 8")
    assert decode(encode(sample)) == sample, "round-trip failed"
    print(f"wrote {args.out}: schema {args.schema}, vocab_size={VOCAB_SIZE}, sample = {len(encode(sample, bos=True))} tokens")
    n, bad = verify(glob.glob(args.verify))
    print(f"verified {n} traces: {'closed vocabulary OK' if not bad else 'UNKNOWN WORDS ' + str(bad)}")


if __name__ == "__main__":
    main()
