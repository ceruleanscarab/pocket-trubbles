/* advisor.c — rule-based advisor stub for the Trubbles (2026-10-08).
 *
 * The schema's teacher priorities (model/trubbles_schema.md, "Teacher prompt
 * guidance") as plain rules, so every goal has a situation that calls for
 * it until a Trubbles model is trained. Synchronous: it answers on request. */
#include "advisor.h"

/* stateless PRNG: advisor must not mutate the tank */
static float frand(const tank_t *t, int fish_idx) {
    uint32_t x = t->rng ^ (0x9E3779B9u * (uint32_t)(fish_idx + 1))
                        ^ (uint32_t)(t->clock * 977.0f);
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return (float)(x & 0xffffff) / 16777215.0f;
}

static goal_t pick(goal_id_t id, float urgency) {
    goal_t g = { id, urgency, 1.0f, GOAL_COUNT };     /* rules are never torn */
    return g;
}

goal_t advisor_rules(const tank_t *t, int fish_idx, bool request) {
    const fish_t *f = &t->fish[fish_idx];
    if (!request) return f->goal;            /* rules are synchronous: polls no-op */
    bool food = tank_nearest_food(t, f, 0) >= 0;
    float friend_d;
    bool friend = tank_nearest_friend(t, fish_idx, &friend_d) >= 0;
    bool keeper = tank_keeper_near(t), chorus = tank_chorus(t, fish_idx);
    float bold = f->bold * 9, cuddly = f->sociable * 9, chatty = f->chatty * 9;
    float r = frand(t, fish_idx);
    goal_id_t last = f->goal.id;

    /* how frightened is too frightened: a shy one hides sooner (bold 9: at
     * stress 6.5, bold 0: at 2.9 - a startle, +4.5, sends the shy half in) */
    float fright = 6.5f - (9 - bold) * 0.4f;
    /* hysteresis: a fresh goal is kept a moment - unless it is an emergency */
    bool emergency = (f->stress >= fright && last != GOAL_HIDE) || (f->hunger > 8 && food && last != GOAL_EAT);
    if (f->goal_age < 2.5f && !emergency) return f->goal;

    /* 1. hungry -> eat, whatever else is going on (except real fright).
     *    No food in the pod: ask the keeper for some, if it trusts them. */
    if (f->hunger >= 7 && f->stress < 8) {
        if (food) return pick(GOAL_EAT, f->hunger > 8.5f ? 9 : 6);
        if (f->trust >= 4 && last != GOAL_GREET_KEEPER) return pick(GOAL_GREET_KEEPER, 6);
        if (f->trust >= 4) return f->goal;
    }
    /* 2. stressed -> hide */
    if (f->stress >= fright) return pick(GOAL_HIDE, f->stress > 8 ? 9 : 6);
    /* 3. night or worn out -> nap */
    if (t->night || f->energy < 2.5f) return pick(GOAL_NAP, f->energy < 1.5f ? 7 : 4);
    /* 4. the keeper is here: a trusting Trubble comes to say hello, a wary one hides */
    if (keeper && f->trust >= 6 && last != GOAL_GREET_KEEPER && r < 0.7f) return pick(GOAL_GREET_KEEPER, 5);
    if (keeper && f->trust < 3) return pick(GOAL_HIDE, 4);
    /* 5. a chorus going and a chatty Trubble joins in */
    if (chorus && chatty >= 5 && last != GOAL_CHIRP) return pick(GOAL_CHIRP, 4);
    /* 6. crowded -> away from the others, never into a cuddle */
    bool crowded = f->crowd >= 6;
    if (crowded && last == GOAL_CUDDLE) return pick(r < 0.5f ? GOAL_EXPLORE : GOAL_NAP, 4);
    /* 7. bored -> anything but the current pastime */
    bool bored = f->bored >= 7;
    /* 8. otherwise personality decides: an ordered wish list, the first
     *    that fits (and, when bored, is not the current goal) wins */
    goal_id_t wish[7]; int n = 0;
    if (food && f->hunger >= 4) wish[n++] = GOAL_EAT;   /* peckish, and there it is: the keeper's pellets get eaten */
    if (cuddly >= 6 && friend && !crowded && r < 0.5f) wish[n++] = GOAL_CUDDLE;
    if (f->curiosity >= 6) wish[n++] = GOAL_EXPLORE;
    if (f->content >= 6 && f->bored < 4 && f->energy > 4) wish[n++] = r < 0.5f ? GOAL_ROLL : last;
    if (chatty >= 6 && r < 0.35f) wish[n++] = GOAL_CHIRP;
    if (f->energy > 6 && bold >= 5 && r < 0.4f) wish[n++] = GOAL_ROLL;
    wish[n++] = r < 0.3f ? GOAL_ROLL : r < 0.45f ? GOAL_CHIRP : GOAL_EXPLORE;   /* the default pastimes */
    for (int i = 0; i < n; i++) {
        if (bored && wish[i] == last) continue;
        if (!bored && i == n - 1 && f->goal_age < 8.0f) return f->goal;   /* nothing pressing: carry on a while */
        return pick(wish[i], wish[i] == GOAL_ROLL ? 5 : 3);
    }
    return pick(last == GOAL_EXPLORE ? GOAL_ROLL : GOAL_EXPLORE, 3);   /* bored of the default */
}
