// Native launcher for Scout Advancement Tool.app.
//
// When an app's executable is a shell script, macOS attributes file-access requests (like
// reading the external drive the repo lives on) to bash/python instead of the app, so it
// silently refuses. This small signed binary runs the launch script as a child process, so
// macOS asks on behalf of "Scout Advancement Tool" and remembers the answer for this app.
//
// The script path is baked in at build time by tools/install_app.sh (-DSCRIPT=…).
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <sys/wait.h>

extern char **environ;
static pid_t child = 0;

static void forward(int sig) {
    if (child > 0) kill(child, sig);
}

int main(void) {
    char *args[] = {"/bin/bash", SCRIPT, NULL};
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
