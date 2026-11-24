/*
 * Persona 5: Dancing in Starlight (PCSE01275): the same code as P3D's (packs/PCSE01274/hooks.c): its hooks (runtime/build.py RECOMP_PACK_HOOKS), placed by pack.toml's IHOOKS=.
 */
#include "hooks.h"
#include <stdio.h>
#include <stdlib.h>
extern int display_frame_rate(void);

/* RECOMP_P5D_STEP30=1: the 1/30 s steps below left alone at 60/90/120 fps (the menus' own clock then runs fast) */
static int step_rate(void) { static int v = -1; if (v < 0) v = getenv("RECOMP_P5D_STEP30") == 0; return v ? display_frame_rate() : 30; }

/* a register just loaded with 1/30 s (0x3d088889, by its movw/movt): 1/60 s at 60 fps, 1/90 s at 90, 1/120 s at 120 -- the per-update steps of the
 * menus' and UI's timers (a time += 1/30, a frame count * 1/30), which assume one update per Vita frame */
void recomp_ihook_p5d_step30(Cpu *c, int reg) {
	int fr = step_rate();
	if (reg < 0 || reg > 14 || fr < 60 || c->r[reg] != 0x3d088889u) return;
	c->r[reg] = fr >= 120 ? 0x3c088889u : fr >= 90 ? 0x3c360b61u : 0x3c888889u;   /* 1/120, 1/90, 1/60 */
}
/* fn at 0x81049a16, "advance one frame": t = (max(int(t * 30), last) + 1) / 30 -- every update moves an animation at
 * least one 30 fps frame. At 60/90/120 fps the grid is 60/90/120: s0 (just set to 30.0) is the frame rate, and its 1/30 (p5d_step30) one frame of it */
void recomp_ihook_p5d_grid30(Cpu *c, int reg) {
	(void)reg;
	int fr = step_rate();
	if (fr >= 60 && c->vfp.f[0] == 30.0f) c->vfp.f[0] = (float)fr;
}
