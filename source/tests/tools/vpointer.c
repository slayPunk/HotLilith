// A scripted virtual mouse for nested-compositor tests (wlr-virtual-pointer).
//
//   vpointer WIDTH HEIGHT CMD...
//     abs X Y      move to X,Y in a WIDTHxHEIGHT output layout
//     rel DX DY    move by DX,DY
//     down / up    press / release the left button   (rdown / rup: right)
//     sleep MS
//
// Everything runs in one connection, so a pressed button stays pressed
// between commands.
#include <linux/input-event-codes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>

#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"

static struct zwlr_virtual_pointer_manager_v1* manager;
static struct wl_seat*                         seat;

static void global(void* data, struct wl_registry* registry, uint32_t name, const char* interface, uint32_t version) {
    if (!strcmp(interface, zwlr_virtual_pointer_manager_v1_interface.name))
        manager = wl_registry_bind(registry, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
    else if (!strcmp(interface, wl_seat_interface.name) && !seat)
        seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
}
static void global_remove(void* data, struct wl_registry* registry, uint32_t name) {}
static const struct wl_registry_listener listener = {global, global_remove};

static uint32_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: vpointer WIDTH HEIGHT [abs X Y|rel DX DY|down|up|rdown|rup|sleep MS]...\n");
        return 2;
    }
    struct wl_display* display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "vpointer: no wayland display\n");
        return 1;
    }
    struct wl_registry* registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &listener, NULL);
    wl_display_roundtrip(display);
    if (!manager) {
        fprintf(stderr, "vpointer: compositor lacks zwlr_virtual_pointer_manager_v1\n");
        return 1;
    }
    struct zwlr_virtual_pointer_v1* pointer = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(manager, seat);
    const uint32_t                  W = atoi(argv[1]), H = atoi(argv[2]);

    const int interactive = argc == 4 && !strcmp(argv[3], "stdin");
    if (interactive) { puts("ready"); fflush(stdout); }
    char line[4096];
    char* commands[256];
    do {
        int count = argc, first = 3;
        char** args = argv;
        if (interactive) {
            if (!fgets(line, sizeof line, stdin)) break;
            count = 0; first = 0; args = commands;
            for (char* token = strtok(line, " \t\r\n"); token && count < 256; token = strtok(NULL, " \t\r\n")) commands[count++] = token;
        }
    for (int i = first; i < count; ++i) {
        const char* cmd = args[i];
        if (!strcmp(cmd, "abs") && i + 2 < count) {
            zwlr_virtual_pointer_v1_motion_absolute(pointer, now_ms(), atoi(args[i + 1]), atoi(args[i + 2]), W, H);
            i += 2;
        } else if (!strcmp(cmd, "rel") && i + 2 < count) {
            zwlr_virtual_pointer_v1_motion(pointer, now_ms(), wl_fixed_from_double(atof(args[i + 1])), wl_fixed_from_double(atof(args[i + 2])));
            i += 2;
        } else if (!strcmp(cmd, "axis") && i + 1 < count) {
            zwlr_virtual_pointer_v1_axis_source(pointer, WL_POINTER_AXIS_SOURCE_WHEEL);
            zwlr_virtual_pointer_v1_axis(pointer, now_ms(), WL_POINTER_AXIS_VERTICAL_SCROLL, wl_fixed_from_double(atof(args[++i])));
        } else if (!strcmp(cmd, "down") || !strcmp(cmd, "up") || !strcmp(cmd, "rdown") || !strcmp(cmd, "rup") || !strcmp(cmd, "mdown") || !strcmp(cmd, "mup")) {
            const uint32_t BUTTON = cmd[0] == 'r' ? BTN_RIGHT : cmd[0] == 'm' ? BTN_MIDDLE : BTN_LEFT;
            const uint32_t STATE  = strstr(cmd, "down") ? WL_POINTER_BUTTON_STATE_PRESSED : WL_POINTER_BUTTON_STATE_RELEASED;
            zwlr_virtual_pointer_v1_button(pointer, now_ms(), BUTTON, STATE);
        } else if (!strcmp(cmd, "sleep") && i + 1 < count) {
            wl_display_flush(display);
            usleep(atoi(args[i + 1]) * 1000);
            i += 1;
            continue;
        } else {
            fprintf(stderr, "vpointer: bad command %s\n", cmd);
            return 2;
        }
        zwlr_virtual_pointer_v1_frame(pointer);
        wl_display_flush(display);
        usleep(8000);
    }
        wl_display_roundtrip(display);
        if (interactive) { puts("done"); fflush(stdout); }
    } while (interactive);
    wl_display_roundtrip(display);
    zwlr_virtual_pointer_v1_destroy(pointer);
    wl_display_roundtrip(display);
    wl_display_disconnect(display);
    return 0;
}
