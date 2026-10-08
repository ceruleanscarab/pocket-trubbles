# Trubbles State & Goal Schema — v1, FROZEN

**Status: FROZEN (approved 2026-10-08).** The tokenizer and all training data
depend on this exact encoding. Do not change field
order, vocabulary, or value ranges without bumping the version, regenerating every
trace, and retraining. `gen_traces.py` must implement this spec and stay in sync.

Derived from pocket-tank's schema v4 (`model/schema.md`), keeping its conventions:
one lowercase, space-delimited line in; one goal line out; a closed word-level
vocabulary.

---

## Habitat model

- **A side-view habitat pod with gravity.** Trubbles roll, hop, and pile up; they do
  not swim. The advisor is queried one Trubble at a time; the state line is
  egocentric to that Trubble.
- **Colony size:** 1 to 8 Trubbles.
- **6 zones:** a 3-wide × 2-tall grid, numbered left-to-right, top row first. The
  top row is ledges and shelves; the bottom row is the floor.

  ```
  1 2 3
  4 5 6
  ```

- **Distances** are bucketed: `none` / `near` / `mid` / `far`.
- **Directions** are clock positions `1`–`12` relative to the Trubble's facing
  (`12` = dead ahead, `6` = behind).
- **Drives and traits** are integers `0`–`9`, one short token each.

## State encoding (model input, one line)

Fixed field order. A sighting is `<key> <dist> <clock>`, or `<key> none` when absent.

```
zone <1-6> hunger <0-9> energy <0-9> stress <0-9> content <0-9>
curiosity <0-9> bored <0-9> crowd <0-9>
cuddly <0-9> bold <0-9> chatty <0-9> stage pip|tuft|fluff bond <0-9>
food <dist> <clock>|none friend <dist> <clock>|none pile <dist> <clock>|none
nook <dist> <clock>|none keeper near|away chorus on|off
last <goal> time day|night
```

(Line breaks above are for readability only; the real encoding is one line.)

Example:

```
zone 5 hunger 6 energy 5 stress 2 content 4 curiosity 3 bored 5 crowd 7 cuddly 8 bold 3 chatty 6 stage tuft bond 7 food mid 2 friend near 9 pile near 10 nook far 4 keeper away chorus off last nap time day
```

About 46 words per line.

### Field notes

**Drives** (change minute to minute):

- `hunger`: rises over time; falls when eating.
- `energy`: falls while active; restored by napping.
- `stress`: spikes on startles (three quick taps) and sustained crowding; decays
  in calm. High stress darkens and flattens the fur.
- `content`: rises with being fed, cuddling, strokes from the keeper, and calm;
  falls with hunger and stress. Sustained high content in a full fluff triggers
  budding (reflex/progression layer, not a goal).
- `curiosity`: rises over idle time and with nearby new objects.
- `bored`: how stale the current pastime is. Same rules as pocket-tank v4: rises
  while the same leisure goal continues; relieved by a different goal or by
  entering a zone not visited recently; eating and night naps never bore.
- `crowd`: local density plus colony size versus habitat capacity. High crowd
  makes cuddling less appealing and raises stress over time.

**Identity** (slow-changing):

- `cuddly`, `bold`, `chatty`: personality traits. Buds inherit a blend of the
  parent's traits with a little random drift.
- `stage`: `pip` (newly budded), `tuft` (half-grown), `fluff` (full grown; can bud).
- `bond`: the keeper relationship (reflex layer 0..10, clamped to one digit).
  Rises with strokes and calm holds; falls with startles.

**Surroundings:**

- `food`: nearest available food in the bin or on the floor.
- `friend`: the nearest other Trubble (`friend none` when alone).
- `pile`: the nearest pile of two or more cuddling Trubbles (`pile none` if none).
- `nook`: the sleeping nook.
- `keeper`: `near` if the keeper touched the glass or stroked a Trubble in the
  last few seconds; otherwise `away`.
- `chorus`: `on` if any Trubble within `mid` range is chirping.
- `last`: the Trubble's current goal (hysteresis signal).
- `time`: `day` or `night` (light on or off).

## Goal output (model output, one line)

```
<goal> urgency <0-9>
```

where `<goal>` ∈

```
eat     cuddle    roll    nap
explore greet_keeper hide chirp
```

Example: `cuddle urgency 6`

As in pocket-tank, each goal fuses intent and target; the reflex layer resolves
the concrete target (nearest food, nearest friend or pile, the nook, a ledge to
climb). Urgency scales speed and commitment. The on-device parser stays tolerant:
unknown goal → keep the previous goal; missing urgency → 5.

| Goal | Reflex layer behavior |
| --- | --- |
| `eat` | Roll to `food` and nibble |
| `cuddle` | Roll to `pile` if one is near, else to `friend`; snuggle and thrum |
| `roll` | Bounce and roll around for fun |
| `nap` | Go to the `nook` (or settle in place at night) and dim |
| `explore` | Hop up ledges, poke at objects, favor unvisited zones |
| `greet_keeper` | Come to the glass and chirp |
| `hide` | Tuck behind the nearest rock; fur flattens |
| `chirp` | Sing in place; may start or join a chorus |

## Vocabulary

Closed word-level lexicon, one token per whitespace word:

| Group | Words | Count |
| --- | --- | --- |
| Field keys | zone hunger energy stress content curiosity bored crowd cuddly bold chatty stage bond food friend pile nook keeper chorus last time urgency | 22 |
| Digits | 0 1 2 3 4 5 6 7 8 9 | 10 |
| Extra clock positions | 10 11 12 | 3 |
| Distances | none near mid far | 4 |
| Stages | pip tuft fluff | 3 |
| Keeper | away (`near` is shared with distances) | 1 |
| Chorus | on off | 2 |
| Time | day night | 2 |
| Goals | eat cuddle roll nap explore greet_keeper hide chirp | 8 |
| Separator | -> | 1 |
| **Total** | | **56** |

Plus the tokenizer's special tokens (BOS and any others `train_tokenizer.py`
adds), about 58 ids in all, close to pocket-tank's 54.

## Trace format (JSONL, one object per line)

```json
{"state": "zone 5 hunger 6 ... time day", "goal": "cuddle urgency 6"}
```

The teacher is queried with structured output constraining the reply to
`{"goal": <enum>, "urgency": 0-9}`, which `gen_traces.py` renders into the goal line.

Training serialization is unchanged from pocket-tank: each trace becomes
`<BOS>state -> goal`; at inference the prompt is `state ->` and the model
completes the goal.

## Teacher prompt guidance (not frozen; tune before the overnight run)

pocket-tank's lesson: the teacher prompt shapes the whole dataset, so keep its
rules few and spot-check a small batch first. Intended priorities:

1. High `hunger` → `eat`, whatever else is going on (except very high `stress`).
2. High `stress` → `hide`, especially for low `bold`.
3. `time night` or low `energy` → `nap`.
4. `keeper near` with high `bond` → `greet_keeper`; low `bond` may `hide` instead.
5. `chorus on` with high `chatty` → `chirp`.
6. High `crowd` → avoid `cuddle`; prefer `explore` or `nap`.
7. High `bored` → switch to something other than `last`.
8. Otherwise, personality decides: high `cuddly` → `cuddle`; high `curiosity` →
   `explore`; high `content` with low `bored` → `roll` or keep `last`.

## Decisions locked at approval

- [x] Drives: hunger, energy, stress, content, curiosity, bored, crowd (`stress`
      is new versus the design doc; it drives the scared mood color and `hide`).
- [x] Traits: cuddly, bold, chatty.
- [x] Stages: pip, tuft, fluff.
- [x] Zones: 6, as a 3×2 grid.
- [x] Sightings: food, friend, pile, nook. (Ledges and rocks are left to the
      reflex layer to keep the line short.)
- [x] `keeper near|away` and `chorus on|off` as two-state fields.
- [x] The 8 goals above.
