/*
 * Persona 3: Dancing in Moonlight (PCSE01274): its hooks (runtime/build.py RECOMP_PACK_HOOKS), placed by pack.toml's IHOOKS=.
 */
#include "hooks.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
extern int display_frame_rate(void);

/* RECOMP_P3D_STEP30=1: the 1/30 s steps below left alone at 60/90/120 fps (the menus' own clock then runs fast) */
static int step_rate(void) { static int v = -1; if (v < 0) v = getenv("RECOMP_P3D_STEP30") == 0; return v ? display_frame_rate() : 30; }

/* a register just loaded with 1/30 s (0x3d088889, by its movw/movt): 1/60 s at 60 fps, 1/90 s at 90, 1/120 s at 120 -- the per-update steps of the
 * menus' and UI's timers (a time += 1/30, a frame count * 1/30), which assume one update per Vita frame */
void recomp_ihook_p3d_step30(Cpu *c, int reg) {
	int fr = step_rate();
	if (reg < 0 || reg > 14 || fr < 60 || c->r[reg] != 0x3d088889u) return;
	c->r[reg] = fr >= 120 ? 0x3c088889u : fr >= 90 ? 0x3c360b61u : 0x3c888889u;   /* 1/120, 1/90, 1/60 */
}
/* fn at 0x81046f9a, "advance one frame": t = (max(int(t * 30), last) + 1) / 30 -- every update moves an animation at
 * least one 30 fps frame. At 60/90/120 fps the grid is 60/90/120: s0 (just set to 30.0) is the frame rate, and its 1/30 (p3d_step30) one frame of it */
void recomp_ihook_p3d_grid30(Cpu *c, int reg) {
	(void)reg;
	int fr = step_rate();
	if (fr >= 60 && c->vfp.f[0] == 30.0f) c->vfp.f[0] = (float)fr;
}

/* the dance scene's update (fn around 0x81045800), given the song time T (s0) and the frame's step dt (*(r4), and *(r4+4) a second
 * one): it hands the dancers, partners and camera (the calls through +0x21c/+0x220/+0x228) whole 30 fps frames,
 * (int(T * 30) + int(dt * 30)) / 30. On the Vita that loses nothing; at 60/90/120 two or more presented frames get the same
 * time and the dancers hold each pose for them (the 3D stepping at 30 while the HUD, which reads the time itself, runs
 * smooth). p3d_dance_t30 (after 0x81045822, s0 = T * 30) keeps the fraction int() is about to drop; p3d_dance_time (after
 * 0x81045874, s16 and s0 the two frame counts as floats, before the divide) puts both fractions back: (T + dt) * 30.
 * The event cues (0x810458b6) take their own int(T * 30) and are untouched. */
static float dance_t30_frac, dance_t30_raw;
void recomp_ihook_p3d_dance_t30(Cpu *c, int reg) {
	(void)reg;
	float f = c->vfp.f[0]; dance_t30_raw = f;
	dance_t30_frac = (f > 0.0f && f < 1e7f) ? f - (float)(int)f : 0.0f;
}
void recomp_ihook_p3d_dance_time(Cpu *c, int reg) {
	(void)reg;
	extern void display_mark_gameplay(void); display_mark_gameplay();   /* a song is being played: no movie 30 fps (its video songs) */
	if (step_rate() < 60) return;
	uint32_t a = RD32(c->r[4]), b = RD32(c->r[4] + 4);
	float d0, d1; memcpy(&d0, &a, 4); memcpy(&d1, &b, 4);
	d0 *= 30.0f; d1 *= 30.0f;
	if (!(d0 >= 0.0f && d0 < 1e4f && d1 >= 0.0f && d1 < 1e4f)) return;
	/* s16 = offset + int(dt * 30), s0 = offset + int(dt * 30) + int(dt2 * 30) (0x81045860/66): s0 carries the first step too, so
	 * it gets both fractions -- s16's time poses the main dancers (+0x230, +0x238), s0's the partners and backup dancers
	 * (+0x23c's twelve, +0x270, +0x26c): with only dt2's fraction (always 0) they stayed on whole 30 fps frames */
	float x0 = dance_t30_frac + (d0 - (float)(int)d0), x1 = x0 + (d1 - (float)(int)d1);
	if (getenv("RECOMP_P3D_TIMING") && d1 > 0.0f) { static unsigned m; if (m++ % 1800 < 12) fprintf(stderr, "    p3d dance time 2: call %u: d0 %.3f d1 %.3f -> s16 %.3f s0 %.3f, words at r4+8.. %#x %#x %#x\n", m, d0, d1, c->vfp.f[16] + x0, c->vfp.f[0] + x1, RD32(c->r[4] + 8), RD32(c->r[4] + 12), RD32(c->r[4] + 16)); }
	static unsigned calls; calls++;
	if (getenv("RECOMP_P3D_TIMING")) {   /* the host time between dance updates (one pose each): steady ~16.7 ms is 60 poses a second */
		struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts); uint64_t now = (uint64_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
		static uint64_t last, n, h[6]; static const unsigned edge[5] = {8000, 14000, 19500, 25000, 40000};
		if (last) { uint64_t d = now - last; int k = 0; while (k < 5 && d >= edge[k]) k++; h[k]++; n++; }
		last = now;
		if (n >= 600) { fprintf(stderr, "    p3d dance update spacing over %llu updates: <8 ms %llu, 8-14 %llu, 14-19.5 %llu, 19.5-25 %llu, 25-40 %llu, >40 %llu\n", (unsigned long long)n, (unsigned long long)h[0], (unsigned long long)h[1], (unsigned long long)h[2], (unsigned long long)h[3], (unsigned long long)h[4], (unsigned long long)h[5]); n = 0; memset(h, 0, sizeof h); }
	}
	c->vfp.f[16] += x0;
	c->vfp.f[0] += x1;
}

/* RECOMP_P3D_TIMING diagnostic: the dancers' blob shadow (danceShadow.c's draw, fn 0x8104638c) works out its alpha from the
 * bone's height over the floor and draws nothing when that is 0 or less (0x81046462). After 0x8104645a: r10 is that alpha. */
void recomp_ihook_p3d_shadow_alpha(Cpu *c, int reg) {
	(void)reg;
	static int on = -1; if (on < 0) on = getenv("RECOMP_P3D_TIMING") != 0;
	if (!on) return;
	static unsigned n, pos; n++; if ((int32_t)c->r[10] > 0) pos++;
	if (n <= 4 || n % 1200 == 0) { uint32_t b = c->r[5]; float f20, f40, s5 = c->vfp.f[5]; uint32_t x = RD32(b + 20), y = RD32(b + 40); memcpy(&f20, &x, 4); memcpy(&f40, &y, 4);
		fprintf(stderr, "    p3d shadow: call %u: alpha %d (%u of them > 0), bone height %.3f, base %.3f scale %.3f\n", n, (int32_t)c->r[10], pos, s5, f20, f40); }
}

/* ---- the aspect ratio setting (RECOMP_ASPECT_HOOK=1 in pack.toml): gfd's camera keeps its vertical field of view in degrees
 * at +0x180 and its aspect at +0x184, each set through a setter (0x811a51cc, 0x811a51ba) that also marks the camera changed
 * (+0x18c bit 0) for its projection to be rebuilt. After either store, both are rewritten from the game's own values: wider
 * (k): the aspect k times wider, the same vertical view (more at the sides); narrower (t): the same horizontal view and a
 * vertical one t times taller -- aspect / t, tan(fov / 2) * t. The game's values are kept per camera: a value read back from
 * the camera and set again (an animated field of view starting from the current one) is the effective one, recognised and
 * left as the game's, so nothing compounds. */
extern double aspect_widen(void);
extern float window_aspect_taller(void);
#define CAMS 32
static struct { uint32_t cam; float fov, asp, efov, easp; } cams[CAMS]; static unsigned ncam;
static int cam_slot(uint32_t cam) {
	for (int i = 0; i < CAMS; i++) if (cams[i].cam == cam) return i;
	int i = (int)(ncam++ % CAMS); cams[i].cam = cam; cams[i].fov = cams[i].asp = cams[i].efov = cams[i].easp = 0; return i;
}
static void cam_apply(uint32_t cam) {
	const float k = (float)aspect_widen(), t = window_aspect_taller();
	const int i = cam_slot(cam);
	const float f = rdf(cam + 0x180), a = rdf(cam + 0x184);
	if (!(f > 1.0f && f < 170.0f && a > 0.3f && a < 4.0f)) return;   /* (not a camera's pair: leave it be) */
	if (f != cams[i].efov || !cams[i].fov) cams[i].fov = f;   /* (a value that isn't what we wrote is the game's own) */
	if (a != cams[i].easp || !cams[i].asp) cams[i].asp = a;
	float ef = cams[i].fov, ea = cams[i].asp;
	if (k > 1.01f) ea = cams[i].asp * k;
	else if (t > 1.01f && cams[i].fov > 0.0f && cams[i].fov < 170.0f) {
		const double r = (double)cams[i].fov * 3.14159265358979 / 360.0;
		ef = (float)(atan(tan(r) * (double)t) * 360.0 / 3.14159265358979); ea = cams[i].asp / t;
	}
	cams[i].efov = ef; cams[i].easp = ea;
	if (ef != f) wrf(cam + 0x180, ef);
	if (ea != a) wrf(cam + 0x184, ea);
}
void recomp_ihook_p3d_cam_aspect(Cpu *c, int reg) { (void)reg; if (aspect_widen() > 1.01 || window_aspect_taller() > 1.01f) cam_apply(c->r[0]); }   /* after 0x811a51be */
/* gfd's camera animation and resets write +0x180/+0x184 themselves, not through the setters (the track select's camera): after
 * each such pair, the same, on the register holding the camera there. Not after gfd's camera copies (0x811a4728, 0x811a47a6):
 * those copy what was already applied */
#define CAMREG(n) void recomp_ihook_p3d_cam_r##n(Cpu *c, int reg) { (void)reg; if (aspect_widen() > 1.01 || window_aspect_taller() > 1.01f) cam_apply(c->r[n]); }
CAMREG(0) CAMREG(4) CAMREG(5) CAMREG(9)
void recomp_ihook_p3d_cam_fov(Cpu *c, int reg) { (void)reg; if (aspect_widen() > 1.01 || window_aspect_taller() > 1.01f) cam_apply(c->r[0]); }      /* after 0x811a51d0 */

/* Keep P3D's two 2D frame-rate managers in sync with 30 / 60 / 90 / 120 fps (live-switchable):
 *   1. FrameRateMgr *(0x8132fe64): +8 is the target FPS enum (1=30, 2=60, 3=90, 4=120), used by 792
 *      calls to fn_8102ab9c (2D UI/menu/gameplay frame-count conversion) and fn_8102abfc/acb6.
 *   2. 2D keyframe evaluator *(0x813caaec): +0 is current FPS (30/60/90/120), +4 is authored FPS (30),
 *      used by fn_81154b98 to scale 2D keyframe curves by (authored / current). */
static void p3d_sync_2d_fps(void) {
	int fr = display_frame_rate();
	uint32_t enm = fr >= 120 ? 4u : fr >= 90 ? 3u : fr >= 60 ? 2u : 1u;   /* (its table: {1, 30, 60, 90, 120} by enum, fn_8102abfc) */
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
	uint32_t mgr = RD32(0x8132fe64u), kf = RD32(0x813caaecu);
	fprintf(stderr, "    p3d timing: frame %u: +4 %.6f +8 %.6f +0xc %u +0x2c %u | 2D rate enum %d, keyframes %d of %d fps\n", n, fa, fb, RD32(g + 0xc), RD32(g + 0x2c),
	        mgr ? (int)RD32(mgr + 8) : -1, kf ? (int)RD32(kf) : -1, kf ? (int)RD32(kf + 4) : -1);
}
static void p3d_on_frame(void) { p3d_sync_2d_fps(); p3d_timing(); }
__attribute__((constructor)) static void p3d_hooks_init(void) { hook_on_frame = p3d_on_frame; }
