# The Trubbles model — runbook (prepared 2026-10-09; first run 2026-10-09..11)

The first Trubbles brain: the same 14M-parameter student and 4-bit engine as
pocket-tank's fish, taught by the same teacher (gemma4:26b via Ollama), on
the Trubbles' own state line ([trubbles_schema.md](../model/trubbles_schema.md),
v1, frozen). Before it existed the pod ran on the rule stub (`common/advisor.c`)
and the sim refused the fish model (it has no Trubble goal words).

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

## The first run (2026-10-09..11) at a glance

On the keeper's Windows laptop (WSL2, Ollama on the Windows side, no GPU that
torch can use):

| Step | Result |
| --- | --- |
| 1. Prompt check | PASS on the 4th candidate prompt (17/17), now `SYSTEM_PROMPT_TRUBBLES` (bbde65e) |
| 2. Label | 40,202 pairs in ~31 h of wall time (~13 h of it a stall while the PC slept) |
| 3. Fold | 40,054 clean; 5 impossible labels; top goal nap 31.5%; bored 7-9 repeats 25% (mostly night naps, ~4-7% real misses) |
| 4. Train | CPU, 4,000 iters in ~2 h, best val_loss 0.7406; model_q4.bin 7.56 MB |
| 5. Eval | 84/100 agree with the teacher, 100/100 valid |
| 6. Install | sim + `make check-all` 36/36 (0d1f181); version.h model constants (5175287) |

Lessons folded into the steps below are marked **(2026-10-11)**.

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

To move a run to another machine, copy the states file - do not regenerate it
there: the resume (step 2) matches states by their text.

## 1. Prompt check — the required gate (~10 min of teacher time)

```bash
python3 model/prompt_check.py --host http://192.168.0.139:11434 --workers 2 \
    | tee model/out/prompt_check_trubbles.log
```

~300 calls on pinned situations, one per teacher priority (starving, scared
and shy, night, the keeper with a strong / weak bond, a chorus, crowded,
alone, bored...), each with a threshold. **Do not start step 2 until it
prints PASS.** A BAD line means the prompt (`SYSTEM_PROMPT_TRUBBLES` in
`model/gen_traces.py` - the schema calls this part "not frozen; tune before
the overnight run") needs a sentence, not the data more volume. Try a
candidate prompt without editing the file: `--prompt-file cand.txt`.

**(2026-10-11)** Things that cost the first run time:

- **`num_ctx` must hold the whole prompt.** The Trubbles system prompt is
  ~950 tokens with the state line; at the old `num_ctx: 512` Ollama silently
  truncated it (`prompt_eval_count` 455) and the check measured a cut prompt.
  `ask_ollama` now sends 2048 (8977b90). If the prompt grows, check
  `prompt_eval_count` on one call.
- **A cold teacher fails the first calls.** gemma4:26b took 735 s to load on
  the laptop; the panel's 30 s timeout counted those calls as failures. The
  check now sends one warm-up call first (09702d5).
- **n=20 per case is noisy**: one answer moves a rate by 0.05. A threshold
  passed exactly at its limit (keeper_wary 0.20) is a pass by one answer.
- What the four candidates taught: stronger wording did not stop a bored
  explorer exploring - the prompt's own definition of `explore` ("visit parts
  of the pod it has not seen lately") made exploring look like the cure for
  boredom until it said so outright; and every nudge away from one goal pushed
  the share onto another (nap rose when explore fell). Re-run the whole panel
  after each edit.

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

**(2026-10-11)**

- **`--count` is NEW pairs for this run**, not the file's total. A resumed
  shard with 4,870 pairs already in its file and `--count 20000` goes on to
  ~24,870. When resuming, pass the number still missing.
- **Size `--max-minutes` to the machine.** The laptop did ~2,000-4,000 pairs an
  hour (both shards together), so 40,000 is 10-20 h, not 10; the 600 above is
  for the Mac Mini.
- **Keep the teacher's machine awake.** The first run lost ~13 h overnight to
  a sleeping PC (486 pairs between 17:02 and 06:28). Run detached
  (`nohup setsid ... &`) so a closed terminal does not stop it.
- **`OLLAMA_NUM_PARALLEL=2` did not help on the laptop's GPU**: queueing fell
  from ~2 s to ~0.7 s per call but generation slowed 3x, so throughput stayed
  the same. Measure before assuming it helps on another machine.
- Watch progress with `wc -l model/out/trubbles_traces_*.jsonl`; judge the
  rate over half an hour or more - 90-second samples swung from 1,900 to
  4,400 an hour.

## 3. Fold and check

```bash
python3 model/fold_traces.py model/out/trubbles_traces_*.jsonl --out model/out/trubbles_clean.jsonl
python3 model/check_states.py model/out/trubbles_clean.jsonl
```

Read the fold's goal distribution (any goal over 40% is flagged - pocket-tank's
v2 incident was one goal at 45%), the impossible-label count (should be a
handful at most) and "bored 7-9 that REPEAT last" (should be rare).

**(2026-10-11)** The REPEAT count includes repeats a higher priority demands
(a bored Trubble at night still naps; a starving one still eats). The first
run's 1,511 of 6,070 (25%) broke down as 838 night / low-energy naps, ~300
hunger / stress / keeper / chorus, and ~260-400 (4-7%) real rule-7 misses.
Break it down before relabelling.

## 4. Train, export (as pipeline.md; the tokenizer is the Trubbles one)

One-time setup **(2026-10-11)** - neither is in git:

```bash
python3 -m venv .venv
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch   # CPU build; plain `torch` for CUDA
.venv/bin/pip install numpy
git clone https://github.com/karpathy/llama2.c model/llama2.c
```

```bash
.venv/bin/python model/train.py --data model/out/trubbles_clean.jsonl \
    --dim 384 --n-layers 8 --n-heads 8 --max-seq-len 64 --batch 64 --iters 4000 --lr 6e-4
.venv/bin/python model/llama2.c/export.py model/out/model.bin --checkpoint model/out/ckpt.pt
.venv/bin/python model/export_q4.py model/out/model_q4.bin --checkpoint model/out/ckpt.pt   # -> 4-bit, ~7.56 MB
```

(`POCKET_SCHEMA` now defaults to `trubbles`; a document is 44-51 tokens.)

`train.py` picks MPS, then CUDA, then CPU. On the laptop's CPU an iteration
took 0.9-1.9 s (it slowed as the machine warmed), ~2 h for 4,000. val_loss
went 0.805 (iter 200) -> 0.751 (2,000) -> 0.7406 (4,000), still creeping down
at the end.

## 5. Evaluate

```bash
cc -O3 -o model/runw model/runw.c -lm
python3 model/eval.py --states model/out/trubbles_states_eval.txt --count 100 --teacher \
    --model-bin model/out/model.bin --host http://192.168.0.139:11434
```

Agreement with the teacher on held-out states (the fish shipped at 72%,
against the teacher's 82% self-agreement). The first Trubbles model: **84%**.
`eval.py` swaps in `tokenizer_trubbles.bin` itself; its teacher calls time out
at 30 s, so warm the teacher first if it may be cold.

## 6. Install

The sim loads `model/out/model_q4.bin` + `model/out/tokenizer.bin`; the
firmware embeds its own copy of the tokenizer (`firmware/main/tokenizer.bin`)
and has the model flashed to its partition. Both model files are tracked in
git (force-added past `model/out/*`), so these are ordinary changes to commit:

```bash
cp model/out/tokenizer_trubbles.bin model/out/tokenizer.bin    # (model_q4.bin is already in place from step 4)
cp model/out/tokenizer_trubbles.bin firmware/main/tokenizer.bin
cd sim && make && make check-all && cd ..                      # "advisor: schema v1" in --selftest-llm's log
```

**Then the model constants (2026-10-11)** - `common/version.h` names the
model the firmware ships with, and `tools/model_trailer.py --check` refuses
the flash until they match the file:

```bash
sha256sum model/out/model_q4.bin; stat -c%s model/out/model_q4.bin
# -> PT_MODEL_TAG (<= 15 chars, e.g. trubbles1), PT_MODEL_LEN, PT_MODEL_SHA256 in common/version.h
```

Then flash (`--model` writes the model at 0x290000, its trailer at 0xA8F000,
then the signed app):

```bash
bash tools/flash.sh --model
```

Firmware and model go together: a board running the new firmware with the
old (fish) model in its partition simply runs the rule stub - the encoder
refuses a tokenizer without the Trubble goals - and vice versa.

(`--selftest-llm` is back in `SELFTESTS` in `sim/Makefile` since 0d1f181.)

### Flashing from Windows / WSL (2026-10-11)

`flash.sh` (efcd0a2) finds the board at `/dev/ttyACM*` as well as macOS's
`/dev/cu.usbmodem*`. What else WSL needs:

- **ESP-IDF v5.4**, at `~/esp/esp-idf` (`flash.sh` looks there first, then
  `~/esp/esp-idf-v*`, or set `IDF_EXPORT`). **v6 does not build the
  firmware** (`mbedtls/sha256.h` gone, `async_memcpy_config_t` fields renamed,
  FreeRTOS includes); a half-started v6 port (json -> cjson) is in a stash.
  ```bash
  git clone -b v5.4.2 --depth 1 --recursive --shallow-submodules \
      https://github.com/espressif/esp-idf.git ~/esp/esp-idf
  ~/esp/esp-idf/install.sh esp32s3
  ```
- **The OTA signing key** at `firmware/keys/ota_signing_key.pem` (not in git;
  `tools/ota_key.sh`). A board only takes over-the-air updates signed with the
  key its running image was signed with. 2026-10-11: the original key was not
  on the laptop and a NEW key was made there (digest `9d33...e5b6`); boards
  flashed with it refuse releases signed with the old one (the CI secret
  `OTA_SIGNING_KEY`) until re-flashed by cable or the secret is replaced.
- **USB into WSL** with usbipd-win, in an administrator PowerShell
  (`winget install --exact dorssel.usbipd-win`, then a NEW PowerShell window):
  ```
  usbipd list                                  # the board: 303a:1001 "USB JTAG/serial debug unit"
  usbipd bind --busid <BUSID>                  # --force if it warns about a USB filter (e.g. ESET's edevmon)
  usbipd attach --wsl --busid <BUSID>          # --auto-attach to survive replugs and resets
  ```
- **Port permissions**: `/dev/ttyACM0` is `root:dialout`. Once:
  `wsl -u root usermod -aG dialout <user>` (takes effect after `wsl --shutdown`);
  until then, after each attach: `wsl -u root chmod a+rw /dev/ttyACM0`.
- **Preflight needs the tank running.** It archives the battery log from the
  running firmware and refuses a silent board. A board stuck in download mode
  (esptool connects with `--before no_reset`) has its GPIO0 / BOOT held low:
  `esptool ... --no-stub read_mem 0x60004038` reads the strapping pins, and
  bit 3 = 0 means download boot (`soc/esp32s3/include/soc/boot_mode.h`).
- **Large reads over usbipd corrupt** (`read_flash` of 16 MB failed twice with
  "Corrupt data"); 256 KB chunks with retries worked at ~23 s each. Writes are
  hash-verified by esptool and were fine.
