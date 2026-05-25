/*
 * Iphone-Cast launcher
 *
 * Tiny Win32 wrapper around `pythonw.exe main.py`. Prefers the project's
 * .venv\Scripts\pythonw.exe; falls back to pythonw.exe on PATH. Uses the
 * Windows subsystem (-mwindows) so no console window appears.
 *
 * Build:
 *   /ucrt64/bin/gcc.exe -O2 -mwindows -static -static-libgcc \
 *       -o Iphone-Cast.exe launcher.c
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static void show_error(const char *msg) {
    MessageBoxA(NULL, msg, "Iphone-Cast", MB_ICONERROR | MB_OK);
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmdline, int show) {
    (void)inst; (void)prev; (void)cmdline; (void)show;

    char exe_path[MAX_PATH];
    if (!GetModuleFileNameA(NULL, exe_path, MAX_PATH)) {
        show_error("No se pudo obtener la ruta del ejecutable.");
        return 1;
    }

    /* exe_dir = exe_path with the filename stripped off */
    char exe_dir[MAX_PATH];
    strncpy(exe_dir, exe_path, MAX_PATH);
    exe_dir[MAX_PATH - 1] = '\0';
    char *slash = strrchr(exe_dir, '\\');
    if (!slash) {
        show_error("Ruta del ejecutable invalida.");
        return 1;
    }
    *slash = '\0';

    char venv_py[MAX_PATH];
    snprintf(venv_py, MAX_PATH, "%s\\.venv\\Scripts\\pythonw.exe", exe_dir);

    char main_py[MAX_PATH];
    snprintf(main_py, MAX_PATH, "%s\\main.py", exe_dir);

    if (GetFileAttributesA(main_py) == INVALID_FILE_ATTRIBUTES) {
        show_error("No se encontro main.py junto al ejecutable.");
        return 1;
    }

    /* Build the command line. CreateProcessA needs a writable buffer. */
    char cmd[MAX_PATH * 3];
    BOOL have_venv = (GetFileAttributesA(venv_py) != INVALID_FILE_ATTRIBUTES);
    if (have_venv) {
        snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\"", venv_py, main_py);
    } else {
        snprintf(cmd, sizeof(cmd), "pythonw.exe \"%s\"", main_py);
    }

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessA(
            NULL,            /* application name (use cmdline) */
            cmd,             /* command line */
            NULL, NULL,      /* security */
            FALSE,           /* inherit handles */
            DETACHED_PROCESS,/* no console */
            NULL,            /* environment */
            exe_dir,         /* working directory */
            &si, &pi)) {
        char msg[MAX_PATH + 200];
        snprintf(msg, sizeof(msg),
                 "No se pudo iniciar Python.\n\n"
                 "Comando intentado:\n%s\n\n"
                 "Verifica que tienes Python instalado (o el .venv del proyecto).",
                 cmd);
        show_error(msg);
        return 1;
    }

    /* Fire and forget: Python keeps running after we exit. */
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return 0;
}
