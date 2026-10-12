#!/bin/bash
# fetch_sdl.sh - SDL2's source into android/third_party/SDL2 (not in git):
# the C library the app links and the Java glue (org.libsdl.app) its
# activity extends. Pinned; re-run after a version bump here.
set -euo pipefail
cd "$(dirname "$0")"
V=2.30.9
[ -f third_party/SDL2/include/SDL_version.h ] && grep -q "SDL_PATCHLEVEL 9" third_party/SDL2/include/SDL_version.h && { echo "fetch_sdl: SDL2 $V already here"; exit 0; }
rm -rf third_party/SDL2 && mkdir -p third_party
curl -fsSL "https://github.com/libsdl-org/SDL/releases/download/release-$V/SDL2-$V.tar.gz" | tar -xz -C third_party
mv "third_party/SDL2-$V" third_party/SDL2
echo "fetch_sdl: SDL2 $V -> android/third_party/SDL2"
