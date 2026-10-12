/* android_port.c - see android_port.h. */
#include "android_port.h"
#include "tank.h"
#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>
#include <android/native_window.h>
#include <android/log.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define LOG(...) __android_log_print(ANDROID_LOG_INFO, "trubbles", __VA_ARGS__)

static void mkdirs(const char *path) {
    char p[512]; snprintf(p, sizeof p, "%s", path);
    for (char *s = p + 1; *s; s++)
        if (*s == '/') { *s = 0; mkdir(p, 0700); *s = '/'; }
    mkdir(p, 0700);
}

/* one APK asset -> a file, unless a file of the same size is already there */
static void copy_asset(const char *name, const char *dst) {
    SDL_RWops *in = SDL_RWFromFile(name, "rb");
    if (!in) { LOG("asset %s: missing (%s)", name, SDL_GetError()); return; }
    Sint64 n = SDL_RWsize(in);
    struct stat st;
    if (stat(dst, &st) == 0 && st.st_size == n) { SDL_RWclose(in); return; }
    FILE *out = fopen(dst, "wb");
    if (!out) { LOG("asset %s: cannot write %s (%s)", name, dst, strerror(errno)); SDL_RWclose(in); return; }
    char buf[64 * 1024]; size_t got;
    while ((got = SDL_RWread(in, buf, 1, sizeof buf)) > 0) fwrite(buf, 1, got, out);
    fclose(out); SDL_RWclose(in);
    LOG("asset %s -> %s (%lld bytes)", name, dst, (long long)n);
}

/* stdout and stderr -> logcat: the sim reports with printf (the save, the
 * sounds, the model), which Android otherwise drops */
static int s_log_fd[2];
static void *log_pump(void *ud) {
    (void)ud;
    char line[1024]; size_t n = 0; char c;
    while (read(s_log_fd[0], &c, 1) == 1) {
        if (c == '\n' || n == sizeof line - 1) { line[n] = 0; __android_log_write(ANDROID_LOG_INFO, "trubbles-sim", line); n = 0; }
        else line[n++] = c;
    }
    return NULL;
}
static void stdout_to_logcat(void) {
    setvbuf(stdout, NULL, _IOLBF, 0); setvbuf(stderr, NULL, _IONBF, 0);
    if (pipe(s_log_fd) != 0) return;
    dup2(s_log_fd[1], 1); dup2(s_log_fd[1], 2);
    pthread_t t;
    if (pthread_create(&t, NULL, log_pump, NULL) == 0) pthread_detach(t);
}

void android_prepare(void) {
    stdout_to_logcat();
    SDL_SetHint(SDL_HINT_ORIENTATIONS, "LandscapeLeft LandscapeRight");   /* SDL's own choice overrides the manifest's */
    const char *base = SDL_AndroidGetInternalStoragePath();
    if (!base) { LOG("no internal storage path: %s", SDL_GetError()); return; }
    char d[512], f[600];
    snprintf(d, sizeof d, "%s/sim", base); mkdirs(d);
    snprintf(d, sizeof d, "%s/assets/sounds", base); mkdirs(d);
    snprintf(f, sizeof f, "%s/sounds.bin", d); copy_asset("sounds.bin", f);
    snprintf(d, sizeof d, "%s/model/out", base); mkdirs(d);
    snprintf(f, sizeof f, "%s/model_q4.bin", d); copy_asset("model_q4.bin", f);
    snprintf(f, sizeof f, "%s/tokenizer.bin", d); copy_asset("tokenizer.bin", f);
    setenv("HOME", base, 1);
    snprintf(d, sizeof d, "%s/sim", base);
    if (chdir(d) != 0) LOG("chdir %s: %s", d, strerror(errno));
    SDL_SetHint(SDL_HINT_TOUCH_MOUSE_EVENTS, "1");     /* the finger arrives as SDL's mouse, as the sim reads it */
}

void android_fit(lv_display_t *disp) {
    static int last_w, last_h;
    /* the surface's real size, from Android: SDL's own idea of the window is
       whatever LVGL last asked for (it requests 448 x 368 at creation, which
       Android ignores but SDL records) */
    SDL_Renderer *r = lv_sdl_window_get_renderer(disp);
    SDL_Window *win = r ? SDL_RenderGetWindow(r) : NULL;
    SDL_SysWMinfo wm; SDL_VERSION(&wm.version);
    if (!win || !SDL_GetWindowWMInfo(win, &wm) || !wm.info.android.window) return;
    int w = ANativeWindow_getWidth(wm.info.android.window), h = ANativeWindow_getHeight(wm.info.android.window);
    if (w <= 0 || h <= 0) return;
    if (w == last_w && h == last_h) return;
    last_w = w; last_h = h;
    int zx = w / TANK_W, zy = h / TANK_H, z = zx < zy ? zx : zy;
    if (z < 1) z = 1;
    if (z > 255) z = 255;
    lv_sdl_window_set_zoom(disp, (uint8_t)z);
    lv_display_set_resolution(disp, w / z, h / z);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_black(), 0);
    LOG("screen %d x %d: the pod at %dx", w, h, z);
}

void android_map_mouse(lv_display_t *disp, lv_obj_t *canvas, int *x, int *y) {
    int z = lv_sdl_window_get_zoom(disp);
    if (z < 1) z = 1;
    lv_area_t a; lv_obj_get_coords(canvas, &a);
    int tx = *x / z - a.x1, ty = *y / z - a.y1;
    *x = tx < 0 ? 0 : tx >= TANK_W ? TANK_W - 1 : tx;
    *y = ty < 0 ? 0 : ty >= TANK_H ? TANK_H - 1 : ty;
}
