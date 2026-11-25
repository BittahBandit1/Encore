#!/bin/bash
# The iOS toolchain, pinned: what an iPhone or iPad build needs (TARGET=ios, runtime/build.py; pipeline/port.py makes the
# app). The same libraries as the Mac's (runtime/platform/macos/setup-toolchain.sh), built for iOS arm64 and static (an
# app's executable carries them): SDL3, SPIRV-Cross's C API (the SPIR-V to Metal translator: the same release, so the
# Metal source matches the Mac's), FFmpeg's H.264 decoder. Into $ATIV_IOS_TOOLCHAIN (default ~/toolchains/ativ-ios).
# Needs Xcode with its iOS platform (the iPhoneOS SDK: Xcode > Settings > Components), cmake and ninja.
set -euo pipefail
SDL=3.4.16
SDL_SHA=7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68
SPIRV_CROSS=vulkan-sdk-1.4.363.0
SPIRV_CROSS_SHA=f708982e88b763ef5b0394ed468fc2c3628f68cdab89f2e7a946cd628c04e721
FFMPEG=7.1.1
FFMPEG_SHA=733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1
MIN=${ATIV_IOS_MIN:-15.0}   # iOS 15: the iPhone 6s and the iPod touch 7 among the oldest (A9, A10); MTLBinaryArchive is 14.0
[[ $(uname -s) == Darwin ]] || { echo "iOS builds: on a Mac with Xcode"; exit 1; }
SDK=$(xcrun --sdk iphoneos --show-sdk-path 2>/dev/null) || { echo "no iPhoneOS SDK: install Xcode and its iOS platform (Xcode > Settings > Components)"; exit 1; }
D=${ATIV_IOS_TOOLCHAIN:-$HOME/toolchains/ativ-ios}
mkdir -p "$D/dl"; cd "$D/dl"
verify() { local h; h=$(shasum -a 256 "$1" | awk '{print $1}'); [[ $h == "$2" ]] && return; echo "checksum mismatch: $1 (expected $2, got $h)"; rm -f "$1"; exit 1; }
fetch() { [[ -f $2 ]] || { curl -fL --retry 3 -o "$2.part" "$1" && verify "$2.part" "$3" && mv -f "$2.part" "$2"; }; }
fetch "https://github.com/libsdl-org/SDL/releases/download/release-$SDL/SDL3-$SDL.tar.gz" "SDL3-$SDL.tar.gz" "$SDL_SHA"
fetch "https://github.com/KhronosGroup/SPIRV-Cross/archive/refs/tags/$SPIRV_CROSS.tar.gz" "SPIRV-Cross-$SPIRV_CROSS.tar.gz" "$SPIRV_CROSS_SHA"
fetch "https://ffmpeg.org/releases/ffmpeg-$FFMPEG.tar.xz" "ffmpeg-$FFMPEG.tar.xz" "$FFMPEG_SHA"
cd "$D"
[[ $(cat min 2>/dev/null) == "$MIN" ]] || rm -rf SDL3 spirv-cross ffmpeg   # (built for another minimum iOS: again)
GEN=; command -v ninja >/dev/null && GEN="-G Ninja"
CM=(-DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_DEPLOYMENT_TARGET=$MIN
    -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO)
NCPU=$(sysctl -n hw.ncpu)
if [[ ! -f SDL3/lib/libSDL3.a ]]; then
  rm -rf sdl-src sdl-build; mkdir sdl-src; tar xzf "dl/SDL3-$SDL.tar.gz" -C sdl-src --strip-components 1
  cmake -S sdl-src -B sdl-build $GEN "${CM[@]}" -DCMAKE_INSTALL_PREFIX="$D/SDL3" \
    -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF -DSDL_INSTALL_DOCS=OFF -DSDL_TEST_LIBRARY=OFF > sdl-configure.log
  cmake --build sdl-build -j"$NCPU" > sdl-build.log 2>&1 && cmake --install sdl-build >> sdl-build.log 2>&1
fi
if [[ ! -f spirv-cross/lib/libspirv-cross-c.a ]]; then
  rm -rf spirv-src spirv-build; mkdir spirv-src; tar xzf "dl/SPIRV-Cross-$SPIRV_CROSS.tar.gz" -C spirv-src --strip-components 1
  cmake -S spirv-src -B spirv-build $GEN "${CM[@]}" -DCMAKE_INSTALL_PREFIX="$D/spirv-cross" \
    -DSPIRV_CROSS_SHARED=OFF -DSPIRV_CROSS_STATIC=ON -DSPIRV_CROSS_CLI=OFF -DSPIRV_CROSS_ENABLE_TESTS=OFF > spirv-configure.log
  cmake --build spirv-build -j"$NCPU" > spirv-build.log 2>&1 && cmake --install spirv-build >> spirv-build.log 2>&1
fi
if [[ ! -f ffmpeg/lib/libavcodec.a ]]; then
  rm -rf ffmpeg-src; mkdir ffmpeg-src; tar xJf "dl/ffmpeg-$FFMPEG.tar.xz" -C ffmpeg-src --strip-components 1
  CC=$(xcrun --sdk iphoneos --find clang)
  F="-arch arm64 -isysroot $SDK -miphoneos-version-min=$MIN"
  ( cd ffmpeg-src && ./configure --prefix="$D/ffmpeg" --enable-cross-compile --target-os=darwin --arch=aarch64 --cc="$CC" \
      --extra-cflags="$F" --extra-ldflags="$F" --sysroot="$SDK" \
      --enable-static --disable-shared --enable-pic --disable-everything --disable-programs --disable-doc --disable-network --disable-autodetect \
      --disable-avdevice --disable-avformat --disable-swscale --disable-swresample --disable-avfilter --disable-debug \
      --enable-decoder=h264 --enable-parser=h264 --enable-parser=hevc > ../ffmpeg-configure.log \
    && make -j"$NCPU" > ../ffmpeg-build.log 2>&1 && make install >> ../ffmpeg-build.log 2>&1 )
fi
mkdir -p spirv-cross/share/licenses ffmpeg/share/licenses
cp spirv-src/LICENSE spirv-cross/share/licenses/LICENSE 2>/dev/null || true
cp ffmpeg-src/LICENSE.md ffmpeg-src/COPYING.LGPLv2.1 ffmpeg/share/licenses/ 2>/dev/null || true
printf 'FFmpeg %s (LGPL 2.1 or later), unmodified: https://ffmpeg.org/releases/ffmpeg-%s.tar.xz\nbuilt by runtime/platform/ios/setup-toolchain.sh with only the H.264 decoder and parsers enabled.\n' "$FFMPEG" "$FFMPEG" > ffmpeg/share/licenses/SOURCE.txt
ok() { [[ -f $1 ]] && echo built || echo MISSING; }
echo "toolchain: $D (iOS $MIN, arm64, SDK $(xcrun --sdk iphoneos --show-sdk-version); SDL3 $SDL $(ok SDL3/lib/libSDL3.a); SPIRV-Cross $SPIRV_CROSS $(ok spirv-cross/lib/libspirv-cross-c.a); FFmpeg $FFMPEG $(ok ffmpeg/lib/libavcodec.a))"
echo "$MIN" > "$D/min"
