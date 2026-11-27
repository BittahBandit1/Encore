"""port_device.py: an Android port on a device over adb (the Android toolchain's platform-tools) -- for testing a port
from the computer that made it, a phone or handheld plugged in or paired for wireless debugging.

  port_device.py devices                       the devices adb sees
  port_device.py connect <host:port>           a device over Wi-Fi (Developer options > Wireless debugging; paired once)
  port_device.py install <title>               the newest APK `vitarecomp port <title> android` made
  port_device.py push <title>                  its data folder into the app's folder (only files that changed)
  port_device.py start|stop <title>            the app
  port_device.py log <title> [out]             the game's session.log (and logcat's last lines): printed, and copied to out
  port_device.py shot <title> <out.png>        the screen
"""
import json
import os
import re
import subprocess
import sys
import time

R = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, R)
from datadir import library_dir  # noqa: E402
from port import package_id  # noqa: E402

ROOT = os.path.dirname(R)
AT = os.environ.get("ATIV_ANDROID_TOOLCHAIN") or os.path.join(os.path.expanduser("~"), "toolchains", "ativ-android")
ADB = os.path.join(AT, "platform-tools", "adb")


def adb(*a, check=True, capture=False, timeout=600):
    r = subprocess.run([ADB] + [str(x) for x in a], capture_output=capture, timeout=timeout)
    if check and r.returncode: print(f"adb {' '.join(str(x) for x in a)[:200]}: failed ({r.returncode})"); sys.exit(1)
    return r


def info(title):
    f = os.path.join(library_dir(ROOT), "ports", "android", title, "port.json")
    if not os.path.isfile(f): print(f"{title}: no Android port yet (vitarecomp port {title} android)"); sys.exit(1)
    return json.load(open(f))


def remote_dir(pkg): return f"/sdcard/Android/data/{pkg}/files"


def push(title):
    """the data folder, file by file where size differs (adb push of gigabytes each time is minutes)"""
    p = info(title); pkg = p["package"]; d = p["data"]; rd = remote_dir(pkg)
    adb("shell", "mkdir", "-p", rd)
    r = adb("shell", f"cd {rd} && find . -type f -exec stat -c '%s %n' {{}} +", capture=True, check=False)
    have = {}
    for line in (r.stdout or b"").decode(errors="replace").splitlines():
        m = re.match(r"(\d+) \./(.*)", line)
        if m: have[m[2]] = int(m[1])
    n = sent = 0
    for dp, _, fs in os.walk(d):
        for f in fs:
            lp = os.path.join(dp, f); rel = os.path.relpath(lp, d).replace(os.sep, "/"); sz = os.path.getsize(lp)
            if have.get(rel) == sz: continue
            adb("push", lp, f"{rd}/{rel}", capture=True); n += 1; sent += sz
    print(f"push: {n} files, {sent / 1048576:.0f} MB to {rd}")
    # the desktop's saves (its fs/ folders other than the game's own: savedata0...), to a device that has none of its own
    # yet -- the first push carries the player's progress over; after that the device's saves are its own and never replaced
    fs = os.path.join(p.get("out", ""), "fs")
    for dev in sorted(os.listdir(fs)) if os.path.isdir(fs) else []:
        lp = os.path.join(fs, dev)
        if dev in ("app0", "addcont0") or os.path.islink(lp) or not os.path.isdir(lp): continue
        # once per device: a save the device made before this computer's came over is set aside (fs/<dev>.device-backup, kept),
        # then this computer's copied in; after that (the backup there) the device's saves are its own and never replaced
        r = adb("shell", f"ls {rd}/fs/{dev} >/dev/null 2>&1 && echo have; ls -d {rd}/fs/{dev}.device-backup >/dev/null 2>&1 && echo backed", capture=True, check=False)
        o = r.stdout or b""
        if b"backed" in o: print(f"saves: fs/{dev} on the device is its own (this computer's came over before): left as it is"); continue
        adb("shell", "mkdir", "-p", f"{rd}/fs")
        if b"have" in o: adb("shell", "mv", f"{rd}/fs/{dev}", f"{rd}/fs/{dev}.device-backup"); print(f"saves: the device's fs/{dev} kept as fs/{dev}.device-backup")
        else: adb("shell", "mkdir", "-p", f"{rd}/fs/{dev}.device-backup")
        adb("push", lp, f"{rd}/fs/", capture=True)
        print(f"saves: fs/{dev} copied from this computer")
    # (what adb wrote is the shell's; Android 11+ lets the app at its own folder's files only where the mode allows)
    adb("shell", f"chmod -R a+rwX {rd} 2>&1 | head -3; ls -lnR {rd} | head -40; id", check=False)


def main(argv):
    if not os.path.isfile(ADB): print(f"no adb at {ADB}: run runtime/platform/android/setup-toolchain.sh"); return 1
    if not argv: print(__doc__); return 1
    a = argv[0]
    if a == "devices": adb("devices", "-l"); return 0
    if a == "connect":
        if len(argv) < 2 or not re.fullmatch(r"[\w.-]+:\d{1,5}", argv[1]): print("connect <host:port>"); return 1
        adb("connect", argv[1]); return 0
    if len(argv) < 2: print(__doc__); return 1
    title = argv[1]; p = info(title); pkg = p["package"]
    if a == "install": adb("install", "-r", "-d", p["apk"]); print(f"installed {os.path.basename(p['apk'])}")
    elif a == "push": push(title)
    elif a == "start":
        adb("shell", "am", "force-stop", pkg); adb("logcat", "-c", check=False)
        adb("shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1", capture=True); print(f"started {pkg}")
    elif a == "stop": adb("shell", "am", "force-stop", pkg); print(f"stopped {pkg}")
    elif a == "env":   # the next launch's extra settings (mobile_main.c reads launch_env.txt): the file the runner checked, empty clears
        if len(argv) < 3 or not os.path.isfile(argv[2]): print("env <title> <file>"); return 1
        rd = remote_dir(pkg); adb("push", argv[2], f"{rd}/launch_env.txt", capture=True); adb("shell", "chmod", "a+rw", f"{rd}/launch_env.txt", check=False)
        txt = open(argv[2], encoding="utf-8").read()
        print("launch_env.txt: " + (", ".join(l.split("=", 1)[0] for l in txt.splitlines() if "=" in l) or "(empty: cleared)"))
    elif a == "log":
        r = adb("shell", "cat", f"{remote_dir(pkg)}/session.log", capture=True, check=False)
        txt = (r.stdout or b"").decode(errors="replace")
        lc = adb("logcat", "-d", "-t", "400", capture=True, check=False, timeout=60)
        lct = (lc.stdout or b"").decode(errors="replace")
        if len(argv) > 2:
            with open(argv[2], "w", encoding="utf-8") as f: f.write(txt + "\n==== logcat ====\n" + lct)
        print(txt[-6000:]); print("==== logcat (SDL, the app, crashes) ====")
        print("\n".join(l for l in lct.splitlines() if re.search(r"SDL|DEBUG|libc|AndroidRuntime|encore|vulkan|Adreno", l, re.I))[-6000:])
    elif a == "profile":   # profile <title> <out.txt> <seconds>: simpleperf on the running game (the app is profileable), its report
        if len(argv) < 4 or not argv[3].isdigit() or not 3 <= int(argv[3]) <= 60: print("profile <title> <out.txt> <3-60 seconds>"); return 1
        sp = os.path.join(AT, "ndk", "simpleperf", "bin", "android", "arm64", "simpleperf")
        if not os.path.isfile(sp): print(f"no simpleperf at {sp}"); return 1
        pid = (adb("shell", "pidof", pkg, capture=True, check=False).stdout or b"").decode().split()
        if not pid: print(f"{pkg} isn't running: start it first"); return 1
        adb("push", sp, "/data/local/tmp/simpleperf", capture=True); adb("shell", "chmod", "755", "/data/local/tmp/simpleperf")
        adb("shell", "setprop", "security.perf_harden", "0", check=False)   # (as the NDK's app_profiler.py does: perf events for the shell)
        r = adb("shell", "/data/local/tmp/simpleperf", "record", "--app", pkg, "--duration", argv[3], "-f", "1000", "-o", "/data/local/tmp/encore-perf.data",
                capture=True, check=False, timeout=int(argv[3]) + 120)
        rec = ((r.stdout or b"") + (r.stderr or b"")).decode(errors="replace")
        out = [f"==== record ({argv[3]} s, pid {pid[0]}) ====", rec.strip()]
        for title_, sort, lim in (("threads", "comm", "0.5"), ("libraries", "dso", "0.5"), ("functions", "comm,dso,symbol", "0.3")):
            rr = adb("shell", "/data/local/tmp/simpleperf", "report", "-i", "/data/local/tmp/encore-perf.data", "--sort", sort, "--percent-limit", lim,
                     capture=True, check=False, timeout=300)
            out += [f"==== {title_} ====", ((rr.stdout or b"") + (rr.stderr or b"")).decode(errors="replace").strip()]
        with open(argv[2], "w", encoding="utf-8") as f: f.write("\n".join(out) + "\n")
        print("\n".join(out)[:12000])
    elif a == "shot":
        if len(argv) < 3: print("shot <title> <out.png>"); return 1
        with open(argv[2], "wb") as f: f.write(adb("exec-out", "screencap", "-p", capture=True).stdout)
        print(f"screen -> {argv[2]}")
    else: print(__doc__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
