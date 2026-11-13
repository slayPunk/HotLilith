// Test-only ext-session-lock client for a disposable child compositor.
#define _GNU_SOURCE
#include <wayland-client.h>
#include <sys/mman.h>
#include <unistd.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <stdlib.h>
#include "ext-session-lock-v1-client-protocol.h"
static struct wl_display *display;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct wl_output *output;
static struct ext_session_lock_manager_v1 *manager;
static struct ext_session_lock_v1 *lock;
static struct wl_surface *surface;
static int locked,finished;
static void global(void *d,struct wl_registry *r,uint32_t name,const char *iface,uint32_t version) {
 if(!strcmp(iface,wl_compositor_interface.name))compositor=wl_registry_bind(r,name,&wl_compositor_interface,4);
 else if(!strcmp(iface,wl_shm_interface.name))shm=wl_registry_bind(r,name,&wl_shm_interface,1);
 else if(!strcmp(iface,wl_output_interface.name)&&!output)output=wl_registry_bind(r,name,&wl_output_interface,1);
 else if(!strcmp(iface,ext_session_lock_manager_v1_interface.name))manager=wl_registry_bind(r,name,&ext_session_lock_manager_v1_interface,1);
}
static void removed(void*d,struct wl_registry*r,uint32_t n){}
static const struct wl_registry_listener registry_listener={global,removed};
static void configured(void*d,struct ext_session_lock_surface_v1 *role,uint32_t serial,uint32_t width,uint32_t height) {
 int fd=memfd_create("isolated-lock-test",MFD_CLOEXEC);size_t bytes=(size_t)width*height*4;
 if(fd<0||ftruncate(fd,bytes))_exit(5);
 uint32_t *pixels=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
 if(pixels==MAP_FAILED)_exit(5);
 for(size_t i=0;i<bytes/4;i++)pixels[i]=0xff182030;
 struct wl_shm_pool *pool=wl_shm_create_pool(shm,fd,bytes);
 struct wl_buffer *buffer=wl_shm_pool_create_buffer(pool,0,width,height,width*4,WL_SHM_FORMAT_XRGB8888);
 ext_session_lock_surface_v1_ack_configure(role,serial);
 wl_surface_attach(surface,buffer,0,0);wl_surface_damage(surface,0,0,width,height);wl_surface_commit(surface);
 wl_shm_pool_destroy(pool);close(fd);
}
static const struct ext_session_lock_surface_v1_listener surface_listener={configured};
static void did_lock(void*d,struct ext_session_lock_v1*l){locked=1;puts("locked");fflush(stdout);}
static void did_finish(void*d,struct ext_session_lock_v1*l){finished=1;puts("denied");fflush(stdout);}
static const struct ext_session_lock_v1_listener lock_listener={did_lock,did_finish};
int main(int argc,char**argv) {
 // An explicit child socket is mandatory; never use the host's default socket.
 const char *host=getenv("HOTLILITH_HOST_WAYLAND_DISPLAY");
 if(argc!=2||!host||!strcmp(host,argv[1])||!getenv("HYPRLAND_INSTANCE_SIGNATURE"))return 2;
 alarm(15);display=wl_display_connect(argv[1]);if(!display)return 2;
 struct wl_registry *registry=wl_display_get_registry(display);wl_registry_add_listener(registry,&registry_listener,NULL);wl_display_roundtrip(display);
 if(!compositor||!shm||!manager||!output)return 3;
 lock=ext_session_lock_manager_v1_lock(manager);ext_session_lock_v1_add_listener(lock,&lock_listener,NULL);
 surface=wl_compositor_create_surface(compositor);
 struct ext_session_lock_surface_v1 *role=ext_session_lock_v1_get_lock_surface(lock,surface,output);
 ext_session_lock_surface_v1_add_listener(role,&surface_listener,NULL);
 while(!locked&&!finished)if(wl_display_dispatch(display)<0)return 4;
 if(finished)return 3;
 wl_display_roundtrip(display);
 for(;;){
  wl_display_flush(display);
  struct pollfd fds[2]={{0,POLLIN,0},{wl_display_get_fd(display),POLLIN,0}};
  if(poll(fds,2,500)<0)return 4;
  if(fds[0].revents&(POLLIN|POLLHUP))break;
  if(fds[1].revents&POLLIN)if(wl_display_dispatch(display)<0)return 4;
 }
 ext_session_lock_v1_unlock_and_destroy(lock);wl_display_roundtrip(display);puts("unlocked");fflush(stdout);
 ext_session_lock_surface_v1_destroy(role);wl_surface_destroy(surface);wl_display_disconnect(display);return 0;
}
