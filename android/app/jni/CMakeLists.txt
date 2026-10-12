# The game for Android: SDL2 (android/third_party, fetch_sdl.sh) and libmain -
# the PC sim's sources (sim/main.c, LVGL + its SDL driver) around common/, with
# android_port.c for the APK's files, the screen and the finger.
cmake_minimum_required(VERSION 3.6)
project(pocket_trubbles C)

set(REPO ${CMAKE_CURRENT_SOURCE_DIR}/../../..)
set(SDL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/SDL2)
if(NOT EXISTS ${SDL_DIR}/CMakeLists.txt)
    message(FATAL_ERROR "no SDL2 source: run android/fetch_sdl.sh")
endif()
if(NOT EXISTS ${REPO}/sim/lvgl/lvgl.h)
    message(FATAL_ERROR "no sim/lvgl: clone LVGL there, as for the PC sim")
endif()

add_subdirectory(${SDL_DIR} SDL2)

# the sim and LVGL include <SDL2/SDL.h>; SDL's own tree has no SDL2/ level
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/sdlshim)
if(NOT EXISTS ${CMAKE_BINARY_DIR}/sdlshim/SDL2)
    file(CREATE_LINK ${SDL_DIR}/include ${CMAKE_BINARY_DIR}/sdlshim/SDL2 SYMBOLIC)
endif()

file(GLOB_RECURSE LVGL_SRCS ${REPO}/sim/lvgl/src/*.c)
set(GAME_SRCS
    ${REPO}/sim/main.c ${REPO}/sim/advisor_llm.c ${REPO}/sim/persist_port_sim.c ${REPO}/sim/net_port_sim.c
    ${REPO}/common/tank.c ${REPO}/common/update.c ${REPO}/common/advisor.c ${REPO}/common/render.c
    ${REPO}/common/icons.c ${REPO}/common/progression.c ${REPO}/common/setup.c ${REPO}/common/audio.c
    ${REPO}/common/notice.c ${REPO}/common/sounds.c ${REPO}/common/battery.c
    ${REPO}/common/llm/q4_model.c ${REPO}/common/llm/word_tok.c ${REPO}/common/llm/advisor_core.c
    android_port.c)

add_library(main SHARED ${GAME_SRCS} ${LVGL_SRCS})
target_include_directories(main PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_BINARY_DIR}/sdlshim ${SDL_DIR}/include
    ${REPO}/sim ${REPO}/common ${REPO}/common/llm)
target_compile_definitions(main PRIVATE
    LV_CONF_INCLUDE_SIMPLE
    SOUNDS_BIN="../assets/sounds/sounds.bin"      # relative to the sim/ dir android_port.c makes the cwd
    PT_VERSION="android")
target_compile_options(main PRIVATE -O2 -std=gnu11 -Wno-unused-parameter -Wno-unused-result)
target_link_libraries(main SDL2 m log android)
