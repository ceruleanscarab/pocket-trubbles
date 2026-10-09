# The Trubbles model — runbook (prepared 2026-10-09; NOT yet run)

The first Trubbles brain: the same 14M-parameter student and 4-bit engine as
pocket-tank's fish, taught by the same teacher (gemma4:26b via Ollama), on
the Trubbles' own state line ([trubbles_schema.md](../model/trubbles_schema.md),
v1, frozen). Until it exists the pod runs on the rule stub (`common/advisor.c`)
and the sim refuses the fish model (it has no Trubble goal words).

What is new against the fish cycles (retrain-v4.md):

- **The states come from the C sim**, through the device's own encoder
  (`fishsim --dump-states`), not from a Python mini-sim kept in sync by hand.
  Real pods of 1-6 under the rule stub, run live, with re-rolled drives and
  injected keeper / chorus moments so the whole schema is covered.
- **Every line is checked** against the schema's grammar
  (`model/check_states.py`: field order, value domains, closed vocabulary,
  per-field coverage).
- **The fold drops impossible labels** - `eat` with `food none`, `cuddle`
  with `friend none` and `pile none` - and counts them: a teacher error rate.

Teacher: gemma4:26b on the Mac Mini (`http://192.168.0.139:11434`, shared -
ask first) or a local Ollama (`--host http://localhost:11434`).

## 0. Build and dry-run (no teacher, ~1 min)

```bash
cd sim && make && cd ..
./sim/fishsim --dump-states 60000 1 > model/out/trubbles_states_1.txt     # training states
./sim/fishsim --dump-states 2000 99 > model/out/trubbles_states_eval.txt  # held-out, for eval
python3 model/check_states.py model/out/trubbles_states_1.txt              # 0 bad; coverage per field
python3 model/train_tokenizer.py                                           # out/tokenizer_trubbles.bin, vocab 59
python3 model/gen_traces.py --states model/out/trubbles_states_1.txt --dry-run --count 5
```

The dump is deterministic for a seed; 60,000 lines take about a second.
Coverage at seed 1 (2026-10-09): pods 1-6 all well represented, night ~20%,
keeper near ~37%, chorus on ~12%, a pile in view ~20%, food in view ~57%;
hunger 7-9 ~16%, stress 6-9 ~18%, bored 7-9 ~15%.

## 1. Prompt check — the required gate (~10 min of teacher time)

```bash
python3 model/prompt_check.py --host http://192.168.0.139:11434 --workers 2 \
    | tee model/out/prompt_check_trubbles.log
```

~240 calls on pinned situations, one per teacher priority (starving, scared
and shy, night, the keeper with a strong / weak bond, a chorus, crowded,
alone, bored...), each with a threshold. **Do not start step 2 until it
prints PASS.** A BAD line means the prompt (`SYSTEM_PROMPT_TRUBBLES` in
`model/gen_traces.py` - the schema calls this part "not frozen; tune before
the overnight run") needs a sentence, not the data more volume. Try a
candidate prompt without editing the file: `--prompt-file cand.txt`.

## 2. Label overnight (~40,000 pairs)

Two workers on the same states file, each taking every other line:

```bash
python3 model/gen_traces.py --states model/out/trubbles_states_1.txt --count 20000 \
    --shard 0/2 --out model/out/trubbles_traces_a.jsonl --host http://192.168.0.139:11434 --max-minutes 600 &
python3 model/gen_traces.py --states model/out/trubbles_states_1.txt --count 20000 \
    --shard 1/2 --out model/out/trubbles_traces_b.jsonl --host http://192.168.0.139:11434 --max-minutes 600 &
```

A stopped run resumes: re-run the same command and the states already in its
`--out` are skipped.

## 3. Fold and check

```bash
python3 model/fold_traces.py model/out/trubbles_traces_*.jsonl --out model/out/trubbles_clean.jsonl
python3 model/check_states.py model/out/trubbles_clean.jsonl
```

Read the fold's goal distribution (any goal over 40% is flagged - pocket-tank's
v2 incident was one goal at 45%), the impossible-label count (should be a
handful at most) and "bored 7-9 that REPEAT last" (should be rare).

## 4. Train, export (as pipeline.md; the tokenizer is the Trubbles one)

```bash
.venv/bin/python model/train.py --data model/out/trubbles_clean.jsonl \
    --dim 384 --n-layers 8 --n-heads 8 --max-seq-len 64 --batch 64 --iters 4000 --lr 6e-4
.venv/bin/python model/llama2.c/export.py model/out/model.bin --checkpoint model/out/ckpt.pt
python3 model/export_q4.py                                       # -> model/out/model_q4.bin
```

(`POCKET_SCHEMA` now defaults to `trubbles`; a document is 44-50 tokens.)

## 5. Evaluate

```bash
cc -O3 -o model/runw model/runw.c -lm
python3 model/eval.py --states model/out/trubbles_states_eval.txt --count 100 --teacher \
    --model-bin model/out/model.bin --host http://192.168.0.139:11434
```

Agreement with the teacher on held-out states (the fish shipped at 72%,
against the teacher's 82% self-agreement).

## 6. Install

The sim loads `model/out/model_q4.bin` + `model/out/tokenizer.bin`; the
firmware embeds its own copy of the tokenizer (`firmware/main/tokenizer.bin`)
and has the model flashed to its partition. Both model files are tracked in
git (force-added past `model/out/*`), so these are ordinary changes to commit:

```bash
cp model/out/tokenizer_trubbles.bin model/out/tokenizer.bin    # (model_q4.bin is already in place from step 4)
cp model/out/tokenizer_trubbles.bin firmware/main/tokenizer.bin
cd sim && make && ./fishsim                                    # "advisor: schema v1" in the log
tools/flash.sh --model                                         # the board: app + model/out/model_q4.bin at 0x290000
```

Firmware and model go together: a board running the new firmware with the
old (fish) model in its partition simply runs the rule stub - the encoder
refuses a tokenizer without the Trubble goals - and vice versa.

Then put `--selftest-llm` back into `SELFTESTS` in `sim/Makefile` (it came
out when the fish model stopped loading) and run `make check-all`.
