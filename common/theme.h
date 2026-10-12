/* theme.h - the words that change with the theme (2026-10-12).
 *
 * TH("trubble words", "cthulhu words") picks one at compile time: the
 * Trubbles' everywhere, the Cthulhu theme's in a THEME_CTHULHU build (the
 * Android app; `make CTHULHU=1` previews it in the sim). A plain string
 * literal either way, so it works in static tables and beside other literals.
 * Keep the second no longer than the first, or check where it is drawn.
 *
 * The Cthulhu theme's words: a Trubble is a SPAWN (the same, one or many),
 * the pod is R'LYEH, the stages are LARVA / YOUNG ONE / ELDER / OLD ONE, a
 * bud SPAWNS, moss is KELP, grime is SLIME; the fern KELP, the crates SUNKEN
 * RUINS, the glow fungus ELDER CORAL, the crystals GLYPH STONES, the crumb
 * mites PALE ISOPODS, the cleaning bot a GLASS SLUG, the mowing bot a KELP
 * CRAB. */
#ifndef THEME_H
#define THEME_H

#ifdef THEME_CTHULHU
#define TH(trubbles, cthulhu) cthulhu
#else
#define TH(trubbles, cthulhu) trubbles
#endif

#endif
