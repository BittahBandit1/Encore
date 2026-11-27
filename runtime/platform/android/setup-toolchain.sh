#!/bin/bash
# The Android toolchain, pinned: what a phone or handheld build needs (TARGET=android, runtime/build.py; pipeline/port.py
# packs the APK). Google's NDK (the compiler and Android's libraries), the SDK's build tools (aapt2, d8, zipalign,
# apksigner) and one platform's android.jar (what SDL's Java code compiles against); SDL3 built for arm64-v8a as the
# shared library the APK carries, with SDL's Java activity beside it; FFmpeg's H.264 decoder, static (the movies).
# Into $ATIV_ANDROID_TOOLCHAIN (default ~/toolchains/ativ-android). Runs on macOS (Apple silicon or Intel) or Linux
# x86-64, the hosts the NDK ships for; needs curl, unzip, cmake, ninja (or make) and a JDK (17 or newer) for packaging.
# About 3.5 GB once unpacked.
set -euo pipefail
NDK=r29; NDK_PKG=29.0.14206865
NDK_MAC_SHA1=03d29fbb57e3c05a7d53597dd011d856c1456a4f
NDK_LINUX_SHA1=87e2bb7e9be5d6a1c6cdf5ec40dd4e0c6d07c30b
BT=36.1; BT_MAC_SHA1=d365b05ca1810ca92b428b92717865ad4188b5e1; BT_LINUX_SHA1=936a0d6bd5ae3e2118a7567dddbc95ff67ed46e9
PLAT=36_r02; PLAT_SHA1=2c1a80dd4d9f7d0e6dd336ec603d9b5c55a6f576
PT=37.0.3; PT_MAC_SHA1=d48920e2650321710b4d15d3acd9e277d59cd55b; PT_LINUX_SHA1=e1579b288a7ae4e9bc28dedec6a154d78b3c04ed   # (adb: installs and tests on a device)
SDL=3.4.16
SDL_SHA=7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68
FFMPEG=7.1.1
FFMPEG_SHA=733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1
API=29   # Android 10: every device with a Vulkan 1.1 driver worth having (the runtime's renderer is SDL_GPU on Vulkan)
G=https://dl.google.com/android/repository
case "$(uname -s)" in
  Darwin) HOST=darwin; NDK_ZIP=android-ndk-$NDK-darwin.zip; NDK_SHA1=$NDK_MAC_SHA1; BT_ZIP=build-tools_r${BT}_macosx.zip; BT_SHA1=$BT_MAC_SHA1; PT_ZIP=platform-tools_r$PT-darwin.zip; PT_SHA1=$PT_MAC_SHA1; NCPU=$(sysctl -n hw.ncpu) ;;
  Linux)  [[ $(uname -m) == x86_64 ]] || { echo "the NDK runs on x86-64 Linux only (this is $(uname -m))"; exit 1; }
          HOST=linux; NDK_ZIP=android-ndk-$NDK-linux.zip; NDK_SHA1=$NDK_LINUX_SHA1; BT_ZIP=build-tools_r${BT}_linux.zip; BT_SHA1=$BT_LINUX_SHA1; PT_ZIP=platform-tools_r$PT-linux.zip; PT_SHA1=$PT_LINUX_SHA1; NCPU=$(nproc) ;;
  *) echo "Android builds: from macOS or Linux"; exit 1 ;;
esac
D=${ATIV_ANDROID_TOOLCHAIN:-$HOME/toolchains/ativ-android}
mkdir -p "$D/dl"; cd "$D/dl"
avail=$(df -Pk "$D" | awk 'NR==2 {print int($4/1048576)}')
[[ -d "$D/ndk" ]] || (( avail >= 5 )) || { echo "only ${avail} GB free where the toolchain goes ($D): it needs about 5 GB while unpacking (ATIV_ANDROID_TOOLCHAIN=<a folder elsewhere>)"; exit 1; }
# a download's checksum against its pin above (sha256, or the sha1 Google's repository lists), so a changed archive stops the script
sum() { local a=$1 f=$2; if command -v sha${a}sum >/dev/null; then sha${a}sum "$f" | awk '{print $1}'; else shasum -a "$a" "$f" | awk '{print $1}'; fi; }
verify() { local h; h=$(sum "$3" "$1"); [[ $h == "$2" ]] && return; echo "checksum mismatch: $1 (expected $2, got $h)"; rm -f "$1"; exit 1; }
fetch() { [[ -f $2 ]] || { curl -fL --retry 3 -C - -o "$2.part" "$1" && verify "$2.part" "$3" "$4" && mv -f "$2.part" "$2"; }; }
fetch "$G/$NDK_ZIP" "$NDK_ZIP" "$NDK_SHA1" 1
fetch "$G/$BT_ZIP" "$BT_ZIP" "$BT_SHA1" 1
fetch "$G/platform-$PLAT.zip" "platform-$PLAT.zip" "$PLAT_SHA1" 1
fetch "$G/$PT_ZIP" "$PT_ZIP" "$PT_SHA1" 1
fetch "https://github.com/libsdl-org/SDL/releases/download/release-$SDL/SDL3-$SDL.tar.gz" "SDL3-$SDL.tar.gz" "$SDL_SHA" 256
fetch "https://ffmpeg.org/releases/ffmpeg-$FFMPEG.tar.xz" "ffmpeg-$FFMPEG.tar.xz" "$FFMPEG_SHA" 256
cd "$D"
unpack() {   # zip, where its one top folder goes
  [[ -d $2 ]] && return
  rm -rf unpack.tmp; mkdir unpack.tmp; unzip -q "dl/$1" -d unpack.tmp && mv unpack.tmp/*/ "$2" && rm -rf unpack.tmp
}
unpack "$NDK_ZIP" ndk
unpack "$BT_ZIP" build-tools
unpack "platform-$PLAT.zip" platform
unpack "$PT_ZIP" platform-tools
TC="$D/ndk/build/cmake/android.toolchain.cmake"
GEN=; command -v ninja >/dev/null && GEN="-G Ninja"
CM=(-DCMAKE_TOOLCHAIN_FILE="$TC" -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-$API -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_LIBDIR=lib)
if [[ ! -f SDL3/lib/libSDL3.so ]]; then
  rm -rf sdl-src sdl-build; mkdir sdl-src; tar xzf "dl/SDL3-$SDL.tar.gz" -C sdl-src --strip-components 1
  cmake -S sdl-src -B sdl-build $GEN "${CM[@]}" -DCMAKE_INSTALL_PREFIX="$D/SDL3" \
    -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF -DSDL_INSTALL_DOCS=OFF \
    -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-z,max-page-size=16384" > sdl-configure.log
  cmake --build sdl-build -j"$NCPU" > sdl-build.log 2>&1 && cmake --install sdl-build >> sdl-build.log 2>&1
  # SDL's activity (org.libsdl.app): the Java half of SDL3, compiled into every APK with the game's own activity on top
  mkdir -p SDL3/java && cp -R sdl-src/android-project/app/src/main/java/org SDL3/java/
fi
if [[ ! -f ffmpeg/lib/libavcodec.a ]]; then
  rm -rf ffmpeg-src; mkdir ffmpeg-src; tar xJf "dl/ffmpeg-$FFMPEG.tar.xz" -C ffmpeg-src --strip-components 1
  BIN=$(echo "$D"/ndk/toolchains/llvm/prebuilt/*/bin)
  ( cd ffmpeg-src && ./configure --prefix="$D/ffmpeg" --enable-cross-compile --target-os=android --arch=aarch64 --cpu=armv8-a \
      --cc="$BIN/aarch64-linux-android$API-clang" --cxx="$BIN/aarch64-linux-android$API-clang++" --ar="$BIN/llvm-ar" --nm="$BIN/llvm-nm" \
      --ranlib="$BIN/llvm-ranlib" --strip="$BIN/llvm-strip" --extra-cflags="-fPIC" \
      --enable-static --disable-shared --enable-pic --disable-everything --disable-programs --disable-doc --disable-network --disable-autodetect \
      --disable-avdevice --disable-avformat --disable-swscale --disable-swresample --disable-avfilter --disable-debug --disable-vulkan \
      --enable-decoder=h264 --enable-parser=h264 --enable-parser=hevc > ../ffmpeg-configure.log \
    && make -j"$NCPU" > ../ffmpeg-build.log 2>&1 && make install >> ../ffmpeg-build.log 2>&1 )
fi
mkdir -p ffmpeg/share/licenses
cp ffmpeg-src/LICENSE.md ffmpeg-src/COPYING.LGPLv2.1 ffmpeg/share/licenses/ 2>/dev/null || true
printf 'FFmpeg %s (LGPL 2.1 or later), unmodified: https://ffmpeg.org/releases/ffmpeg-%s.tar.xz\nbuilt by runtime/platform/android/setup-toolchain.sh with only the H.264 decoder and parsers enabled.\n' "$FFMPEG" "$FFMPEG" > ffmpeg/share/licenses/SOURCE.txt
ok() { [[ -e $1 ]] && echo built || echo MISSING; }
jv=$(javac -version 2>&1 | tail -1 || true)
echo "toolchain: $D (Android API $API, arm64-v8a; NDK $NDK $(ok ndk/build/cmake/android.toolchain.cmake); build tools $BT $(ok build-tools/aapt2); platform $PLAT $(ok platform/android.jar); adb $(ok platform-tools/adb); SDL3 $SDL $(ok SDL3/lib/libSDL3.so); FFmpeg $FFMPEG $(ok ffmpeg/lib/libavcodec.a); javac: ${jv:-none -- install a JDK to package APKs})"
