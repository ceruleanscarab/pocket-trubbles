package com.pockettrubbles.app;

import org.libsdl.app.SDLActivity;

/** SDL2's activity, loading the game (libmain.so: sim/main.c and common/). */
public class TrubblesActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        return new String[] { "SDL2", "main" };
    }
}
