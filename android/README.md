# Pocket Trubbles for Android (prototype, 2026-10-12)

The PC simulator (`sim/main.c`, LVGL + SDL2) built for Android around the
same `common/` the device runs: the pod, the Trubbles, the model, the sounds.
Nothing in `common/` changes; `sim/main.c` has four `#ifdef __ANDROID__`
hooks, and `app/jni/android_port.c` (~110 lines) does the rest:

- copies `sounds.bin`, `model_q4.bin` and `tokenizer.bin` out of the APK into
  the app's storage in the repo's own layout, and makes that the working
  directory and `$HOME`, so the sim's relative paths and its
  `~/.cache/pocket-tank/tank.sav` work unchanged
- fits the pod to the screen at the largest whole zoom (crisp pixels), black
  around it; landscape only, either way up (`SDL_HINT_ORIENTATIONS`)
- maps the finger (SDL's synthesized mouse) to the pod's own pixels, so the
  sim's tap / hold / drag-to-feed gestures work as on the glass
- sends the sim's `printf` to logcat (tag `trubbles-sim`)

`sim/main.c` also saves when the app goes to the background.

**Status:** runs on a Galaxy SM-F976U1 (Android 17, arm64): the pod
centered in landscape at 2x, the save restored, the model deciding, tapping
opens a card, dragging down from the top feeds, the coos play.

## Build

Needs: `sim/lvgl` cloned (as for the PC sim), and a Linux Android toolchain.
On WSL, without sudo, everything under `~/android`:

```bash
mkdir -p ~/android && cd ~/android
# Java 17
curl -fsSL -o jdk17.tgz https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse
mkdir -p jdk && tar -xzf jdk17.tgz -C jdk --strip-components=1
# the SDK's command-line tools (no unzip on a fresh WSL: python's zipfile)
curl -fsSL -o cmdline.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
python3 -m zipfile -e cmdline.zip ct && mkdir -p sdk/cmdline-tools && mv ct/cmdline-tools sdk/cmdline-tools/latest
chmod +x sdk/cmdline-tools/latest/bin/*
export JAVA_HOME=~/android/jdk ANDROID_HOME=~/android/sdk PATH=~/android/jdk/bin:$PATH
yes | sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=$ANDROID_HOME --licenses
sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=$ANDROID_HOME \
    "platform-tools" "platforms;android-34" "build-tools;34.0.0" "ndk;27.2.12479018" "cmake;3.22.1"
```

Then, from the repo:

```bash
android/fetch_sdl.sh                                         # SDL2 2.30.9 -> android/third_party (not in git)
printf 'sdk.dir=%s\n' "$HOME/android/sdk" > android/local.properties
cd android
export JAVA_HOME=~/android/jdk ANDROID_HOME=~/android/sdk PATH=~/android/jdk/bin:$PATH
./gradlew assembleDebug                                      # -> app/build/outputs/apk/debug/app-debug.apk
```

The APK takes `assets/sounds/sounds.bin` and `model/out/model_q4.bin` +
`tokenizer.bin` from the repo at build time (nothing duplicated in git): run
`tools/make_sounds.py build` / a model export first if those changed. It
holds arm64-v8a (phones) and x86_64 (the emulator) and needs **Android 9+**
(`minSdkVersion 28`: LVGL's SDL driver calls `aligned_alloc`, which bionic
has from API 28).

## Install and run

USB debugging on the phone (Settings > About phone > tap Build number 7
times; Developer options > USB debugging), plugged into Windows. From WSL,
the Windows SDK's adb sees it without usbipd:

```bash
ADB=/mnt/c/Users/<you>/AppData/Local/Android/Sdk/platform-tools/adb.exe
$ADB install -r "$(wslpath -w android/app/build/outputs/apk/debug/app-debug.apk)"
$ADB shell am start -S -n com.pockettrubbles.app/.TrubblesActivity
$ADB logcat -s trubbles:* trubbles-sim:* SDL:V AndroidRuntime:E
```

On a foldable, `screencap` needs `-d <display id>`
(`adb shell dumpsys SurfaceFlinger --display-id`); write the PNG on the phone
and `adb pull` it (`exec-out` mixes a warning into the image). The phone
dropped off USB several times on 2026-10-12: wrap adb calls in `timeout`.

## Known gaps

- **The pod fills ~40% of the screen** (2x on 2268 x 990). A fractional scale
  (2.7x) would fill the height at the cost of uneven pixels.
- **No on-screen controls** for what the sim does with keys (the light,
  reset, the brain toggle, the debug keys).
- **Time away is not caught up** as the device's sleep does
  (`tank_tick_sleep`): resume after hours away and the pod has not lived them.
- It still calls itself "pocket-tank v0.3.3" in its log; the icon is SDL's.
- No release signing, no Play Store listing.
