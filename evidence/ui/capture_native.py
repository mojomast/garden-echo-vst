#!/usr/bin/env python3
"""Local X11 native-window capture; no external packages or network.

Run inside xvfb-run after building the standalone. Captures actual X11 pixels
with ffmpeg. XTest is only used for native input, never to manufacture images.
"""
import ctypes as C
import os
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence/ui"
X = C.CDLL("libX11.so.6")
T = C.CDLL("libXtst.so.6")
D = C.c_void_p
W = C.c_ulong
X.XOpenDisplay.argtypes = [C.c_char_p]
X.XOpenDisplay.restype = D
X.XDefaultRootWindow.argtypes = [D]
X.XDefaultRootWindow.restype = W
X.XQueryTree.argtypes = [D, W, C.POINTER(W), C.POINTER(W), C.POINTER(C.POINTER(W)), C.POINTER(C.c_uint)]
X.XFetchName.argtypes = [D, W, C.POINTER(C.c_char_p)]
X.XFree.argtypes = [D]
X.XResizeWindow.argtypes = [D, W, C.c_uint, C.c_uint]
X.XMoveWindow.argtypes = [D, W, C.c_int, C.c_int]
X.XRaiseWindow.argtypes = [D, W]
X.XSetInputFocus.argtypes = [D, W, C.c_int, W]
X.XFlush.argtypes = [D]
X.XGetGeometry.argtypes = [D, W, C.POINTER(W), C.POINTER(C.c_int), C.POINTER(C.c_int), C.POINTER(C.c_uint), C.POINTER(C.c_uint), C.POINTER(C.c_uint), C.POINTER(C.c_uint)]
X.XInternAtom.argtypes = [D, C.c_char_p, C.c_int]
X.XInternAtom.restype = W
X.XGetWindowProperty.argtypes = [D, W, W, C.c_long, C.c_long, C.c_int, W, C.POINTER(W), C.POINTER(C.c_int), C.POINTER(W), C.POINTER(W), C.POINTER(C.POINTER(C.c_ubyte))]
X.XGetWindowProperty.restype = C.c_int
X.XStringToKeysym.argtypes = [C.c_char_p]
X.XStringToKeysym.restype = W
X.XKeysymToKeycode.argtypes = [D, W]
X.XKeysymToKeycode.restype = C.c_uint
T.XTestFakeMotionEvent.argtypes = [D, C.c_int, C.c_int, C.c_int, W]
T.XTestFakeButtonEvent.argtypes = [D, C.c_uint, C.c_int, W]
T.XTestFakeKeyEvent.argtypes = [D, C.c_uint, C.c_int, W]
d = X.XOpenDisplay(None)
if not d:
    raise SystemExit("Requires an X11 display")
root = X.XDefaultRootWindow(d)


def children(window):
    r, p, ptr, n = W(), W(), C.POINTER(W)(), C.c_uint()
    X.XQueryTree(d, window, C.byref(r), C.byref(p), C.byref(ptr), C.byref(n))
    result = [ptr[i] for i in range(n.value)]
    if ptr:
        X.XFree(ptr)
    return result


def title(window):
    ptr = C.c_char_p()
    X.XFetchName(d, window, C.byref(ptr))
    result = ptr.value.decode(errors="replace") if ptr.value else ""
    if ptr:
        X.XFree(C.cast(ptr, D))
    return result


def property_text(window, name):
    actual, fmt, count, remaining = W(), C.c_int(), W(), W()
    data = C.POINTER(C.c_ubyte)()
    status = X.XGetWindowProperty(d, window, X.XInternAtom(d, name.encode(), 0),
                                  0, 256, 0, 0, C.byref(actual), C.byref(fmt),
                                  C.byref(count), C.byref(remaining), C.byref(data))
    try:
        return C.string_at(data, count.value).decode(errors="replace") if status == 0 and fmt.value == 8 and data else ""
    finally:
        if data:
            X.XFree(C.cast(data, D))


def window_tree(window, depth=0):
    """Inspect X11 names below the root, including JUCE-owned child windows."""
    if depth > 5:
        return []
    result = []
    for child in children(window):
        result.append({"id": hex(child), "name": title(child), "netName": property_text(child, "_NET_WM_NAME"), "class": property_text(child, "WM_CLASS"), "geometry": geometry(child), "depth": depth})
        result.extend(window_tree(child, depth + 1))
    return result


def key(name):
    codes = [X.XKeysymToKeycode(d, X.XStringToKeysym(part.encode())) for part in name.split("+")]
    if not all(codes):
        raise ValueError("Unknown X11 key: " + name)
    for code in codes:
        T.XTestFakeKeyEvent(d, code, 1, 0)
    for code in reversed(codes):
        T.XTestFakeKeyEvent(d, code, 0, 0)
    X.XFlush(d)
    time.sleep(.15)


def click(x, y):
    T.XTestFakeMotionEvent(d, -1, x, y, 0)
    T.XTestFakeButtonEvent(d, 1, 1, 0)
    T.XTestFakeButtonEvent(d, 1, 0, 0)
    X.XFlush(d)
    time.sleep(.25)


def capture(name):
    time.sleep(.5)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "x11grab", "-video_size", "1400x1200", "-draw_mouse", "0", "-i", os.environ["DISPLAY"],
                    "-frames:v", "1", str(OUT / (name + ".png"))], check=True)


def geometry(window):
    r, x, y, w, h, border, depth = W(), C.c_int(), C.c_int(), C.c_uint(), C.c_uint(), C.c_uint(), C.c_uint()
    X.XGetGeometry(d, window, C.byref(r), C.byref(x), C.byref(y), C.byref(w), C.byref(h), C.byref(border), C.byref(depth))
    return {"x": x.value, "y": y.value, "width": w.value, "height": h.value}


if __name__ == "__main__":
    home = ROOT / ("build/astra-ui/capture-home-" + str(os.getpid()))
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home))
    binary = ROOT / "build/astra-ui/GardenEcho_artefacts/Release/Standalone/Garden Echo"
    with (OUT / "standalone.log").open("w") as log:
        process = subprocess.Popen([str(binary)], env=env, stdout=log, stderr=log)
        try:
            window = None
            for _ in range(60):
                candidates = [w for w in children(root)
                              if title(w) == "Garden Echo" or property_text(w, "_NET_WM_NAME") == "Garden Echo"
                              or "Garden Echo" in property_text(w, "WM_CLASS").split("\0")]
                if candidates:
                    window = candidates[0]
                    break
                if process.poll() is not None:
                    break
                time.sleep(.25)
            if window is None:
                raise RuntimeError(f"Native Garden Echo window did not appear (exit={process.poll()}, X11 tree={window_tree(root)})")
            X.XMoveWindow(d, window, 20, 20)
            X.XRaiseWindow(d, window)
            X.XSetInputFocus(d, window, 1, 0)
            X.XFlush(d)
            time.sleep(1)
            initial = geometry(window)
            screen = geometry(root)
            if (screen["width"], screen["height"]) != (1400, 1200):
                raise RuntimeError("Capture requires a 1400x1200 Xvfb screen")
            overhead_w, overhead_h = initial["width"] - 900, initial["height"] - 730
            receipt = {"default-900x730": initial, "screen": screen,
                       "standaloneChromeInferredFromDefaultEditor": {"width": overhead_w, "height": overhead_h},
                       "dimensionVerification": "Exact editor sizes also rendered by NativeChecks component snapshots; standalone chrome inferred from constructor default 900x730."}
            capture("default-900x730")
            # Preserve measured standalone chrome, including its mute warning.
            for name, width, height in [("compact-710x645", 710, 645), ("expanded-1280x1000", 1280, 1000)]:
                X.XResizeWindow(d, window, width + overhead_w, height + overhead_h)
                X.XFlush(d)
                capture(name)
                receipt[name] = geometry(window)
            actions = json.loads(os.environ.get("GARDEN_UI_ACTIONS", "[]"))
            if not isinstance(actions, list):
                raise ValueError("GARDEN_UI_ACTIONS must be a JSON list")
            for action in actions:
                if not isinstance(action, dict) or not set(action) <= {"click", "key", "resize", "capture"}:
                    raise ValueError("Unsupported native input action")
                if "click" in action:
                    if len(action["click"]) != 2 or not (0 <= action["click"][0] < 1400 and 0 <= action["click"][1] < 1200):
                        raise ValueError("Click outside screenshot")
                    click(*action["click"])
                if "key" in action:
                    key(action["key"])
                if "resize" in action:
                    width, height = action["resize"]
                    if not (710 <= width <= 1280 and 645 <= height <= 1000):
                        raise ValueError("Resize outside editor limits")
                    X.XResizeWindow(d, window, width + overhead_w, height + overhead_h)
                    X.XFlush(d)
                    time.sleep(.4)
                if "capture" in action:
                    if not isinstance(action["capture"], str) or not action["capture"].replace("-", "").isalnum():
                        raise ValueError("Invalid capture name")
                    capture(action["capture"])
                    receipt[action["capture"]] = geometry(window)
            receipt["nativeInputActions"] = actions
            (OUT / "capture-dimensions.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print("Native capture completed; inspect actual dimensions and content before acceptance.")
        finally:
            process.terminate()
            process.wait(timeout=10)
