// Exercise the same SDL2 relative mouse mode used by games, on Wayland/X11.
#include <SDL.h>
#include <stdio.h>
int main(void) {
    setbuf(stdout,NULL);
    if (SDL_Init(SDL_INIT_VIDEO)) { puts(SDL_GetError());return 1; }
    SDL_Window* w=SDL_CreateWindow("hotlilit-relative",40,40,720,400,SDL_WINDOW_RESIZABLE);
    if(!w){puts(SDL_GetError());return 1;}
    SDL_Renderer* r=SDL_CreateRenderer(w,-1,SDL_RENDERER_SOFTWARE);
    printf("ready %s\n",SDL_GetCurrentVideoDriver());
    int relative=0,grab=0,run=1,lastWidth=0,lastHeight=0;double yaw=0;
    while(run) {
        SDL_Event e;
        while(SDL_PollEvent(&e)) {
            if(e.type==SDL_QUIT)run=0;
            if(e.type==SDL_MOUSEBUTTONDOWN || e.type==SDL_MOUSEBUTTONUP)
                printf("button %d %d\n",e.button.button,e.button.state);
            if(e.type==SDL_KEYDOWN) {
                printf("key %s\n",SDL_GetKeyName(e.key.keysym.sym));
                if(e.key.keysym.sym==SDLK_c) {
                    relative=!relative;
                    int result=SDL_SetRelativeMouseMode(relative?SDL_TRUE:SDL_FALSE);
                    printf("relative %d result %d %s\n",relative,result,SDL_GetError());
                }
                if(e.key.keysym.sym==SDLK_g) {grab=!grab;SDL_SetWindowGrab(w,grab?SDL_TRUE:SDL_FALSE);printf("grab %d\n",grab);}
                if(e.key.keysym.sym==SDLK_n) {
                    int width,height;SDL_GetWindowSize(w,&width,&height);
                    SDL_SetWindowMaximumSize(w,width,height);
                    printf("maximum %d %d\n",width,height);
                }
            }
            if(e.type==SDL_MOUSEMOTION) {
                printf("motion %d %d %d\n",SDL_GetRelativeMouseMode(),e.motion.xrel,e.motion.yrel);
                if(SDL_GetRelativeMouseMode())yaw+=e.motion.xrel;
            }
        }
        int width,height;SDL_GetRendererOutputSize(r,&width,&height);
        if(width!=lastWidth || height!=lastHeight) {
            printf("render-size %d %d\n",width,height);
            lastWidth=width;lastHeight=height;
        }
        SDL_SetRenderDrawColor(r,20,28,44,255);SDL_RenderClear(r);
        SDL_SetRenderDrawColor(r,90,190,240,255);
        for(int x=-width;x<width*2;x+=80) {
            int screen=(int)(x-yaw)% (width+80);if(screen<0)screen+=width+80;
            SDL_RenderDrawLine(r,screen,0,width/2+(screen-width/2)/3,height/2);
            SDL_RenderDrawLine(r,screen,height,width/2+(screen-width/2)/3,height/2);
        }
        SDL_RenderPresent(r);SDL_Delay(8);
    }
    SDL_Quit();return 0;
}
