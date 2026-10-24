#include <cstdio>
#include <string>
#include <hyprland/src/version.h>
// Same ABI identity as PluginAPI.hpp in the pinned Hyprland 0.56.2 API,
// without the compositor-only globals instantiated by the full plugin header.
static std::string minor(const char* version) {
    std::string text{version};
    const auto dot=text.find_last_of('.');
    return dot==std::string::npos ? text : text.substr(0,dot);
}
int main() {
    const auto abi=std::string{GIT_COMMIT_HASH}+"_aq_"+minor(AQUAMARINE_VERSION)+
        "_hu_"+minor(HYPRUTILS_VERSION)+"_hg_"+minor(HYPRGRAPHICS_VERSION)+
        "_hc_"+minor(HYPRCURSOR_VERSION)+"_hlg_"+minor(HYPRLANG_VERSION);
    std::puts(abi.c_str());
}
