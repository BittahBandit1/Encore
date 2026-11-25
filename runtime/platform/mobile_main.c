/* A phone's or handheld's start (TARGET=android | ios, runtime/build.py): SDL_main, which finds the game's files, sets up
 * the folder the game writes in and calls main.c's main (recomp_main here) as `vitarecomp run` would have.
 *
 * pipeline/port.py puts a game in two parts:
 *   the data folder   launch.ini, game.img and its modules' images, shaders.txt, fs/app0 (the game's own files) and any
 *                     other read-only device the copy has (fs/addcont0: its add-ons). Read only.
 *   the work folder   the game's current directory: settings.ini, its saves (fs/ux0, savedata...), shader caches,
 *                     session.log. fs/<device> links to the data folder's for each device it has.
 * iOS: the data folder is in the app (<app>/game), unless Documents/game has a launch.ini (a copy put there in Files or
 * Finder, for an app built without one); the work folder is Documents/<title> -- the Files app shows it, saves and logs
 * included.
 * Android: both are the app's own folder on the shared storage (Android/data/<package>/files): the port's data folder
 * copied there (USB or adb push), the game writes beside it. Its own folder needs no storage permission.
 *
 * launch.ini, one setting a line:
 *   title=PCSE01274            the title id (RECOMP_TITLE)
 *   name=...                   the game's name (RECOMP_GAME_NAME: the window's, the overlay's)
 *   image=game.img             the program's image, entry=<hex> its module_start
 *   modules=mod_a.img,...      the modules loaded with it (RECOMP_MODULES)
 *   env=KEY=VALUE              its RUN_ENV and the run's fixed settings, one per line (the environment wins where it's set)
 */
#ifdef RECOMP_MOBILE
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <errno.h>
#include <stdarg.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int recomp_main(int argc, char **argv);

static char data_dir[1024], work_dir[1024];

static int exists(const char *p) { struct stat st; return stat(p, &st) == 0; }
static void mkdirs(const char *p) {
	char b[1024]; snprintf(b, sizeof b, "%s", p);
	for (char *q = b + 1; *q; q++) if (*q == '/') { *q = 0; mkdir(b, 0755); *q = '/'; }
	mkdir(b, 0755);
}
static void strip_slash(char *p) { size_t n = strlen(p); while (n > 1 && p[n - 1] == '/') p[--n] = 0; }

/* a message the player can read when the game can't start (no data folder): SDL's box, and the log */
static int fail(const char *fmt, ...) {
	char msg[2048]; va_list ap; va_start(ap, fmt); vsnprintf(msg, sizeof msg, fmt, ap); va_end(ap);
	fprintf(stderr, "encore: %s\n", msg);
	SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Encore", msg, NULL);
	return 1;
}

static int find_dirs(void) {
#ifdef __ANDROID__
	const char *ext = SDL_GetAndroidExternalStoragePath();
	if (!ext) return fail("Android gave no folder for the game (%s).", SDL_GetError());
	snprintf(data_dir, sizeof data_dir, "%s", ext); snprintf(work_dir, sizeof work_dir, "%s", ext);
	/* (the internal folder too, for a data folder adb put there: run-as <package> cp -r) */
	char p[1200]; snprintf(p, sizeof p, "%s/launch.ini", data_dir);
	if (!exists(p)) {
		const char *in = SDL_GetAndroidInternalStoragePath();
		char q[1200]; if (in) snprintf(q, sizeof q, "%s/launch.ini", in);
		if (in && exists(q)) { snprintf(data_dir, sizeof data_dir, "%s", in); snprintf(work_dir, sizeof work_dir, "%s", in); }
	}
#else
	const char *docs = SDL_GetUserFolder(SDL_FOLDER_DOCUMENTS), *base = SDL_GetBasePath();
	if (!docs) return fail("iOS gave no Documents folder (%s).", SDL_GetError());
	char p[1200];
	snprintf(p, sizeof p, "%sgame/launch.ini", docs);
	if (exists(p)) snprintf(data_dir, sizeof data_dir, "%sgame", docs);
	else snprintf(data_dir, sizeof data_dir, "%sgame", base ? base : "./");
	snprintf(work_dir, sizeof work_dir, "%s", docs);   /* (the title's own folder under it: below, once launch.ini names it) */
#endif
	strip_slash(data_dir); strip_slash(work_dir);
	return 0;
}

/* fs/<device> in the work folder for each of the data folder's devices (app0, addcont0): a link, made again every start (an
 * iOS app's folder moves with each install); one the game made itself (a real folder: its saves) is left alone */
static void link_devices(void) {
	char fs[1200], dfs[1200]; snprintf(fs, sizeof fs, "%s/fs", work_dir); snprintf(dfs, sizeof dfs, "%s/fs", data_dir);
	mkdirs(fs);
	if (!strcmp(fs, dfs)) return;
	DIR *d = opendir(dfs); if (!d) return;
	struct dirent *e;
	while ((e = readdir(d))) {
		if (e->d_name[0] == '.') continue;
		char link[1400], target[1400]; snprintf(link, sizeof link, "%s/%s", fs, e->d_name); snprintf(target, sizeof target, "%s/%s", dfs, e->d_name);
		struct stat st;
		if (lstat(link, &st) == 0) { if (!S_ISLNK(st.st_mode)) continue; unlink(link); }
		if (symlink(target, link)) fprintf(stderr, "encore: fs/%s: can't link to %s (%s)\n", e->d_name, target, strerror(errno));
	}
	closedir(d);
}

int main(int argc, char **argv) {
	(void)argc;
	SDL_SetHint(SDL_HINT_ORIENTATIONS, "LandscapeLeft LandscapeRight");
	SDL_SetHint(SDL_HINT_IOS_HIDE_HOME_INDICATOR, "2");
	if (find_dirs()) return 1;
	char ini[1200]; snprintf(ini, sizeof ini, "%s/launch.ini", data_dir);
	FILE *f = fopen(ini, "r");
	if (!f) {
#ifdef __ANDROID__
		return fail("The game's files aren't here yet. Copy the folder Encore made for this game (the one with launch.ini in it) "
		            "into:\n\n%s\n\nwith USB file transfer or adb push, then open the app again.", work_dir);
#else
		return fail("This app has no game in it. Put the folder Encore made for the game (the one with launch.ini in it) in "
		            "Files > On My iPhone > %s, named game, then open the app again.", SDL_GetAppMetadataProperty(SDL_PROP_APP_METADATA_NAME_STRING) ? SDL_GetAppMetadataProperty(SDL_PROP_APP_METADATA_NAME_STRING) : "Encore");
#endif
	}
	char title[64] = "", name[256] = "", image[256] = "game.img", entry[32] = "", modules[2048] = "", line[4096];
	static char envs[64][1024]; int nenv = 0;
	while (fgets(line, sizeof line, f)) {
		line[strcspn(line, "\r\n")] = 0;
		char *eq = strchr(line, '='); if (!eq || line[0] == '#') continue;
		*eq = 0; const char *k = line, *v = eq + 1;
		if (!strcmp(k, "title")) snprintf(title, sizeof title, "%s", v);
		else if (!strcmp(k, "name")) snprintf(name, sizeof name, "%s", v);
		else if (!strcmp(k, "image")) snprintf(image, sizeof image, "%s", v);
		else if (!strcmp(k, "entry")) snprintf(entry, sizeof entry, "%s", v);
		else if (!strcmp(k, "modules")) snprintf(modules, sizeof modules, "%s", v);
		else if (!strcmp(k, "env") && nenv < 64) snprintf(envs[nenv++], sizeof envs[0], "%s", v);
	}
	fclose(f);
	if (!entry[0]) return fail("%s has no entry= line: make the port again.", ini);
#ifndef __ANDROID__
	if (title[0]) { size_t n = strlen(work_dir); snprintf(work_dir + n, sizeof work_dir - n, "/%s", title); }
#endif
	mkdirs(work_dir);
	if (chdir(work_dir)) return fail("can't use %s (%s)", work_dir, strerror(errno));
	/* the session's log where the player can get at it (the Files app; adb pull), the one before kept */
	rename("session.log", "session.prev.log");
	if (!freopen("session.log", "w", stderr)) fprintf(stderr, "encore: no session.log (%s)\n", strerror(errno));
	setvbuf(stderr, NULL, _IOLBF, 0);
	fprintf(stderr, "encore: %s (%s), data %s, work %s\n", name, title, data_dir, work_dir);
	link_devices();
	{	/* launch_env.txt in the work folder, KEY=VALUE a line: this launch's extra settings, set from a computer (port_device.py
		 * env: a test's scripted input, a frame rate) -- over launch.ini's and the app's own */
		FILE *ef = fopen("launch_env.txt", "r");
		if (ef) {
			static char line[1 << 16];
			while (fgets(line, sizeof line, ef)) {
				size_t n = strlen(line); while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = 0;
				char *eq = strchr(line, '='); if (!eq || eq == line) continue;
				*eq = 0; setenv(line, eq + 1, 1);
				fprintf(stderr, "encore: launch_env.txt: %s (%zu characters)\n", line, strlen(eq + 1));
			}
			fclose(ef);
		}
	}
	for (int i = 0; i < nenv; i++) {
		char *eq = strchr(envs[i], '='); if (!eq) continue;
		*eq = 0; setenv(envs[i], eq + 1, 0); *eq = '=';
	}
	if (title[0]) setenv("RECOMP_TITLE", title, 0);
	if (name[0]) setenv("RECOMP_GAME_NAME", name, 0);
	/* the launcher's shared settings (main.c): the work folder's, on a phone there's no launcher */
	{ char p[1200]; snprintf(p, sizeof p, "%s/shared-settings.ini", work_dir); setenv("RECOMP_SETTINGS_SHARED", p, 0); }
	{ char p[1200]; snprintf(p, sizeof p, "%s/shaders.txt", data_dir); if (exists(p)) setenv("RECOMP_SHADER_RECIPES_SHIPPED", p, 0); }
	if (modules[0]) {   /* the module images, from the data folder */
		static char mods[8192]; size_t n = 0; char list[2048]; snprintf(list, sizeof list, "%s", modules);
		for (char *m = strtok(list, ","); m; m = strtok(0, ","))
			n += (size_t)snprintf(mods + n, sizeof mods - n, "%s%s/%s", n ? "," : "", data_dir, m);
		setenv("RECOMP_MODULES", mods, 1);
	}
	static char img[1400]; snprintf(img, sizeof img, "%s/%s", data_dir, image);
	char *av[] = { argv && argv[0] ? argv[0] : "encore", img, entry, "100000000000", NULL };
	return recomp_main(4, av);
}
#endif
