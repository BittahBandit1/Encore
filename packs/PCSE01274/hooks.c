/*
 * Persona 3: Dancing in Moonlight (PCSE01274): its hooks (runtime/build.py RECOMP_PACK_HOOKS), placed by pack.toml's IHOOKS=.
 */
#include "hooks.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int display_frame_rate(void);

/* RECOMP_P3D_STEP30=1: the 1/30 s steps below left alone at 60/120 fps (the menus' own clock then runs fast) */
static int step_rate(void) { static int v = -1; if (v < 0) v = getenv("RECOMP_P3D_STEP30") == 0; return v ? display_frame_rate() : 30; }

/* a register just loaded with 1/30 s (0x3d088889, by its movw/movt): 1/60 s at 60 fps, 1/120 s at 120 fps -- the per-update steps of the
 * menus' and UI's timers (a time += 1/30, a frame count * 1/30), which assume one update per Vita frame */
void recomp_ihook_p3d_step30(Cpu *c, int reg) {
	int fr = step_rate();
	if (reg < 0 || reg > 14 || fr < 60 || c->r[reg] != 0x3d088889u) return;
	c->r[reg] = fr >= 120 ? 0x3c088889u : 0x3c888889u;
}
/* fn at 0x81046f9a, "advance one frame": t = (max(int(t * 30), last) + 1) / 30 -- every update moves an animation at
 * least one 30 fps frame. At 60/120 fps the grid is 60/120: s0 (just set to 30.0) is 60.0/120.0, and its 1/30 (p3d_step30) 1/60 or 1/120 */
void recomp_ihook_p3d_grid30(Cpu *c, int reg) {
	(void)reg;
	int fr = step_rate();
	if (fr >= 60 && c->vfp.f[0] == 30.0f) c->vfp.f[0] = (float)fr;
}

/* Keep P3D's two 2D frame-rate managers in sync with 30 / 60 / 120 fps (live-switchable):
 *   1. FrameRateMgr *(0x8132fe64): +8 is the target FPS enum (1=30, 2=60, 3=90, 4=120), used by 792
 *      calls to fn_8102ab9c (2D UI/menu/gameplay frame-count conversion) and fn_8102abfc/acb6.
 *   2. 2D keyframe evaluator *(0x813caaec): +0 is current FPS (30/60/120), +4 is authored FPS (30),
 *      used by fn_81154b98 to scale 2D keyframe curves by (authored / current). */
static void p3d_sync_2d_fps(void) {
	int fr = display_frame_rate();
	uint32_t enm = fr >= 120 ? 4u : fr >= 60 ? 2u : 1u;
	uint32_t mgr = RD32(0x8132fe64u);
	if (mgr >= 0x10000000u && mgr < 0x80000000u && RD32(mgr + 8u) != enm) WR32(mgr + 8u, enm);
	uint32_t kf = RD32(0x813caaec);
	if (kf >= 0x10000000u && kf < 0x80000000u && RD32(kf) != (uint32_t)fr) WR32(kf, (uint32_t)fr);
}
/* RECOMP_P3D_TIMING=1: gfd's frame globals (0x816e7a50: +4/+8 floats, +0xc, +0x2c the fps) for 8 presented frames in a row
 * every 2 s -- whether the engine's step advances each presented frame or only every few */
static void p3d_timing(void) {
	static int on = -1; if (on < 0) on = getenv("RECOMP_P3D_TIMING") != 0;
	if (!on) return;
	static unsigned n; unsigned k = n++ % 240;
	if (k >= 8) return;
	uint32_t g = 0x816e7a50u, a = RD32(g + 4), b = RD32(g + 8);
	float fa, fb; memcpy(&fa, &a, 4); memcpy(&fb, &b, 4);
	fprintf(stderr, "    p3d timing: frame %u: +4 %.6f +8 %.6f +0xc %u +0x2c %u\n", n, fa, fb, RD32(g + 0xc), RD32(g + 0x2c));
}
static void p3d_on_frame(void) { p3d_sync_2d_fps(); p3d_timing(); }
__attribute__((constructor)) static void p3d_hooks_init(void) { hook_on_frame = p3d_on_frame; }
