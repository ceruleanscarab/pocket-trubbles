/* android_port.h - what the Android build adds around the PC sim (sim/main.c,
 * under #ifdef __ANDROID__): the game's files out of the APK, the pod scaled
 * to the screen, and the finger's position on the pod. */
#ifndef ANDROID_PORT_H
#define ANDROID_PORT_H
#include "lvgl/lvgl.h"

/* copy sounds.bin, model_q4.bin and tokenizer.bin out of the APK into the
 * app's storage in the repo's own layout (assets/sounds, model/out), make
 * <storage>/sim the working directory and <storage> $HOME: the sim's relative
 * paths and its ~/.cache/pocket-tank save then work as they are */
void android_prepare(void);
/* each frame: fit the pod to the screen at the largest whole zoom (crisp
 * pixels), the rest of the screen black; again whenever the screen changes */
void android_fit(lv_display_t *disp);
/* a window position (the finger, as SDL's mouse) -> the pod's own pixels */
void android_map_mouse(lv_display_t *disp, lv_obj_t *canvas, int *x, int *y);

#endif
