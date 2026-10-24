// Send physical US keycodes to a disposable child Wayland compositor.
// Unlike wtype's compact keymap, these codes match a normal keyboard, so
// compositor bindings are tested under their usual keycode resolution.
#define _GNU_SOURCE
#include <linux/input-event-codes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include <xkbcommon/xkbcommon.h>
#include "virtual-keyboard-unstable-v1-client-protocol.h"

static struct zwp_virtual_keyboard_manager_v1* manager;
static struct wl_seat* seat;
static void global(void* data,struct wl_registry* registry,uint32_t name,const char* interface,uint32_t version) {
    if(!strcmp(interface,zwp_virtual_keyboard_manager_v1_interface.name))
        manager=wl_registry_bind(registry,name,&zwp_virtual_keyboard_manager_v1_interface,1);
    else if(!strcmp(interface,wl_seat_interface.name) && !seat)
        seat=wl_registry_bind(registry,name,&wl_seat_interface,1);
}
static void removed(void* data,struct wl_registry* registry,uint32_t name) {}
static const struct wl_registry_listener registry_listener={global,removed};
static uint32_t now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000+t.tv_nsec/1000000; }
static void key(struct wl_display* display,struct zwp_virtual_keyboard_v1* vk,struct xkb_state* state,uint32_t code,int pressed) {
    zwp_virtual_keyboard_v1_key(vk,now(),code,pressed);
    xkb_state_update_key(state,code+8,pressed?XKB_KEY_DOWN:XKB_KEY_UP);
    zwp_virtual_keyboard_v1_modifiers(vk,
        xkb_state_serialize_mods(state,XKB_STATE_MODS_DEPRESSED),
        xkb_state_serialize_mods(state,XKB_STATE_MODS_LATCHED),
        xkb_state_serialize_mods(state,XKB_STATE_MODS_LOCKED),0);
    wl_display_roundtrip(display);usleep(35000);
}
int main(int argc,char** argv) {
    if(argc!=2) { fprintf(stderr,"usage: keyboard super[+ctrl][+shift]+g\n");return 2; }
    const char* signature=getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if(!signature || !getenv("WAYLAND_DISPLAY")) return 2;
    struct wl_display* display=wl_display_connect(NULL);if(!display)return 1;
    struct wl_registry* registry=wl_display_get_registry(display);
    wl_registry_add_listener(registry,&registry_listener,NULL);wl_display_roundtrip(display);
    if(!manager || !seat)return 1;
    struct zwp_virtual_keyboard_v1* vk=zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(manager,seat);
    struct xkb_context* ctx=xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_rule_names names={.layout="us"};
    struct xkb_keymap* map=xkb_keymap_new_from_names(ctx,&names,XKB_KEYMAP_COMPILE_NO_FLAGS);
    if(!map)return 1;
    char* text=xkb_keymap_get_as_string(map,XKB_KEYMAP_FORMAT_TEXT_V1);
    size_t size=strlen(text)+1;int fd=memfd_create("hotlilit-test-keymap",MFD_CLOEXEC);
    if(fd<0 || write(fd,text,size)!=(ssize_t)size)return 1;
    zwp_virtual_keyboard_v1_keymap(vk,WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1,fd,size);
    wl_display_roundtrip(display);close(fd);free(text);
    struct xkb_state* state=xkb_state_new(map);
    const int hold=!strncmp(argv[1],"hold-",5);
    const int meta=strstr(argv[1],"super")!=NULL;
    const int ctrl=strstr(argv[1],"ctrl")!=NULL,shift=strstr(argv[1],"shift")!=NULL;
    if(meta)key(display,vk,state,KEY_LEFTMETA,1);
    const int alt=strstr(argv[1],"alt")!=NULL;
    if(alt)key(display,vk,state,KEY_LEFTALT,1);
    if(ctrl)key(display,vk,state,KEY_LEFTCTRL,1);
    if(shift)key(display,vk,state,KEY_LEFTSHIFT,1);
    if(!strcmp(argv[1],"hold-w"))key(display,vk,state,KEY_W,1);
    if(hold) { puts("ready");fflush(stdout);usleep(!strcmp(argv[1],"hold-seat")?600000000:1800000); }
    else {
        const char* name=strrchr(argv[1],'+'); name=name?name+1:argv[1];
        uint32_t code=KEY_G;
        if(!strcmp(name,"escape"))code=KEY_ESC;
        else if(!strcmp(name,"enter"))code=KEY_ENTER;
        else if(!strcmp(name,"space"))code=KEY_SPACE;
        else if(!strcmp(name,"up"))code=KEY_UP;
        else if(!strcmp(name,"down"))code=KEY_DOWN;
        else if(!strcmp(name,"left"))code=KEY_LEFT;
        else if(!strcmp(name,"right"))code=KEY_RIGHT;
        else if(!strcmp(name,"c"))code=KEY_C;
        else if(!strcmp(name,"n"))code=KEY_N;
        else if(!strcmp(name,"p"))code=KEY_P;
        else if(!strcmp(name,"w"))code=KEY_W;
        else if(!strcmp(name,"a"))code=KEY_A;
        else if(!strcmp(name,"s"))code=KEY_S;
        else if(!strcmp(name,"d"))code=KEY_D;
        else if(!strcmp(name,"f"))code=KEY_F;
        else if(!strcmp(name,"home"))code=KEY_HOME;
        key(display,vk,state,code,1);key(display,vk,state,code,0);
    }
    if(!strcmp(argv[1],"hold-w"))key(display,vk,state,KEY_W,0);
    if(shift)key(display,vk,state,KEY_LEFTSHIFT,0);
    if(ctrl)key(display,vk,state,KEY_LEFTCTRL,0);
    if(alt)key(display,vk,state,KEY_LEFTALT,0);
    if(meta)key(display,vk,state,KEY_LEFTMETA,0);
    zwp_virtual_keyboard_v1_destroy(vk);wl_display_roundtrip(display);
    xkb_state_unref(state);xkb_keymap_unref(map);xkb_context_unref(ctx);wl_display_disconnect(display);
    return 0;
}
