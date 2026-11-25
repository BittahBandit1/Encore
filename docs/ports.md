# Phones, handhelds and tablets

Encore builds a game for Android (arm64) and iOS/iPadOS on the computer that has the game, from the same recompiled
code the desktop build uses. Each player makes their own port from their own copy, for their own devices: a port
holds the game's code and data and is never shared.

## Toolchains (once)

| | needs | sets up |
|---|---|---|
| Android | macOS or x86-64 Linux, a JDK 17+, cmake, ninja | `runtime/platform/android/setup-toolchain.sh`: the NDK, the SDK's build tools, a platform's `android.jar`, adb, SDL3 and FFmpeg's H.264 decoder in `~/toolchains/ativ-android` (about 3.5 GB) |
| iOS | a Mac with Xcode and its iOS platform, cmake, ninja | `runtime/platform/ios/setup-toolchain.sh`: SDL3, SPIRV-Cross and FFmpeg for iOS in `~/toolchains/ativ-ios` |

`ATIV_ANDROID_TOOLCHAIN` / `ATIV_IOS_TOOLCHAIN` put them elsewhere. Every download is checked against a pinned checksum.

## Making a port

```sh
vitarecomp port PCSE01274 android          # APK + data folder
vitarecomp port PCSE01274 ios              # IPA/TIPA with the data inside
vitarecomp port PCSE01274 ios --no-data    # IPA without the data (SideStore/AltStore: smaller to sideload)
```

The game must be recompiled already (`vitarecomp add` or `recompile`). The port lands in
`<library>/ports/<android|ios>/<title>/`, and the newest APK or IPA/TIPA is copied to `~/Downloads/Encore`.
Each build is numbered (`-b<N>`).

### Android

- Install the APK. Each game is its own app (`io.github.bittahbandit1.encore.<title>`), signed with
  `<library>/ports/android/encore-debug.keystore`. Keep that file: an APK signed with another key won't install over
  an older one.
- Copy what's in the port's `data` folder into the device's `Android/data/<package>/files/`: USB file transfer works,
  or `adb push data/. /sdcard/Android/data/<package>/files/`. `pipeline/port_device.py push <title>` copies only the files
  that changed.
- Saves, settings, shader caches and `session.log` are written in that same folder.
- Rendering is SDL_GPU on Vulkan. API 29 (Android 10) or newer, arm64.

### iOS / iPadOS

- The `.tipa` installs with TrollStore and keeps the entitlements a big game needs: extended virtual addressing for the
  Vita's 4 GB address space, and the increased memory limit. SideStore and AltStore re-sign the app without them. A
  game may still run that way on a device with plenty of memory, but it isn't supported.
- With `--no-data`, put the port's `data` folder in Files > On My iPhone > (the app), and name it `game`.
- The app's Documents folder holds the saves, settings, shader caches and `session.log`. It is visible in the Files
  app and in Finder.
- iOS 15 or newer, arm64 (A9 and later). Rendering is SDL_GPU on Metal, through the same SPIR-V to MSL translator as
  the Mac.

## Playing on a touch screen

With no controller connected, a touch controller is drawn over the picture: d-pad, face buttons, L and R, Select and
Start, and a menu button at the top. It disappears when a controller connects. Setting `touch_controls` changes this:
`auto` (the default on a phone), `on` or `off` (the default on desktop). Touches anywhere else go to the Vita's
touch screen.

## Testing on a device from the computer

`pipeline/port_device.py` drives an Android device over adb (USB, or Wi-Fi after pairing):

```sh
pipeline/port_device.py devices | connect <host:port>
pipeline/port_device.py install|push|start|stop <title>
pipeline/port_device.py log <title> [file]    # the game's session.log and logcat
pipeline/port_device.py shot <title> out.png  # the screen
```

## How it fits together

- `runtime/build.py` with `TARGET=android` builds `libmain.so` with the NDK's clang (`-march=armv8.2-a`, 16 KB page
  alignment). With `TARGET=ios` it builds an arm64 executable against the iPhoneOS SDK with SDL3 static.
- `runtime/platform/mobile_main.c` is the start on both (`SDL_main`). It finds the data folder and its `launch.ini`
  (the title, the image and entry, the modules, the run settings), makes the writable work folder the current
  directory, links each of the data folder's devices (`fs/app0`, `fs/addcont0`) into it, then calls the desktop's
  `main`.
- `pipeline/port.py` packs it: an APK built without Gradle (SDL's Java activity compiled with javac and d8, aapt2,
  zipalign, apksigner), or the app bundle (Info.plist, icons, ad hoc signature with the entitlements, zip).
