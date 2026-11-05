// Native launcher for Scout Advancement Tool.app.
//
// When an app's executable is a shell script, macOS attributes file-access requests (like
// reading the external drive the repo lives on) to bash/python instead of the app, so it
// silently refuses. This small signed binary runs the launch script as a child process, so
// macOS asks on behalf of "Scout Advancement Tool" and remembers the answer for this app.
//
// tools/install_app.sh bakes the script path in at build time (-DSCRIPT=…). Without SCRIPT
// (the self-contained release build from tools/build_release.sh), it runs the launch.sh in the
// app's own Contents/Resources, wherever the app was moved.
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

extern char **environ;
static pid_t child = 0;

static void forward(int sig) {
    if (child > 0) kill(child, sig);
}

int main(void) {
#ifdef SCRIPT
    char *script = SCRIPT;
#else
    char exe[PATH_MAX], real[PATH_MAX], script[PATH_MAX];
    uint32_t n = sizeof exe;
    if (_NSGetExecutablePath(exe, &n) != 0 || !realpath(exe, real)) {
        fprintf(stderr, "scout-advancement: could not find the app's own location\n");
        return 1;
    }
    // .../Contents/MacOS/scout-advancement -> .../Contents/Resources/launch.sh
    snprintf(script, sizeof script, "%s/../Resources/launch.sh", dirname(real));
#endif
    char *args[] = {"/bin/bash", script, NULL};
    if (posix_spawn(&child, "/bin/bash", NULL, NULL, args, environ) != 0) {
        perror("scout-advancement: could not start the launch script");
        return 1;
    }
    signal(SIGTERM, forward);
    signal(SIGINT, forward);

    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
