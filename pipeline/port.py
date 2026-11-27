"""port.py: a game made for a phone, handheld or tablet -- `vitarecomp port <title> <android|ios> [--no-data]` builds the
game's program for the device (runtime/build.py TARGET=android|ios) and then packs it here:

  android   <library>/ports/android/<title>/
              Encore-<title>-b<N>.apk      the game's code and SDL (an APK of its own per game: <package> below), debug-signed
                                           with <library>/ports/android/encore-debug.keystore -- keep it, or a newer APK won't
                                           install over an older one
              data/                        its data folder (runtime/platform/mobile_main.c): copied to the device's
                                           Android/data/<package>/files/ -- USB file transfer, or `adb push data/. <that>`
  ios       <library>/ports/ios/<title>/
              Encore-<title>-b<N>.ipa / .tipa   the app, ad hoc signed with the entitlements a big game needs (TrollStore
                                           keeps them; SideStore and AltStore re-sign without them), its data folder inside
                                           (--no-data: without -- the data folder goes in Files > On My iPhone > <app> > game)

The newest of each is copied to ~/Downloads/Encore too (ENCORE_PORT_OUT: elsewhere), to AirDrop or install from there.
Everything made here is the player's own game -- code and data -- for their own devices: never shared.
"""
import json
import os
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import zipfile

R = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(R)


def say(s): print(s, flush=True)


def die(s): say(f"port: {s}"); sys.exit(1)


def run(argv, **kw):
    r = subprocess.run([str(a) for a in argv], **kw)
    if r.returncode and kw.get("capture_output"): sys.stdout.write((r.stdout or b"").decode(errors="replace")[-4000:] + (r.stderr or b"").decode(errors="replace")[-4000:])
    if r.returncode: die(f"{os.path.basename(str(argv[0]))} failed ({r.returncode}): " + " ".join(str(a) for a in argv[1:])[:400])
    return r


def package_id(title): return "io.github.bittahbandit1.encore." + re.sub(r"[^a-z0-9_]", "_", title.lower())


def build_number(d):
    """one counter per target (<library>/ports/<target>/build-number): every APK or IPA made gets the next, so two builds are
    never mistaken for each other"""
    f = os.path.join(d, "build-number")
    try: n = int(open(f).read().strip()) + 1
    except (OSError, ValueError): n = 1
    with open(f, "w") as fh: fh.write(f"{n}\n")
    return n


def sync_tree(src, dst, skip=()):
    """src copied into dst, links followed; a file only when its size or time differs (a second port copies only what
    changed), and what dst has that src doesn't removed"""
    os.makedirs(dst, exist_ok=True)
    names = set()
    for e in sorted(os.listdir(src)):
        if e in skip or e.endswith(".elf"): continue   # (the decrypter's ELFs beside the game's SELFs: the recompiler's, not the game's)
        s, d = os.path.join(src, e), os.path.join(dst, e); names.add(e)
        if os.path.isdir(s): sync_tree(s, d); continue
        st = os.stat(s)
        try: dt = os.stat(d)
        except OSError: dt = None
        if dt and dt.st_ino == st.st_ino and dt.st_dev == st.st_dev: continue
        # a hard link where the library and the game's files share a disk (they do, as a rule): no second copy of gigabytes
        try:
            if os.path.lexists(d + ".part"): os.remove(d + ".part")
            os.link(s, d + ".part"); os.replace(d + ".part", d); continue
        except OSError: pass
        if dt and dt.st_size == st.st_size and int(dt.st_mtime) == int(st.st_mtime): continue
        shutil.copyfile(s, d + ".part"); os.replace(d + ".part", d); os.utime(d, (st.st_atime, st.st_mtime))
    for e in os.listdir(dst):
        if e not in names:
            p = os.path.join(dst, e)
            shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)


def data_folder(game, dst):
    """the data folder mobile_main.c starts from: launch.ini, the program's and modules' images, the shipped shader recipes,
    and the game's read-only devices (fs/app0, fs/addcont0: the links import made)"""
    os.makedirs(dst, exist_ok=True)
    lines = [f"title={game['title']}", f"name={game['name']}", f"image={os.path.basename(game['image'])}", f"entry={game['entry']}"]
    if game["modules"]: lines.append("modules=" + ",".join(os.path.basename(m) for m in game["modules"]))
    lines += [f"env={k}={v}" for k, v in game["env"]]
    files = [game["image"]] + game["modules"] + ([game["shaders"]] if game["shaders"] else [])
    keep = {"launch.ini", "fs"}
    for f in files:
        d = os.path.join(dst, os.path.basename(f)); keep.add(os.path.basename(f))
        st = os.stat(f)
        if not (os.path.isfile(d) and os.stat(d).st_size == st.st_size and int(os.stat(d).st_mtime) == int(st.st_mtime)):
            shutil.copyfile(f, d); os.utime(d, (st.st_atime, st.st_mtime))
    fs = os.path.join(game["out"], "fs"); devs = []
    say(f"  data: {fs}: " + (", ".join(sorted(os.listdir(fs))) if os.path.isdir(fs) else "none"))
    for dev in sorted(os.listdir(fs)) if os.path.isdir(fs) else []:
        p = os.path.join(fs, dev)
        # the game's own read-only devices (app0: the game, addcont0: its add-ons), and any other the import linked in; the
        # rest (ux0, savedata0...) is the desktop's play -- saves, not the game's data
        if os.path.isdir(p) and (dev in ("app0", "addcont0") or os.path.islink(p)):
            say(f"  data: fs/{dev}"); sync_tree(p, os.path.join(dst, "fs", dev)); devs.append(dev)
    for dev in os.listdir(os.path.join(dst, "fs")) if os.path.isdir(os.path.join(dst, "fs")) else []:
        if dev not in devs: shutil.rmtree(os.path.join(dst, "fs", dev))
    for e in os.listdir(dst):
        if e not in keep: p = os.path.join(dst, e); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    with open(os.path.join(dst, "launch.ini"), "w", encoding="utf-8", newline="\n") as f: f.write("\n".join(lines) + "\n")
    return dst


def tree_size(p):
    n = 0
    for dp, _, fs in os.walk(p):
        for f in fs: n += os.path.getsize(os.path.join(dp, f))
    return n


def pub_dir():
    out = os.environ.get("ENCORE_PORT_OUT") or os.path.join(os.path.expanduser("~"), "Downloads", "Encore")
    os.makedirs(out, exist_ok=True)
    return out


def publish(path, prefix):
    """the newest build in ~/Downloads/Encore: a hard link where it can be (no second copy), the older ones of the same
    game and target removed there"""
    out = pub_dir(); d = os.path.join(out, os.path.basename(path))
    for old in os.listdir(out):
        if old.startswith(prefix) and os.path.splitext(old)[1] == os.path.splitext(path)[1] and old != os.path.basename(path): os.remove(os.path.join(out, old))
    if os.path.lexists(d): os.remove(d)
    try: os.link(path, d)
    except OSError: shutil.copyfile(path, d)
    return d


def free_gb(p):
    st = os.statvfs(p); return st.f_bavail * st.f_frsize / 1073741824


# ---- Android

def java_tool(name):
    jh = os.environ.get("JAVA_HOME")
    if not jh and sys.platform == "darwin":
        r = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True); jh = r.stdout.strip() if r.returncode == 0 else ""
    p = os.path.join(jh, "bin", name) if jh else shutil.which(name)
    if not p or not os.path.isfile(p): die(f"no {name}: install a JDK (17 or newer) -- it compiles SDL's Java half and signs the APK")
    return p


def android(game, prog, dest, with_data=True):
    at = os.environ.get("ATIV_ANDROID_TOOLCHAIN") or os.path.join(os.path.expanduser("~"), "toolchains", "ativ-android")
    bt, plat, sdl = os.path.join(at, "build-tools"), os.path.join(at, "platform", "android.jar"), os.path.join(at, "SDL3")
    for p in (bt, plat, os.path.join(sdl, "java")):
        if not os.path.exists(p): die(f"no {p}: run runtime/platform/android/setup-toolchain.sh")
    os.makedirs(dest, exist_ok=True)
    work = os.path.join(dest, "apk-work"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    n = build_number(os.path.dirname(dest)); pkg = package_id(game["title"])
    javac, keytool = java_tool("javac"), java_tool("keytool")
    jenv = dict(os.environ); jenv["PATH"] = os.path.dirname(javac) + os.pathsep + jenv.get("PATH", "")
    # SDL's activity as it ships: it loads libSDL3.so and libmain.so (this game) and calls SDL_main
    label = game["name"].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{pkg}"
    android:versionCode="{n}" android:versionName="b{n}" android:installLocation="auto">
  <uses-feature android:glEsVersion="0x00020000"/>
  <uses-feature android:name="android.hardware.vulkan.version" android:version="0x401000" android:required="true"/>
  <uses-feature android:name="android.hardware.touchscreen" android:required="false"/>
  <uses-feature android:name="android.hardware.gamepad" android:required="false"/>
  <uses-feature android:name="android.software.leanback" android:required="false"/>
  <uses-permission android:name="android.permission.INTERNET"/>
  <uses-permission android:name="android.permission.VIBRATE"/>
  <application android:label="{label}" android:icon="@mipmap/ic_launcher" android:allowBackup="false" android:hardwareAccelerated="true"
      android:extractNativeLibs="true" android:appCategory="game" android:isGame="true" android:largeHeap="true"
      android:theme="@android:style/Theme.Black.NoTitleBar.Fullscreen">
    <activity android:name="org.libsdl.app.SDLActivity" android:exported="true" android:label="{label}"
        android:screenOrientation="sensorLandscape" android:launchMode="singleInstance" android:alwaysRetainTaskState="true"
        android:configChanges="layoutDirection|locale|orientation|uiMode|screenLayout|screenSize|smallestScreenSize|keyboard|keyboardHidden|navigation"
        android:preferMinimalPostProcessing="true" android:resizeableActivity="false">
      <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/>
        <category android:name="android.intent.category.LEANBACK_LAUNCHER"/></intent-filter>
    </activity>
    <profileable android:shell="true"/>
  </application>
</manifest>
'''
    with open(os.path.join(work, "AndroidManifest.xml"), "w", encoding="utf-8") as f: f.write(manifest)
    res = os.path.join(work, "res", "mipmap-xxxhdpi"); os.makedirs(res)
    shutil.copyfile(os.path.join(ROOT, "assets", "brand", "png", "icon-256.png"), os.path.join(res, "ic_launcher.png"))
    # Java: SDL's sources against the platform's android.jar, then dex
    srcs = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(sdl, "java")) for f in fs if f.endswith(".java"))
    classes = os.path.join(work, "classes"); os.makedirs(classes)
    run([javac, "-nowarn", "-encoding", "UTF-8", "-source", "11", "-target", "11", "-cp", plat, "-d", classes] + srcs, env=jenv, capture_output=True)
    cls = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(classes) for f in fs if f.endswith(".class"))
    d8 = os.path.join(bt, "d8")
    run([d8, "--release", "--min-api", "29", "--lib", plat, "--output", work] + cls, env=jenv)
    aapt2 = os.path.join(bt, "aapt2")
    run([aapt2, "compile", "--dir", os.path.join(work, "res"), "-o", os.path.join(work, "res.zip")])
    unsigned = os.path.join(work, "unsigned.apk")
    run([aapt2, "link", "-o", unsigned, "-I", plat, "--manifest", os.path.join(work, "AndroidManifest.xml"), "--min-sdk-version", "29",
         "--target-sdk-version", "35", "--version-code", n, "--version-name", f"b{n}", os.path.join(work, "res.zip")])
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(work, "classes.dex"), "classes.dex")
        z.write(prog, "lib/arm64-v8a/libmain.so")
        z.write(os.path.join(sdl, "lib", "libSDL3.so"), "lib/arm64-v8a/libSDL3.so")
    aligned = os.path.join(work, "aligned.apk")
    run([os.path.join(bt, "zipalign"), "-f", "-P", "16", "4", unsigned, aligned])
    ks = os.path.join(os.path.dirname(dest), "encore-debug.keystore")
    if not os.path.isfile(ks):   # (made once: an APK signed with another key won't install over this one)
        run([keytool, "-genkeypair", "-keystore", ks, "-storepass", "android", "-keypass", "android", "-alias", "encore", "-keyalg", "RSA",
             "-keysize", "2048", "-validity", "10000", "-dname", "CN=Encore (debug)"], env=jenv, capture_output=True)
    apk = os.path.join(dest, f"Encore-{game['title']}-b{n}.apk")
    run([os.path.join(bt, "apksigner"), "sign", "--ks", ks, "--ks-pass", "pass:android", "--key-pass", "pass:android", "--ks-key-alias", "encore",
         "--v4-signing-enabled", "false", "--out", apk, aligned], env=jenv)
    for old in os.listdir(dest):   # (the earlier builds' APKs: the newest stays)
        if old.endswith(".apk") and old != os.path.basename(apk): os.remove(os.path.join(dest, old))
    shutil.rmtree(work, ignore_errors=True)
    pub = publish(apk, f"Encore-{game['title']}-b")
    say(f"android: {apk} ({os.path.getsize(apk) / 1048576:.0f} MB, package {pkg}, build {n}); also {pub}")
    if with_data:
        d = data_folder(game, os.path.join(dest, "data"))
        say(f"android: data folder {d} ({tree_size(d) / 1073741824:.2f} GB): copy what's IN it to the device's "
            f"Android/data/{pkg}/files/ (USB file transfer, or: adb push \"{d}/.\" /sdcard/Android/data/{pkg}/files/)")
    with open(os.path.join(dest, "port.json"), "w") as f: json.dump({"package": pkg, "build": n, "apk": apk, "data": os.path.join(dest, "data"), "out": game["out"]}, f)
    return apk


# ---- iOS

def xcrun(*a):
    r = subprocess.run(["xcrun"] + list(a), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def ios(game, prog, dest, with_data=True):
    if sys.platform != "darwin": die("iOS apps: on a Mac")
    os.makedirs(dest, exist_ok=True)
    n = build_number(os.path.dirname(dest)); bid = package_id(game["title"])
    minos = os.environ.get("ATIV_IOS_MIN") or "15.0"
    work = os.path.join(dest, "ipa-work"); shutil.rmtree(work, ignore_errors=True)
    for old in os.listdir(dest):   # (the earlier builds first: the room for this one)
        if old.endswith((".ipa", ".tipa", ".part")): os.remove(os.path.join(dest, old))
    for old in os.listdir(pub_dir()):
        if old.startswith(f"Encore-{game['title']}-b") and old.endswith((".ipa", ".tipa")): os.remove(os.path.join(pub_dir(), old))
    need = (tree_size(os.path.join(game["out"], "fs", "app0")) / 1073741824 if with_data else 0) + 0.5
    if free_gb(dest) < need: die(f"only {free_gb(dest):.1f} GB free; the IPA needs about {need:.1f} GB (--no-data: without the game's data, a few MB)")
    app = os.path.join(work, "Payload", "Encore.app"); os.makedirs(app)
    exe = os.path.join(app, "Encore"); shutil.copyfile(prog, exe); os.chmod(exe, 0o755)
    # iOS 27's rule for an app linked against its SDK: the UIScene life cycle, which SDL's app delegate doesn't adopt yet; the
    # SDK the executable records set back to 26.0, as an Xcode 26 build would carry (the check reads only that)
    sdkv = xcrun("--sdk", "iphoneos", "--show-sdk-version")
    if sdkv and int(sdkv.split(".")[0]) >= 27:
        run(["xcrun", "vtool", "-set-build-version", "ios", minos, "26.0", "-replace", "-output", exe, exe])
    for size, name in ((120, "AppIcon60x60@2x.png"), (180, "AppIcon60x60@3x.png"), (152, "AppIcon76x76@2x~ipad.png"), (167, "AppIcon83.5x83.5@2x~ipad.png")):
        run(["sips", "-z", size, size, os.path.join(ROOT, "assets", "brand", "png", "icon-256.png"), "--out", os.path.join(app, name)], capture_output=True)
    short = game.get("short") or game["name"]
    info = {
        "CFBundleIdentifier": bid, "CFBundleExecutable": "Encore", "CFBundleName": short[:15], "CFBundleDisplayName": short,
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "1.0", "CFBundleVersion": str(n), "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleSupportedPlatforms": ["iPhoneOS"], "DTPlatformName": "iphoneos", "DTSDKName": f"iphoneos{sdkv}", "MinimumOSVersion": minos,
        "UIDeviceFamily": [1, 2], "UIRequiredDeviceCapabilities": ["arm64", "metal"], "LSRequiresIPhoneOS": True,
        "UISupportedInterfaceOrientations": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
        "UISupportedInterfaceOrientations~ipad": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
        "UIRequiresFullScreen": True, "UIStatusBarHidden": True, "UIViewControllerBasedStatusBarAppearance": False,
        "UILaunchScreen": {"UIColorName": ""},   # (a launch screen: without one iOS runs the app letterboxed at an old phone's size)
        "UIFileSharingEnabled": True, "LSSupportsOpeningDocumentsInPlace": True,   # (Documents in the Files app: saves, logs, a data folder put there)
        "UIApplicationSupportsIndirectInputEvents": True, "GCSupportsControllerUserInteraction": True,
        "GCSupportedGameControllers": [{"ProfileName": "ExtendedGamepad"}], "UIBackgroundModes": [],
        "CFBundleIcons": {"CFBundlePrimaryIcon": {"CFBundleIconFiles": ["AppIcon60x60"], "CFBundleIconName": "AppIcon"}},
        "CFBundleIcons~ipad": {"CFBundlePrimaryIcon": {"CFBundleIconFiles": ["AppIcon60x60", "AppIcon76x76", "AppIcon83.5x83.5"], "CFBundleIconName": "AppIcon"}},
        "NSLocalNetworkUsageDescription": "Online play finds other players on your network.",
    }
    with open(os.path.join(app, "Info.plist"), "wb") as f: plistlib.dump(info, f)
    if with_data:
        d = data_folder(game, os.path.join(dest, "data"))
        say(f"ios: data {tree_size(d) / 1073741824:.2f} GB into the app")
        def link_or_copy(s, t):   # (hard links: the same disk, no second copy of gigabytes)
            try: os.link(s, t)
            except OSError: shutil.copy2(s, t)
        shutil.copytree(d, os.path.join(app, "game"), copy_function=link_or_copy)
    # the entitlements a 4 GB guest address space and a big game need: TrollStore keeps them (SideStore and AltStore can't);
    # get-task-allow: a debugger and a crash log with symbols
    ent = os.path.join(work, "entitlements.plist")
    with open(ent, "wb") as f:
        plistlib.dump({"com.apple.developer.kernel.extended-virtual-addressing": True, "com.apple.developer.kernel.increased-memory-limit": True,
                       "get-task-allow": True, "application-identifier": bid}, f)
    run(["codesign", "-f", "-s", "-", "--entitlements", ent, "--timestamp=none", "--generate-entitlement-der", app])
    base = f"Encore-{game['title']}-b{n}" + ("" if with_data else "-nodata")
    ipa = os.path.join(dest, base + ".ipa")
    with zipfile.ZipFile(ipa + ".part", "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for dp, dns, fs in os.walk(os.path.join(work, "Payload")):
            for f in sorted(fs):
                p = os.path.join(dp, f); arc = os.path.relpath(p, work)
                zi = zipfile.ZipInfo.from_file(p, arc)
                big = os.path.getsize(p) > (8 << 20) and "/game/" in "/" + arc   # (the game's data stored: it's mostly compressed already)
                zi.compress_type = zipfile.ZIP_STORED if big else zipfile.ZIP_DEFLATED
                with open(p, "rb") as src, z.open(zi, "w", force_zip64=True) as dst: shutil.copyfileobj(src, dst, 1 << 22)
    os.replace(ipa + ".part", ipa)
    shutil.rmtree(work, ignore_errors=True)
    tipa = os.path.join(dest, base + ".tipa")   # (TrollStore opens a .tipa straight from AirDrop: the same file, linked)
    try: os.link(ipa, tipa)
    except OSError: shutil.copyfile(ipa, tipa)
    pub = publish(tipa, f"Encore-{game['title']}-b{n}.t"); publish(ipa, f"Encore-{game['title']}-b{n}.i")
    say(f"ios: {ipa} ({os.path.getsize(ipa) / 1048576:.0f} MB, {bid}, build {n}); also {pub} and the .ipa beside it")
    return ipa
